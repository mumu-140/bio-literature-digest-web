from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..deps import get_current_user, get_db
from ..models import LoginOtpCode, Session as UserSession, User
from ..schemas import (
    AuthUser,
    LoginOtpIssuedResponse,
    LoginOtpRequest,
    LoginOtpVerifyRequest,
    LoginRequest,
    LoginResponse,
    LoginVerifySuccessResponse,
    RegisterOtpRequest,
    RegisterRequest,
)
from ..security import (
    create_session_token,
    has_usable_password,
    hash_password,
    hash_session_token,
    verify_password,
)
from ..services.access_trace import write_access_trace
from ..services.audit import record_action
from ..services.push_email import PushEmailError, send_otp_email
from ..services.user_sync import derive_display_name

router = APIRouter(prefix="/auth", tags=["auth"])

WHITELIST_MESSAGE = "此邮箱未开通访问权限，请联系管理员开通"


def build_auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
    )


def _issue_login_session(
    *,
    user: User,
    request: Request,
    response: Response,
    db: Session,
    auth_method: str,
    action_type: str,
    extra_detail: dict[str, object] | None = None,
) -> LoginResponse:
    token, token_hash, expires_at = create_session_token()
    session_obj = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        auth_method=auth_method,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    user.last_login_at = datetime.utcnow()
    db.add(session_obj)
    detail: dict[str, object] = {"email": user.email}
    if extra_detail:
        detail.update(extra_detail)
    record_action(
        db,
        action_type=action_type,
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="session",
        detail=detail,
    )
    db.commit()
    db.refresh(user)
    write_access_trace(user=user, request=request, event_type=action_type)

    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    return LoginResponse(user=build_auth_user(user))


COMMON_DOMAIN_TYPOS: dict[str, str] = {
    "qq.ocm": "qq.com",
    "qq.con": "qq.com",
    "qq.cm": "qq.com",
    "qq.co": "qq.com",
    "qq.cmo": "qq.com",
    "163.ocm": "163.com",
    "163.con": "163.com",
    "163.cm": "163.com",
    "163.cmo": "163.com",
    "126.ocm": "126.com",
    "126.con": "126.com",
    "126.cm": "126.com",
    "gmail.ocm": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.cm": "gmail.com",
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "outlook.ocm": "outlook.com",
    "outlook.con": "outlook.com",
    "outlok.com": "outlook.com",
    "hotmail.ocm": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "icloud.ocm": "icloud.com",
    "icloud.con": "icloud.com",
    "sina.ocm": "sina.com",
    "sina.con": "sina.com",
    "foxmail.ocm": "foxmail.com",
    "foxmail.con": "foxmail.com",
}

INVALID_TLD_SUFFIXES = (".ocm", ".con", ".cmo", ".comm", ".cnm", ".ed.cn")


def _validate_email_domain_typo(email: str) -> None:
    if "@" not in email:
        return
    local_part, domain = email.rsplit("@", 1)
    domain = domain.strip().lower()
    if domain in COMMON_DOMAIN_TYPOS:
        suggested = f"{local_part}@{COMMON_DOMAIN_TYPOS[domain]}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"邮箱后缀疑似拼写错误（@{domain}），请检查是否应为 {suggested}",
        )
    for bad_suffix in INVALID_TLD_SUFFIXES:
        if domain.endswith(bad_suffix):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"邮箱域名后缀疑似拼写错误（@{domain}），请核对后再试",
            )


def _hash_otp_code(email: str, code: str) -> str:
    secret = get_settings().session_secret
    return hashlib.sha256(f"{secret}:{email.lower()}:{code}".encode("utf-8")).hexdigest()


def _generate_otp_code(length: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def _count_otp_codes(
    db: Session,
    *,
    email: str,
    client_ip: str,
    since: datetime,
    by_ip: bool = False,
) -> int:
    stmt = select(LoginOtpCode.id).where(LoginOtpCode.created_at > since)
    stmt = stmt.where(LoginOtpCode.created_ip == client_ip) if by_ip else stmt.where(LoginOtpCode.email == email)
    return len(db.scalars(stmt).all())


def _enforce_otp_rate_limits(
    db: Session,
    *,
    email: str,
    client_ip: str,
    now: datetime,
    settings: Settings,
) -> None:
    last_code = db.scalar(
        select(LoginOtpCode)
        .where(LoginOtpCode.email == email)
        .order_by(LoginOtpCode.created_at.desc())
        .limit(1)
    )
    if last_code is not None and last_code.created_at > now - timedelta(seconds=settings.otp_resend_cooldown_seconds):
        retry_after = int(
            (last_code.created_at + timedelta(seconds=settings.otp_resend_cooldown_seconds) - now).total_seconds()
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"验证码发送过于频繁，请 {max(retry_after, 1)} 秒后再试",
        )
    hourly_count = _count_otp_codes(db, email=email, client_ip=client_ip, since=now - timedelta(hours=1))
    if hourly_count >= settings.otp_per_email_hourly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="验证码发送次数达到上限，请一小时后再试",
        )
    daily_count = _count_otp_codes(db, email=email, client_ip=client_ip, since=now - timedelta(hours=24))
    if daily_count >= settings.otp_per_email_daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日验证码发送次数已达上限，请明天再试",
        )
    if client_ip:
        ip_count = _count_otp_codes(
            db, email=email, client_ip=client_ip, since=now - timedelta(hours=1), by_ip=True,
        )
        if ip_count >= settings.otp_per_ip_hourly_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="当前网络验证码发送次数已达上限，请稍后再试",
            )


@router.post(
    "/register/otp/request",
    response_model=LoginOtpIssuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_register_otp(
    payload: RegisterOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginOtpIssuedResponse:
    settings = get_settings()
    normalized_email = payload.email.lower()
    _validate_email_domain_typo(normalized_email)
    purpose = (payload.purpose or "register").strip().lower()
    if purpose not in {"register", "reset"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的验证用途")

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is not None:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账户已被停用，请联系管理员")
    elif purpose == "reset":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该邮箱尚未注册，请先切换至「注册 / 首次设密」完成注册",
        )

    client_ip = request.client.host if request.client else ""
    now = datetime.utcnow()
    _enforce_otp_rate_limits(db, email=normalized_email, client_ip=client_ip, now=now, settings=settings)

    code = _generate_otp_code(settings.otp_code_length)
    action_type = "password_reset_otp_requested" if purpose == "reset" else "register_otp_requested"
    if not settings.otp_dev_echo:
        try:
            send_otp_email(
                email=normalized_email,
                code=code,
                ttl_minutes=max(settings.otp_code_ttl_seconds // 60, 1),
                purpose=purpose,
            )
        except PushEmailError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"验证码邮件发送失败：{exc}")

    otp = LoginOtpCode(
        email=normalized_email,
        code_hash=_hash_otp_code(normalized_email, code),
        attempts_remaining=settings.otp_max_verify_attempts,
        created_ip=client_ip or None,
        expires_at=now + timedelta(seconds=settings.otp_code_ttl_seconds),
    )
    db.add(otp)
    record_action(
        db,
        action_type=action_type,
        actor_user_id=user.id if user else None,
        target_user_id=user.id if user else None,
        entity_type="session",
        detail={"email": normalized_email, "purpose": purpose},
    )
    db.commit()

    if user is not None:
        write_access_trace(user=user, request=request, event_type=action_type)
    if settings.otp_dev_echo:
        return LoginOtpIssuedResponse(
            email=normalized_email,
            expires_in=settings.otp_code_ttl_seconds,
            resend_after=settings.otp_resend_cooldown_seconds,
            dev_code=code,
        )
    return LoginOtpIssuedResponse(
        email=normalized_email,
        expires_in=settings.otp_code_ttl_seconds,
        resend_after=settings.otp_resend_cooldown_seconds,
    )


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_with_otp(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    normalized_email = payload.email.lower()
    _validate_email_domain_typo(normalized_email)
    purpose = (payload.purpose or "register").strip().lower()
    if purpose not in {"register", "reset"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的验证用途")

    raw_password = payload.password.strip()
    if len(raw_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="登录密码长度至少为 6 位")

    code = payload.code.strip()
    if len(code) != settings.otp_code_length or not code.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码格式不正确")

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is not None:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账户已被停用，请联系管理员")
    elif purpose == "reset":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该邮箱尚未注册，请先切换至「注册 / 首次设密」完成注册",
        )

    now = datetime.utcnow()
    otp = db.scalar(
        select(LoginOtpCode)
        .where(
            LoginOtpCode.email == normalized_email,
            LoginOtpCode.consumed_at.is_(None),
            LoginOtpCode.expires_at > now,
        )
        .order_by(LoginOtpCode.created_at.desc())
        .limit(1)
    )
    if otp is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已失效或尚未获取，请重新获取验证码")

    if otp.code_hash != _hash_otp_code(normalized_email, code):
        otp.attempts_remaining -= 1
        if otp.attempts_remaining <= 0:
            otp.consumed_at = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误次数过多，请重新获取",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"验证码不正确，还可尝试 {otp.attempts_remaining} 次",
        )

    otp.consumed_at = now
    display_name = (payload.name or "").strip()
    created_user = False
    if user is None:
        user = User(
            email=normalized_email,
            name=display_name or derive_display_name(normalized_email),
            password_hash=hash_password(raw_password),
            role="member",
            user_group="internal",
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.flush()
        created_user = True
        action_type = "register_success"
    else:
        user.password_hash = hash_password(raw_password)
        if display_name:
            user.name = display_name
        user.must_change_password = False
        action_type = "password_reset_success" if purpose == "reset" else "register_activate_success"

    return _issue_login_session(
        user=user,
        request=request,
        response=response,
        db=db,
        auth_method="password",
        action_type=action_type,
        extra_detail={"created_user": created_user, "purpose": purpose},
    )


@router.post(
    "/login/otp/request",
    response_model=LoginOtpIssuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_login_otp(
    payload: LoginOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginOtpIssuedResponse:
    settings = get_settings()
    if not settings.otp_login_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OTP login is disabled")
    normalized_email = payload.email.lower()
    _validate_email_domain_typo(normalized_email)
    client_ip = request.client.host if request.client else ""
    now = datetime.utcnow()

    _enforce_otp_rate_limits(db, email=normalized_email, client_ip=client_ip, now=now, settings=settings)

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        return LoginOtpIssuedResponse(
            email=payload.email,
            expires_in=settings.otp_code_ttl_seconds,
            resend_after=settings.otp_resend_cooldown_seconds,
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    code = _generate_otp_code(settings.otp_code_length)
    if not settings.otp_dev_echo:
        try:
            send_otp_email(
                email=user.email,
                code=code,
                ttl_minutes=max(settings.otp_code_ttl_seconds // 60, 1),
                purpose="login",
            )
        except PushEmailError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"验证码邮件发送失败：{exc}")

    otp = LoginOtpCode(
        email=normalized_email,
        code_hash=_hash_otp_code(normalized_email, code),
        attempts_remaining=settings.otp_max_verify_attempts,
        created_ip=client_ip or None,
        expires_at=now + timedelta(seconds=settings.otp_code_ttl_seconds),
    )
    db.add(otp)
    record_action(
        db,
        action_type="login_otp_requested",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="session",
        detail={"email": user.email},
    )
    db.commit()
    write_access_trace(user=user, request=request, event_type="login_otp_requested")
    if settings.otp_dev_echo:
        return LoginOtpIssuedResponse(
            email=user.email,
            expires_in=settings.otp_code_ttl_seconds,
            resend_after=settings.otp_resend_cooldown_seconds,
            dev_code=code,
        )
    return LoginOtpIssuedResponse(
        email=user.email,
        expires_in=settings.otp_code_ttl_seconds,
        resend_after=settings.otp_resend_cooldown_seconds,
    )


@router.post("/login/otp/verify", response_model=LoginVerifySuccessResponse)
def verify_login_otp(
    payload: LoginOtpVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginVerifySuccessResponse:
    settings = get_settings()
    if not settings.otp_login_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OTP login is disabled")
    normalized_email = payload.email.lower()
    code = payload.code.strip()
    if len(code) != settings.otp_code_length or not code.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码格式不正确")

    now = datetime.utcnow()
    otp = db.scalar(
        select(LoginOtpCode)
        .where(
            LoginOtpCode.email == normalized_email,
            LoginOtpCode.consumed_at.is_(None),
            LoginOtpCode.expires_at > now,
        )
        .order_by(LoginOtpCode.created_at.desc())
        .limit(1)
    )
    user = db.scalar(select(User).where(User.email == normalized_email))
    if otp is None:
        if user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=WHITELIST_MESSAGE)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已失效，请重新获取")

    if otp.code_hash != _hash_otp_code(normalized_email, code):
        otp.attempts_remaining -= 1
        if otp.attempts_remaining <= 0:
            otp.consumed_at = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误次数过多，请重新获取",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"验证码不正确，还可尝试 {otp.attempts_remaining} 次",
        )

    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=WHITELIST_MESSAGE)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    otp.consumed_at = now
    issued = _issue_login_session(
        user=user,
        request=request,
        response=response,
        db=db,
        auth_method="otp-email",
        action_type="login_otp_success",
    )
    return LoginVerifySuccessResponse(user=issued.user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    """Direct account + password login.

    When OTP_LOGIN_ENABLED is false and no password is provided (used by legacy
    test suites), falls back to passwordless session creation for existing
    passwordless test accounts.
    """
    settings = get_settings()
    normalized_email = payload.email.lower()
    _validate_email_domain_typo(normalized_email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    raw_password = payload.password or ""

    if not raw_password:
        if not settings.otp_login_enabled:
            if user is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=WHITELIST_MESSAGE)
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
            if has_usable_password(user.password_hash):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入登录密码")
            return _issue_login_session(
                user=user,
                request=request,
                response=response,
                db=db,
                auth_method="passwordless",
                action_type="login_success",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入登录密码")

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误，若尚未注册请先切换至「注册 / 首次设密」完成注册",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账户已被停用，请联系管理员")
    if not has_usable_password(user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账户尚未设置登录密码，请切换至「注册 / 首次设密」通过邮箱验证设置密码",
        )
    if not verify_password(raw_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    return _issue_login_session(
        user=user,
        request=request,
        response=response,
        db=db,
        auth_method="password",
        action_type="login_success",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        from ..security import hash_session_token

        db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(token)))
        db.commit()
    response.delete_cookie(settings.session_cookie_name)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthUser)
def me(request: Request, current_user: User = Depends(get_current_user)) -> AuthUser:
    write_access_trace(user=current_user, request=request, event_type="session_entry")
    return build_auth_user(current_user)


def _safe_next_path(value: str) -> str:
    return value if value.startswith("/") and not value.startswith("//") else "/papers/published"


@router.post("/deerflow-sso/consume")
async def consume_deerflow_sso(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    raw_body = await request.body()
    if len(raw_body) > 4096:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="SSO payload is too large")
    form = parse_qs(raw_body.decode("utf-8", errors="strict"), keep_blank_values=True)
    ticket = (form.get("ticket") or [""])[0].strip()
    next_path = _safe_next_path((form.get("next") or ["/papers/published"])[0].strip())
    if not ticket or len(ticket) > 512:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid SSO ticket")

    session_obj = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_session_token(ticket),
            UserSession.auth_method == "deerflow-pending",
        )
    )
    if session_obj is None or session_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO ticket is invalid or expired")
    user = session_obj.user
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    session_obj.auth_method = "deerflow-sso"
    session_obj.last_seen_at = datetime.utcnow()
    settings = get_settings()
    session_obj.expires_at = datetime.utcnow() + timedelta(hours=settings.session_ttl_hours)
    session_obj.ip_address = request.client.host if request.client else ""
    session_obj.user_agent = request.headers.get("user-agent", "")
    user.last_login_at = datetime.utcnow()
    record_action(
        db,
        action_type="deerflow_sso_consumed",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="session",
        entity_id=session_obj.id,
        detail={"next_path": next_path},
    )
    db.commit()
    write_access_trace(user=user, request=request, event_type="deerflow_sso_consumed")

    response = RedirectResponse(url=next_path, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=ticket,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    response.headers["Cache-Control"] = "no-store"
    return response

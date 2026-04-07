from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_current_user, get_db
from ..models import Session as UserSession, User
from ..schemas import AuthUser, ChangePasswordRequest, LoginRequest, LoginResponse
from ..security import create_session_token, hash_password, verify_email_login_token, verify_password
from ..services.access_trace import write_access_trace
from ..services.audit import record_action

router = APIRouter(prefix="/auth", tags=["auth"])


def build_auth_user(user: User, session_auth_method: str = "password") -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        must_change_password=user.must_change_password,
        is_active=user.is_active,
        session_auth_method=session_auth_method,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    token, token_hash, expires_at = create_session_token()
    session_obj = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        auth_method="password",
        expires_at=expires_at,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    user.last_login_at = datetime.utcnow()
    db.add(session_obj)
    record_action(
        db,
        action_type="login_success",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="session",
        detail={"email": user.email},
    )
    db.commit()
    db.refresh(user)
    write_access_trace(user=user, request=request, event_type="login_success")

    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    return LoginResponse(user=build_auth_user(user, session_auth_method="password"))


@router.post("/email-login", response_model=LoginResponse)
def email_login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_email_login_token(payload.password, payload.email):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired email login link")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    token, token_hash, expires_at = create_session_token()
    session_obj = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        auth_method="email_link",
        expires_at=expires_at,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    user.last_login_at = datetime.utcnow()
    db.add(session_obj)
    record_action(
        db,
        action_type="email_link_login_success",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="session",
        detail={"email": user.email},
    )
    db.commit()
    db.refresh(user)
    write_access_trace(user=user, request=request, event_type="email_link_login_success")

    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    return LoginResponse(user=build_auth_user(user, session_auth_method="email_link"))


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
    session_auth_method = getattr(getattr(request.state, "user_session", None), "auth_method", "password")
    return build_auth_user(current_user, session_auth_method=session_auth_method)


@router.post("/change-password", response_model=AuthUser)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthUser:
    session_auth_method = getattr(getattr(request.state, "user_session", None), "auth_method", "password")
    allow_without_current = session_auth_method == "email_link" and current_user.must_change_password
    if not allow_without_current and not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    record_action(
        db,
        action_type="password_change",
        actor_user_id=current_user.id,
        target_user_id=current_user.id,
        entity_type="user",
        entity_id=current_user.id,
        detail={"must_change_password": False},
    )
    db.commit()
    db.refresh(current_user)
    return build_auth_user(current_user, session_auth_method=session_auth_method)

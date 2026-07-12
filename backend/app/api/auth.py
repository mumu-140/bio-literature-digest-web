from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_current_user, get_db
from ..models import Session as UserSession, User
from ..schemas import AuthUser, LoginRequest, LoginResponse
from ..security import create_session_token
from ..services.access_trace import write_access_trace
from ..services.audit import record_action
from ..services.user_sync import derive_display_name

router = APIRouter(prefix="/auth", tags=["auth"])


def build_auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
    )


def _login_with_email(
    payload: LoginRequest,
    *,
    request: Request,
    response: Response,
    db: Session,
    action_type: str,
) -> LoginResponse:
    normalized_email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    created_user = False
    if user is None:
        display_name = (payload.name or "").strip() or derive_display_name(normalized_email)
        user = User(
            email=normalized_email,
            name=display_name,
            password_hash="passwordless",
            role="member",
            user_group="internal",
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.flush()
        created_user = True

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    token, token_hash, expires_at = create_session_token()
    session_obj = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        auth_method="passwordless",
        expires_at=expires_at,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    user.last_login_at = datetime.utcnow()
    db.add(session_obj)
    record_action(
        db,
        action_type=action_type,
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="session",
        detail={"email": user.email, "created_user": created_user},
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


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    return _login_with_email(
        payload,
        request=request,
        response=response,
        db=db,
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

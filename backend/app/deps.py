from __future__ import annotations

from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_session
from .models import Session as UserSession, User
from .shared_database import get_shared_session
from .security import hash_session_token


def get_db(session: Session = Depends(get_session)) -> Session:
    return session


def get_shared_db(session: Session = Depends(get_shared_session)) -> Session:
    return session


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    token_hash = hash_session_token(token)
    session_obj = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if not session_obj or session_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = session_obj.user
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    session_obj.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    request.state.user_session = session_obj
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

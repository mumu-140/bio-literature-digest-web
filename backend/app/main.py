from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api import admin, analytics, auth, digests, exports, favorites, pushes
from .config import get_settings
from . import database
from .migrations import run_runtime_migrations
from .models import User
from .security import hash_password


def bootstrap_admin() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin:
        return
    if database.SessionLocal is None:
        return
    with database.SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == settings.initial_admin_email.lower()))
        if existing:
            return
        admin_user = User(
            email=settings.initial_admin_email.lower(),
            name=settings.initial_admin_name,
            password_hash=hash_password(settings.initial_admin_password),
            role="admin",
            is_active=True,
            must_change_password=False,
        )
        db.add(admin_user)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.configure_database()
    run_runtime_migrations(database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    bootstrap_admin()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(admin.router, prefix=settings.api_prefix)
    app.include_router(digests.router, prefix=settings.api_prefix)
    app.include_router(favorites.router, prefix=settings.api_prefix)
    app.include_router(pushes.router, prefix=settings.api_prefix)
    app.include_router(analytics.router, prefix=settings.api_prefix)
    app.include_router(exports.router, prefix=settings.api_prefix)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

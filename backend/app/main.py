from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api import admin, auth, digests, exports, favorites, pushes
from .config import get_settings
from . import database
from .migrations import run_runtime_migrations
from .models import User
from .integrations.producer_import.service import check_and_import_latest_runs, sync_users_from_producer_sources

_PRODUCER_SYNC_LOCK = Lock()


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
            password_hash="passwordless",
            role="admin",
            is_active=True,
            must_change_password=False,
        )
        db.add(admin_user)
        db.commit()

def sync_from_producer(*, trigger: str = "startup") -> None:
    if not _PRODUCER_SYNC_LOCK.acquire(blocking=False):
        return
    try:
        if database.SessionLocal is not None:
            with database.SessionLocal() as db:
                settings = get_settings()
                if settings.producer_sync_enabled:
                    sync_users_from_producer_sources(db)
                    check_and_import_latest_runs(db, trigger=trigger)
    finally:
        _PRODUCER_SYNC_LOCK.release()


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.configure_database()
    run_runtime_migrations(database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    await asyncio.to_thread(sync_from_producer, trigger="startup")
    bootstrap_admin()
    try:
        yield
    finally:
        return


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
    app.include_router(exports.router, prefix=settings.api_prefix)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api import admin, auth, digests, exports, favorites, pushes
from .config import Settings, get_settings
from .models import User
from .integrations.producer_import.runtime_sync import (
    ensure_runtime_database_ready,
    inside_sync_window as _inside_sync_window,
    sync_from_producer,
)
from . import database


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

async def periodic_producer_sync(settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.producer_sync_interval_seconds)
        if not settings.producer_sync_enabled or not _inside_sync_window(settings):
            continue
        try:
            await asyncio.to_thread(sync_from_producer, trigger="periodic")
        except Exception as exc:
            print(f"[producer-sync] periodic sync failed: {exc}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    ensure_runtime_database_ready()
    if settings.producer_sync_enabled:
        await asyncio.to_thread(sync_from_producer, trigger="startup")
    bootstrap_admin()

    sync_task: asyncio.Task[None] | None = None
    if settings.producer_sync_enabled and settings.producer_sync_interval_seconds > 0:
        sync_task = asyncio.create_task(periodic_producer_sync(settings))
    try:
        yield
    finally:
        if sync_task is not None:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task


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

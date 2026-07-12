from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pathlib import Path

from .config import PROJECT_ROOT, get_instance_paths, get_settings


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def configure_database(database_url: Optional[str] = None) -> None:
    global engine, SessionLocal
    settings = get_settings()
    instance_paths = get_instance_paths(PROJECT_ROOT)
    resolved_url = database_url or settings.database_url
    if resolved_url.startswith("sqlite:///./"):
        relative_path = resolved_url.removeprefix("sqlite:///./")
        resolved_url = f"sqlite:///{(instance_paths.web_data_dir / relative_path).resolve()}"
    if resolved_url.startswith("sqlite:///"):
        sqlite_path = Path(resolved_url.removeprefix("sqlite:///")).resolve()
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    engine = create_engine(resolved_url, future=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session():
    if SessionLocal is None:
        configure_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import PROJECT_ROOT, get_instance_paths, get_settings


class SharedBase(DeclarativeBase):
    pass


shared_engine = None
SharedSessionLocal = None


def configure_shared_database(database_url: Optional[str] = None) -> None:
    global shared_engine, SharedSessionLocal
    settings = get_settings()
    instance_paths = get_instance_paths(PROJECT_ROOT)
    resolved_url = database_url or settings.shared_database_url
    if resolved_url.startswith("sqlite:///./"):
        relative_path = resolved_url.removeprefix("sqlite:///./")
        resolved_url = f"sqlite:///{(instance_paths.shared_data_dir / relative_path).resolve()}"
    if resolved_url.startswith("sqlite:///"):
        sqlite_path = Path(resolved_url.removeprefix("sqlite:///")).resolve()
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    shared_engine = create_engine(resolved_url, future=True, connect_args=connect_args)
    if resolved_url.startswith("sqlite"):
        with shared_engine.begin() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
    SharedSessionLocal = sessionmaker(bind=shared_engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_shared_session():
    if SharedSessionLocal is None:
        configure_shared_database()
    db = SharedSessionLocal()
    try:
        yield db
    finally:
        db.close()

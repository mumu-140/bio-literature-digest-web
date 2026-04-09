from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def run_runtime_migrations(engine: Engine) -> None:
    _migrate_user_visibility_fields(engine)
    _migrate_user_producer_uid(engine)
    _migrate_session_auth_method(engine)


def _user_columns(engine: Engine) -> set[str]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "users" not in table_names:
        return set()
    return {column["name"] for column in inspector.get_columns("users")}


def _migrate_user_visibility_fields(engine: Engine) -> None:
    columns = _user_columns(engine)
    if not columns:
        return
    statements: list[str] = []
    if "user_group" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN user_group VARCHAR(32) NOT NULL DEFAULT 'internal'")
    if "owner_admin_user_id" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN owner_admin_user_id INTEGER")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_user_group ON users (user_group)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_owner_admin_user_id ON users (owner_admin_user_id)"))


def _session_columns(engine: Engine) -> set[str]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "sessions" not in table_names:
        return set()
    return {column["name"] for column in inspector.get_columns("sessions")}


def _migrate_session_auth_method(engine: Engine) -> None:
    columns = _session_columns(engine)
    if not columns or "auth_method" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE sessions ADD COLUMN auth_method VARCHAR(32) NOT NULL DEFAULT 'passwordless'"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_auth_method ON sessions (auth_method)"))


def _migrate_user_producer_uid(engine: Engine) -> None:
    columns = _user_columns(engine)
    if not columns or "producer_uid" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN producer_uid VARCHAR(128) NOT NULL DEFAULT ''"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_producer_uid ON users (producer_uid)"))

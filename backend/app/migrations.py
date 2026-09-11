from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .services.database_tuning import install_performance_indexes
from .services.library_stats import ensure_library_stats
from .services.search_index import ensure_search_index


def run_runtime_migrations(engine: Engine) -> None:
    _migrate_user_visibility_fields(engine)
    _migrate_user_producer_uid(engine)
    _migrate_session_auth_method(engine)
    _migrate_push_email_fields(engine)
    _migrate_push_batch_fields(engine)
    install_performance_indexes(engine)
    ensure_search_index(engine)
    ensure_library_stats(engine)


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


def _migrate_push_email_fields(engine: Engine) -> None:
    inspector = inspect(engine)
    if "literature_pushes_v2" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("literature_pushes_v2")}
    statements = []
    if "email_notification_status" not in columns:
        statements.append("ALTER TABLE literature_pushes_v2 ADD COLUMN email_notification_status VARCHAR(32) NOT NULL DEFAULT 'not_requested'")
    if "email_notification_attempts" not in columns:
        statements.append("ALTER TABLE literature_pushes_v2 ADD COLUMN email_notification_attempts INTEGER NOT NULL DEFAULT 0")
    if "email_notification_error" not in columns:
        statements.append("ALTER TABLE literature_pushes_v2 ADD COLUMN email_notification_error TEXT NOT NULL DEFAULT ''")
    if "email_notification_sent_at" not in columns:
        statements.append("ALTER TABLE literature_pushes_v2 ADD COLUMN email_notification_sent_at DATETIME")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_literature_pushes_v2_email_notification_status "
            "ON literature_pushes_v2 (email_notification_status)"
        ))


def _migrate_push_batch_fields(engine: Engine) -> None:
    inspector = inspect(engine)
    if "literature_pushes_v2" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("literature_pushes_v2")}
    with engine.begin() as connection:
        if "batch_id" not in columns:
            connection.execute(text(
                "ALTER TABLE literature_pushes_v2 ADD COLUMN batch_id VARCHAR(36) NOT NULL DEFAULT ''"
            ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_literature_pushes_v2_batch_id "
            "ON literature_pushes_v2 (batch_id)"
        ))

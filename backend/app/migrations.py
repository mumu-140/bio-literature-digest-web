from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


LEGACY_FAVORITE_COLUMNS = {
    "doi",
    "journal",
    "publish_date",
    "category",
    "interest_level",
    "interest_tag",
    "title_en",
    "title_zh",
    "article_url",
}


def _favorite_columns(engine: Engine) -> set[str]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "favorites" not in table_names:
        return set()
    return {column["name"] for column in inspector.get_columns("favorites")}


def _migrate_sqlite_favorites(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(
            text(
                """
                CREATE TABLE favorites_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    paper_id INTEGER NOT NULL,
                    favorited_at DATETIME NOT NULL,
                    CONSTRAINT uq_favorites_user_paper UNIQUE (user_id, paper_id),
                    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY(paper_id) REFERENCES papers (id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO favorites_new (id, user_id, paper_id, favorited_at)
                SELECT id, user_id, paper_id, favorited_at
                FROM favorites
                """
            )
        )
        connection.execute(text("DROP TABLE favorites"))
        connection.execute(text("ALTER TABLE favorites_new RENAME TO favorites"))
        connection.execute(text("CREATE INDEX ix_favorites_paper_id ON favorites (paper_id)"))
        connection.execute(text("CREATE INDEX ix_favorites_user_id ON favorites (user_id)"))
        connection.execute(text("PRAGMA foreign_keys=ON"))


def run_runtime_migrations(engine: Engine) -> None:
    columns = _favorite_columns(engine)
    if columns and (columns & LEGACY_FAVORITE_COLUMNS) and engine.dialect.name == "sqlite":
        _migrate_sqlite_favorites(engine)
    _migrate_favorite_review_fields(engine)
    _migrate_user_visibility_fields(engine)
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


def _migrate_favorite_review_fields(engine: Engine) -> None:
    columns = _favorite_columns(engine)
    if not columns:
        return
    statements: list[str] = []
    if "review_interest_level" not in columns:
        statements.append("ALTER TABLE favorites ADD COLUMN review_interest_level VARCHAR(64) NOT NULL DEFAULT ''")
    if "review_interest_tag" not in columns:
        statements.append("ALTER TABLE favorites ADD COLUMN review_interest_tag VARCHAR(255) NOT NULL DEFAULT ''")
    if "review_final_decision" not in columns:
        statements.append("ALTER TABLE favorites ADD COLUMN review_final_decision VARCHAR(32) NOT NULL DEFAULT ''")
    if "review_final_category" not in columns:
        statements.append("ALTER TABLE favorites ADD COLUMN review_final_category VARCHAR(128) NOT NULL DEFAULT ''")
    if "reviewer_notes" not in columns:
        statements.append("ALTER TABLE favorites ADD COLUMN reviewer_notes TEXT NOT NULL DEFAULT ''")
    if "review_updated_at" not in columns:
        statements.append("ALTER TABLE favorites ADD COLUMN review_updated_at DATETIME")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_favorites_review_updated_at ON favorites (review_updated_at)"))


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
        connection.execute(text("ALTER TABLE sessions ADD COLUMN auth_method VARCHAR(32) NOT NULL DEFAULT 'password'"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_auth_method ON sessions (auth_method)"))

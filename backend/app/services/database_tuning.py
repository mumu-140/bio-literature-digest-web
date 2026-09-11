from __future__ import annotations

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine


SQLITE_INDEX_STATEMENTS = {
    "imported_digest_memberships": (
        "CREATE INDEX IF NOT EXISTS ix_memberships_list_item_date ON imported_digest_memberships (list_type, literature_item_id, digest_date DESC)",
        "CREATE INDEX IF NOT EXISTS ix_memberships_list_date_item ON imported_digest_memberships (list_type, digest_date DESC, literature_item_id)",
    ),
    "imported_literature_items": (
        "CREATE INDEX IF NOT EXISTS ix_literature_publish_date_id ON imported_literature_items (publish_date DESC, id DESC)",
    ),
    "user_literature_favorites": (
        "CREATE INDEX IF NOT EXISTS ix_favorites_user_item_key ON user_literature_favorites (user_id, literature_item_key)",
    ),
}



def configure_sqlite_engine(engine: Engine) -> None:
    """Apply low-risk SQLite connection settings for concurrent web reads and imports."""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=-32768")
        cursor.close()


def install_performance_indexes(engine: Engine) -> None:
    """Create idempotent indexes used by the literature library hot paths."""
    if engine.dialect.name != "sqlite":
        return
    existing_tables = set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        for table_name, statements in SQLITE_INDEX_STATEMENTS.items():
            if table_name not in existing_tables:
                continue
            for statement in statements:
                connection.execute(text(statement))
        connection.execute(text("PRAGMA optimize"))

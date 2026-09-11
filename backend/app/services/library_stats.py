from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


STATS_TABLE = "paper_library_daily_stats"
NORMALIZED_DATE_SQL = (
    "CASE WHEN imported_literature_items.publish_date GLOB '????-??-??*' "
    "THEN substr(imported_literature_items.publish_date,1,10) "
    "ELSE coalesce(nullif(trim(imported_literature_items.publish_date),''),'unknown') END"
)


def ensure_library_stats(engine: Engine) -> None:
    """Create and populate the rebuildable daily library statistics table."""
    if engine.dialect.name != "sqlite":
        return
    tables = set(inspect(engine).get_table_names())
    if not {"imported_literature_items", "imported_digest_memberships"}.issubset(tables):
        return
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS paper_library_daily_stats ("
            "publish_date TEXT PRIMARY KEY, paper_count INTEGER NOT NULL)"
        ))
        count = connection.execute(text("SELECT count(*) FROM paper_library_daily_stats")).scalar_one()
        if not count:
            _refresh_connection(connection)


def refresh_library_stats(db: Session) -> None:
    """Refresh daily counts inside the caller's import transaction."""
    connection = db.connection()
    _ensure_stats_table(connection)
    _refresh_connection(connection)


def load_library_stats(db: Session) -> list[tuple[str, int]]:
    try:
        rows = db.execute(text(
            "SELECT publish_date,paper_count FROM paper_library_daily_stats ORDER BY publish_date DESC"
        ))
    except OperationalError:
        return []
    return [(str(row.publish_date), int(row.paper_count)) for row in rows]


def _ensure_stats_table(connection) -> None:
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS paper_library_daily_stats ("
        "publish_date TEXT PRIMARY KEY, paper_count INTEGER NOT NULL)"
    ))


def _refresh_connection(connection) -> None:
    connection.execute(text("DELETE FROM paper_library_daily_stats"))
    connection.execute(text(
        "INSERT INTO paper_library_daily_stats(publish_date,paper_count) "
        f"SELECT {NORMALIZED_DATE_SQL}, count(DISTINCT imported_literature_items.id) "
        "FROM imported_literature_items "
        "JOIN imported_digest_memberships ON imported_digest_memberships.literature_item_id=imported_literature_items.id "
        "WHERE imported_digest_memberships.list_type='digest' "
        "GROUP BY 1"
    ))

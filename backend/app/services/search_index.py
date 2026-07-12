from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


FTS_TABLE = "imported_literature_fts"


def search_index_available(db: Session) -> bool:
    """Return whether the optional SQLite FTS index is ready for queries."""
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return False
    return db.execute(text(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"
    ), {"name": FTS_TABLE}).scalar_one_or_none() is not None


def ensure_search_index(engine: Engine) -> None:
    """Create and synchronize the FTS5 index when the source table exists."""
    if engine.dialect.name != "sqlite":
        return
    tables = set(inspect(engine).get_table_names())
    if "imported_literature_items" not in tables:
        return
    index_exists = FTS_TABLE in tables
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS imported_literature_fts USING fts5("
            "title_en, title_zh, summary_zh, abstract, journal, interest_tag, "
            "content='imported_literature_items', content_rowid='id', tokenize='trigram')"
        ))
        connection.execute(text(
            "CREATE TRIGGER IF NOT EXISTS imported_literature_fts_ai AFTER INSERT ON imported_literature_items BEGIN "
            "INSERT INTO imported_literature_fts(rowid,title_en,title_zh,summary_zh,abstract,journal,interest_tag) "
            "VALUES (new.id,new.title_en,new.title_zh,new.summary_zh,new.abstract,new.journal,new.interest_tag); END"
        ))
        connection.execute(text(
            "CREATE TRIGGER IF NOT EXISTS imported_literature_fts_ad AFTER DELETE ON imported_literature_items BEGIN "
            "INSERT INTO imported_literature_fts(imported_literature_fts,rowid,title_en,title_zh,summary_zh,abstract,journal,interest_tag) "
            "VALUES ('delete',old.id,old.title_en,old.title_zh,old.summary_zh,old.abstract,old.journal,old.interest_tag); END"
        ))
        connection.execute(text(
            "CREATE TRIGGER IF NOT EXISTS imported_literature_fts_au AFTER UPDATE ON imported_literature_items BEGIN "
            "INSERT INTO imported_literature_fts(imported_literature_fts,rowid,title_en,title_zh,summary_zh,abstract,journal,interest_tag) "
            "VALUES ('delete',old.id,old.title_en,old.title_zh,old.summary_zh,old.abstract,old.journal,old.interest_tag); "
            "INSERT INTO imported_literature_fts(rowid,title_en,title_zh,summary_zh,abstract,journal,interest_tag) "
            "VALUES (new.id,new.title_en,new.title_zh,new.summary_zh,new.abstract,new.journal,new.interest_tag); END"
        ))
        if not index_exists:
            connection.execute(text("INSERT INTO imported_literature_fts(imported_literature_fts) VALUES ('rebuild')"))


def apply_full_text_filter(statement: Select, query: str) -> Select:
    """Filter a SQLAlchemy statement through the synchronized trigram FTS index."""
    phrase = query.strip().replace('"', '""')
    if not phrase:
        return statement
    return statement.where(
        text(
            "imported_literature_items.id IN ("
            "SELECT rowid FROM imported_literature_fts "
            "WHERE imported_literature_fts MATCH :fts_query)"
        ).bindparams(fts_query=f'"{phrase}"')
    )

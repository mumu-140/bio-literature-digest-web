from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .shared_database import SharedBase


class SharedActor(SharedBase):
    __tablename__ = "shared_actors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    favorites: Mapped[list["SharedActorFavorite"]] = relationship(back_populates="actor", cascade="all, delete-orphan")


class SharedLiteratureItem(SharedBase):
    __tablename__ = "shared_literature_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    doi: Mapped[str] = mapped_column(String(255), default="", index=True)
    canonical_url: Mapped[str] = mapped_column(Text, default="")
    article_url: Mapped[str] = mapped_column(Text, default="")
    journal: Mapped[str] = mapped_column(String(255), default="", index=True)
    publish_date: Mapped[str] = mapped_column(String(64), default="")
    publication_stage: Mapped[str] = mapped_column(String(64), default="journal")
    category: Mapped[str] = mapped_column(String(128), default="other", index=True)
    interest_level: Mapped[str] = mapped_column(String(64), default="一般", index=True)
    interest_score: Mapped[int] = mapped_column(Integer, default=3, index=True)
    interest_tag: Mapped[str] = mapped_column(String(255), default="其他")
    title_en: Mapped[str] = mapped_column(Text, default="")
    title_zh: Mapped[str] = mapped_column(Text, default="")
    summary_zh: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    publisher_family: Mapped[str] = mapped_column(String(128), default="")
    group_name: Mapped[str] = mapped_column(String(128), default="")
    authors_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_json: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships: Mapped[list["SharedDigestMembership"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    favorites: Mapped[list["SharedActorFavorite"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    aliases: Mapped[list["SharedLiteratureAlias"]] = relationship(back_populates="item", cascade="all, delete-orphan")


class SharedLiteratureAlias(SharedBase):
    __tablename__ = "shared_literature_aliases"
    __table_args__ = (UniqueConstraint("alias_type", "alias_value", name="uq_shared_literature_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias_type: Mapped[str] = mapped_column(String(32), index=True)
    alias_value: Mapped[str] = mapped_column(Text)
    item_id: Mapped[int] = mapped_column(ForeignKey("shared_literature_items.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item: Mapped[SharedLiteratureItem] = relationship(back_populates="aliases")


class SharedDigestRun(SharedBase):
    __tablename__ = "shared_digest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    run_dir: Mapped[str] = mapped_column(String(1024), default="")
    status: Mapped[str] = mapped_column(String(32), default="success")
    email_status: Mapped[str] = mapped_column(String(32), default="not_attempted")
    window_start_utc: Mapped[str] = mapped_column(String(64), default="")
    window_end_utc: Mapped[str] = mapped_column(String(64), default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["SharedDigestMembership"]] = relationship(back_populates="digest_run", cascade="all, delete-orphan")


class SharedDigestMembership(SharedBase):
    __tablename__ = "shared_digest_memberships"
    __table_args__ = (
        UniqueConstraint("digest_date", "list_type", "item_id", name="uq_shared_digest_membership"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shared_digest_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("shared_literature_items.id", ondelete="CASCADE"), index=True)
    digest_date: Mapped[date] = mapped_column(Date, index=True)
    list_type: Mapped[str] = mapped_column(String(32), index=True)
    publication_stage: Mapped[str] = mapped_column(String(64), default="journal")
    decision: Mapped[str] = mapped_column(String(32), default="")
    row_index: Mapped[int] = mapped_column(Integer, default=0)
    source_record_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    digest_run: Mapped[Optional[SharedDigestRun]] = relationship(back_populates="memberships")
    item: Mapped[SharedLiteratureItem] = relationship(back_populates="memberships")


class SharedActorFavorite(SharedBase):
    __tablename__ = "shared_actor_favorites"
    __table_args__ = (UniqueConstraint("actor_id", "item_id", name="uq_shared_actor_favorite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("shared_actors.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("shared_literature_items.id", ondelete="CASCADE"), index=True)
    favorited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    review_interest_level: Mapped[str] = mapped_column(String(64), default="")
    review_interest_tag: Mapped[str] = mapped_column(String(255), default="")
    review_final_decision: Mapped[str] = mapped_column(String(32), default="")
    review_final_category: Mapped[str] = mapped_column(String(128), default="")
    reviewer_notes: Mapped[str] = mapped_column(Text, default="")
    review_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    actor: Mapped[SharedActor] = relationship(back_populates="favorites")
    item: Mapped[SharedLiteratureItem] = relationship(back_populates="favorites")


class SharedExportJob(SharedBase):
    __tablename__ = "shared_export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shared_actors.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by_key: Mapped[str] = mapped_column(String(255), default="", index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_name: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(128), default="text/plain")
    content_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SharedActionLog(SharedBase):
    __tablename__ = "shared_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shared_actors.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

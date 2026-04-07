from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="member", index=True)
    user_group: Mapped[str] = mapped_column(String(32), default="internal", index=True)
    owner_admin_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    received_pushes: Mapped[list["PaperPush"]] = relationship(
        back_populates="recipient",
        cascade="all, delete-orphan",
        foreign_keys="PaperPush.recipient_user_id",
    )
    sent_pushes: Mapped[list["PaperPush"]] = relationship(
        back_populates="sender",
        cascade="all, delete-orphan",
        foreign_keys="PaperPush.sent_by_user_id",
    )
    managed_users: Mapped[list["User"]] = relationship(
        back_populates="owner_admin",
        foreign_keys="User.owner_admin_user_id",
    )
    owner_admin: Mapped[Optional["User"]] = relationship(
        back_populates="managed_users",
        remote_side="User.id",
        foreign_keys=[owner_admin_user_id],
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    auth_method: Mapped[str] = mapped_column(String(32), default="password", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class DigestRun(Base):
    __tablename__ = "digest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, index=True)
    work_dir: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="success")
    email_status: Mapped[str] = mapped_column(String(32), default="not_attempted")
    window_start_utc: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    window_end_utc: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    daily_entries: Mapped[list["PaperDailyEntry"]] = relationship(back_populates="digest_run", cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    doi: Mapped[str] = mapped_column(String(255), default="", index=True)
    journal: Mapped[str] = mapped_column(String(255), default="", index=True)
    category: Mapped[str] = mapped_column(String(128), default="other", index=True)
    publish_date: Mapped[str] = mapped_column(String(64), default="")
    interest_level: Mapped[str] = mapped_column(String(64), default="一般", index=True)
    interest_score: Mapped[int] = mapped_column(Integer, default=3, index=True)
    interest_tag: Mapped[str] = mapped_column(String(255), default="其他")
    title_en: Mapped[str] = mapped_column(Text, default="")
    title_zh: Mapped[str] = mapped_column(Text, default="")
    summary_zh: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    article_url: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    daily_entries: Mapped[list["PaperDailyEntry"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="paper")
    pushes: Mapped[list["PaperPush"]] = relationship(back_populates="paper", cascade="all, delete-orphan")


class PaperDailyEntry(Base):
    __tablename__ = "paper_daily_entries"
    __table_args__ = (UniqueConstraint("digest_date", "paper_id", name="uq_paper_daily_entries_date_paper"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_run_id: Mapped[int] = mapped_column(ForeignKey("digest_runs.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    digest_date: Mapped[date] = mapped_column(Date, index=True)
    publication_stage: Mapped[str] = mapped_column(String(64), default="journal")
    row_index: Mapped[int] = mapped_column(Integer, default=0)
    raw_record_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    digest_run: Mapped[DigestRun] = relationship(back_populates="daily_entries")
    paper: Mapped[Paper] = relationship(back_populates="daily_entries")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "paper_id", name="uq_favorites_user_paper"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    favorited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    review_interest_level: Mapped[str] = mapped_column(String(64), default="")
    review_interest_tag: Mapped[str] = mapped_column(String(255), default="")
    review_final_decision: Mapped[str] = mapped_column(String(32), default="")
    review_final_category: Mapped[str] = mapped_column(String(128), default="")
    reviewer_notes: Mapped[str] = mapped_column(Text, default="")
    review_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    user: Mapped[User] = relationship(back_populates="favorites")
    paper: Mapped[Paper] = relationship(back_populates="favorites")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(32), index=True)
    month: Mapped[str] = mapped_column(String(16), index=True)
    snapshot_kind: Mapped[str] = mapped_column(String(32), default="network", index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    total_papers: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)

    nodes: Mapped[list["AnalyticsNode"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    edges: Mapped[list["AnalyticsEdge"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class AnalyticsNode(Base):
    __tablename__ = "analytics_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("analytics_snapshots.id", ondelete="CASCADE"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    label: Mapped[str] = mapped_column(String(255))
    weight: Mapped[int] = mapped_column(Integer, default=0)

    snapshot: Mapped[AnalyticsSnapshot] = relationship(back_populates="nodes")


class AnalyticsEdge(Base):
    __tablename__ = "analytics_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("analytics_snapshots.id", ondelete="CASCADE"), index=True)
    source_key: Mapped[str] = mapped_column(String(255), index=True)
    target_key: Mapped[str] = mapped_column(String(255), index=True)
    weight: Mapped[int] = mapped_column(Integer, default=0)

    snapshot: Mapped[AnalyticsSnapshot] = relationship(back_populates="edges")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128), default="text/plain")
    content_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PaperPush(Base):
    __tablename__ = "paper_pushes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sent_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pushed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    paper: Mapped[Paper] = relationship(back_populates="pushes")
    recipient: Mapped[User] = relationship(back_populates="received_pushes", foreign_keys=[recipient_user_id])
    sender: Mapped[User] = relationship(back_populates="sent_pushes", foreign_keys=[sent_by_user_id])

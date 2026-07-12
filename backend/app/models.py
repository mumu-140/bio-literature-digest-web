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
    password_hash: Mapped[str] = mapped_column(String(255), default="passwordless")
    role: Mapped[str] = mapped_column(String(32), default="member", index=True)
    user_group: Mapped[str] = mapped_column(String(32), default="internal", index=True)
    owner_admin_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    producer_uid: Mapped[str] = mapped_column(String(128), default="", index=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    imported_favorites: Mapped[list["UserLiteratureFavorite"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    manual_reviews: Mapped[list["UserManualReview"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    received_imported_pushes: Mapped[list["LiteraturePushV2"]] = relationship(
        back_populates="recipient",
        cascade="all, delete-orphan",
        foreign_keys="LiteraturePushV2.recipient_user_id",
    )
    sent_imported_pushes: Mapped[list["LiteraturePushV2"]] = relationship(
        back_populates="sender",
        cascade="all, delete-orphan",
        foreign_keys="LiteraturePushV2.sent_by_user_id",
    )
    export_jobs_v2: Mapped[list["UserExportJobV2"]] = relationship(back_populates="requested_by")
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
    auth_method: Mapped[str] = mapped_column(String(32), default="passwordless", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


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


class ImportedLiteratureItem(Base):
    __tablename__ = "imported_literature_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    literature_item_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    doi: Mapped[str] = mapped_column(String(255), default="", index=True)
    canonical_url: Mapped[str] = mapped_column(Text, default="")
    article_url: Mapped[str] = mapped_column(Text, default="")
    journal: Mapped[str] = mapped_column(String(255), default="", index=True)
    publish_date: Mapped[str] = mapped_column(String(64), default="")
    publication_stage: Mapped[str] = mapped_column(String(64), default="journal")
    category: Mapped[str] = mapped_column(String(128), default="other", index=True)
    interest_level: Mapped[str] = mapped_column(String(64), default="一般", index=True)
    interest_score: Mapped[int] = mapped_column(Integer, default=3, index=True)
    interest_tag: Mapped[str] = mapped_column(String(255), default="")
    title_en: Mapped[str] = mapped_column(Text, default="")
    title_zh: Mapped[str] = mapped_column(Text, default="")
    summary_zh: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    source_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    publisher_family: Mapped[str] = mapped_column(String(128), default="")
    group_name: Mapped[str] = mapped_column(String(128), default="")
    authors_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_json: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships: Mapped[list["ImportedDigestMembership"]] = relationship(
        back_populates="literature_item",
        cascade="all, delete-orphan",
    )
    favorites_v2: Mapped[list["UserLiteratureFavorite"]] = relationship(back_populates="literature_item")
    manual_reviews: Mapped[list["UserManualReview"]] = relationship(back_populates="literature_item")
    pushes_v2: Mapped[list["LiteraturePushV2"]] = relationship(back_populates="literature_item")


class ImportedDigestRun(Base):
    __tablename__ = "imported_digest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    source_run_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    source_updated_at_utc: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_status: Mapped[str] = mapped_column(String(32), default="")
    source_email_status: Mapped[str] = mapped_column(String(32), default="")
    source_work_dir: Mapped[str] = mapped_column(String(1024), default="")
    source_window_start_utc: Mapped[str] = mapped_column(String(64), default="")
    source_window_end_utc: Mapped[str] = mapped_column(String(64), default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_validation_status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    artifact_validation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships: Mapped[list["ImportedDigestMembership"]] = relationship(
        back_populates="digest_run",
        cascade="all, delete-orphan",
    )


class ImportedDigestMembership(Base):
    __tablename__ = "imported_digest_memberships"
    __table_args__ = (
        UniqueConstraint(
            "digest_date",
            "list_type",
            "literature_item_key",
            name="uq_imported_digest_membership",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imported_digest_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    literature_item_id: Mapped[int] = mapped_column(
        ForeignKey("imported_literature_items.id", ondelete="CASCADE"),
        index=True,
    )
    literature_item_key: Mapped[str] = mapped_column(String(512), index=True)
    digest_date: Mapped[date] = mapped_column(Date, index=True)
    list_type: Mapped[str] = mapped_column(String(32), index=True)
    publication_stage: Mapped[str] = mapped_column(String(64), default="journal")
    decision: Mapped[str] = mapped_column(String(32), default="")
    row_index: Mapped[int] = mapped_column(Integer, default=0)
    source_record_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    digest_run: Mapped[Optional[ImportedDigestRun]] = relationship(back_populates="memberships")
    literature_item: Mapped[ImportedLiteratureItem] = relationship(back_populates="memberships")


class ProducerImportLedger(Base):
    __tablename__ = "producer_import_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    source_run_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    source_updated_at_utc: Mapped[str] = mapped_column(String(64), default="", index=True)
    trigger: Mapped[str] = mapped_column(String(32), default="startup", index=True)
    result_status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    imported_items_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_memberships_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_missing_key_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_membership_count: Mapped[int] = mapped_column(Integer, default=0)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class UserLiteratureFavorite(Base):
    __tablename__ = "user_literature_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "literature_item_key", name="uq_user_literature_favorite"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    literature_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imported_literature_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    literature_item_key: Mapped[str] = mapped_column(String(512), index=True)
    favorited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="imported_favorites")
    literature_item: Mapped[Optional[ImportedLiteratureItem]] = relationship(back_populates="favorites_v2")


class UserManualReview(Base):
    __tablename__ = "user_manual_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "literature_item_key", name="uq_user_manual_review"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    literature_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imported_literature_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    literature_item_key: Mapped[str] = mapped_column(String(512), index=True)
    review_interest_level: Mapped[str] = mapped_column(String(64), default="")
    review_interest_tag: Mapped[str] = mapped_column(String(255), default="")
    review_final_decision: Mapped[str] = mapped_column(String(32), default="")
    review_final_category: Mapped[str] = mapped_column(String(128), default="")
    reviewer_notes: Mapped[str] = mapped_column(Text, default="")
    review_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="manual_reviews")
    literature_item: Mapped[Optional[ImportedLiteratureItem]] = relationship(back_populates="manual_reviews")


class UserExportJobV2(Base):
    __tablename__ = "user_export_jobs_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requested_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by_key: Mapped[str] = mapped_column(String(255), default="", index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_name: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(128), default="text/plain")
    content_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    requested_by: Mapped[Optional[User]] = relationship(back_populates="export_jobs_v2")


class LiteraturePushV2(Base):
    __tablename__ = "literature_pushes_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    literature_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imported_literature_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    literature_item_key: Mapped[str] = mapped_column(String(512), index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sent_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pushed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    literature_item: Mapped[Optional[ImportedLiteratureItem]] = relationship(back_populates="pushes_v2")
    recipient: Mapped[User] = relationship(back_populates="received_imported_pushes", foreign_keys=[recipient_user_id])
    sender: Mapped[User] = relationship(back_populates="sent_imported_pushes", foreign_keys=[sent_by_user_id])

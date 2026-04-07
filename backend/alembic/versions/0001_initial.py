"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-06 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)

    op.create_table(
        "digest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("work_dir", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("email_status", sa.String(length=32), nullable=False),
        sa.Column("window_start_utc", sa.String(length=64), nullable=True),
        sa.Column("window_end_utc", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_digest_runs_digest_date", "digest_runs", ["digest_date"], unique=False)

    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_key", sa.String(length=512), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("journal", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("publish_date", sa.String(length=64), nullable=False),
        sa.Column("interest_level", sa.String(length=64), nullable=False),
        sa.Column("interest_score", sa.Integer(), nullable=False),
        sa.Column("interest_tag", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("title_zh", sa.Text(), nullable=False),
        sa.Column("summary_zh", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("article_url", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("extra_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_papers_canonical_key", "papers", ["canonical_key"], unique=True)
    op.create_index("ix_papers_doi", "papers", ["doi"], unique=False)
    op.create_index("ix_papers_journal", "papers", ["journal"], unique=False)
    op.create_index("ix_papers_category", "papers", ["category"], unique=False)
    op.create_index("ix_papers_interest_level", "papers", ["interest_level"], unique=False)
    op.create_index("ix_papers_interest_score", "papers", ["interest_score"], unique=False)

    op.create_table(
        "paper_daily_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("digest_run_id", sa.Integer(), sa.ForeignKey("digest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("publication_stage", sa.String(length=64), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("raw_record_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("digest_date", "paper_id", name="uq_paper_daily_entries_date_paper"),
    )
    op.create_index("ix_paper_daily_entries_digest_run_id", "paper_daily_entries", ["digest_run_id"], unique=False)
    op.create_index("ix_paper_daily_entries_paper_id", "paper_daily_entries", ["paper_id"], unique=False)
    op.create_index("ix_paper_daily_entries_digest_date", "paper_daily_entries", ["digest_date"], unique=False)

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("journal", sa.String(length=255), nullable=False),
        sa.Column("publish_date", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("interest_level", sa.String(length=64), nullable=False),
        sa.Column("interest_tag", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("title_zh", sa.Text(), nullable=False),
        sa.Column("article_url", sa.Text(), nullable=False),
        sa.Column("favorited_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "paper_id", name="uq_favorites_user_paper"),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"], unique=False)
    op.create_index("ix_favorites_paper_id", "favorites", ["paper_id"], unique=False)

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("month", sa.String(length=16), nullable=False),
        sa.Column("snapshot_kind", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("total_papers", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_analytics_snapshots_scope_type", "analytics_snapshots", ["scope_type"], unique=False)
    op.create_index("ix_analytics_snapshots_user_id", "analytics_snapshots", ["user_id"], unique=False)
    op.create_index("ix_analytics_snapshots_period", "analytics_snapshots", ["period"], unique=False)
    op.create_index("ix_analytics_snapshots_month", "analytics_snapshots", ["month"], unique=False)
    op.create_index("ix_analytics_snapshots_snapshot_kind", "analytics_snapshots", ["snapshot_kind"], unique=False)
    op.create_index("ix_analytics_snapshots_generated_at", "analytics_snapshots", ["generated_at"], unique=False)

    op.create_table(
        "analytics_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("analytics_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_key", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
    )
    op.create_index("ix_analytics_nodes_snapshot_id", "analytics_nodes", ["snapshot_id"], unique=False)
    op.create_index("ix_analytics_nodes_node_key", "analytics_nodes", ["node_key"], unique=False)

    op.create_table(
        "analytics_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("analytics_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("target_key", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
    )
    op.create_index("ix_analytics_edges_snapshot_id", "analytics_edges", ["snapshot_id"], unique=False)
    op.create_index("ix_analytics_edges_source_key", "analytics_edges", ["source_key"], unique=False)
    op.create_index("ix_analytics_edges_target_key", "analytics_edges", ["target_key"], unique=False)

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("output_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_export_jobs_requested_by", "export_jobs", ["requested_by"], unique=False)
    op.create_index("ix_export_jobs_kind", "export_jobs", ["kind"], unique=False)
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_kind", table_name="export_jobs")
    op.drop_index("ix_export_jobs_requested_by", table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index("ix_analytics_edges_target_key", table_name="analytics_edges")
    op.drop_index("ix_analytics_edges_source_key", table_name="analytics_edges")
    op.drop_index("ix_analytics_edges_snapshot_id", table_name="analytics_edges")
    op.drop_table("analytics_edges")
    op.drop_index("ix_analytics_nodes_node_key", table_name="analytics_nodes")
    op.drop_index("ix_analytics_nodes_snapshot_id", table_name="analytics_nodes")
    op.drop_table("analytics_nodes")
    op.drop_index("ix_analytics_snapshots_generated_at", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_snapshot_kind", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_month", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_period", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_user_id", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_scope_type", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
    op.drop_index("ix_favorites_paper_id", table_name="favorites")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_table("favorites")
    op.drop_index("ix_paper_daily_entries_digest_date", table_name="paper_daily_entries")
    op.drop_index("ix_paper_daily_entries_paper_id", table_name="paper_daily_entries")
    op.drop_index("ix_paper_daily_entries_digest_run_id", table_name="paper_daily_entries")
    op.drop_table("paper_daily_entries")
    op.drop_index("ix_papers_interest_score", table_name="papers")
    op.drop_index("ix_papers_interest_level", table_name="papers")
    op.drop_index("ix_papers_category", table_name="papers")
    op.drop_index("ix_papers_journal", table_name="papers")
    op.drop_index("ix_papers_doi", table_name="papers")
    op.drop_index("ix_papers_canonical_key", table_name="papers")
    op.drop_table("papers")
    op.drop_index("ix_digest_runs_digest_date", table_name="digest_runs")
    op.drop_table("digest_runs")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

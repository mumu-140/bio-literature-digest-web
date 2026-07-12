"""action logs

Revision ID: 0003_action_logs
Revises: 0002_paper_pushes
Create Date: 2026-04-06 01:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_action_logs"
down_revision = "0002_paper_pushes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_action_logs_actor_user_id", "action_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_action_logs_target_user_id", "action_logs", ["target_user_id"], unique=False)
    op.create_index("ix_action_logs_action_type", "action_logs", ["action_type"], unique=False)
    op.create_index("ix_action_logs_entity_id", "action_logs", ["entity_id"], unique=False)
    op.create_index("ix_action_logs_created_at", "action_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_action_logs_created_at", table_name="action_logs")
    op.drop_index("ix_action_logs_entity_id", table_name="action_logs")
    op.drop_index("ix_action_logs_action_type", table_name="action_logs")
    op.drop_index("ix_action_logs_target_user_id", table_name="action_logs")
    op.drop_index("ix_action_logs_actor_user_id", table_name="action_logs")
    op.drop_table("action_logs")

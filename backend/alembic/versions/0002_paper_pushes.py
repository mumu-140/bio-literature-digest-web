"""paper pushes

Revision ID: 0002_paper_pushes
Revises: 0001_initial
Create Date: 2026-04-06 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_paper_pushes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_pushes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sent_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("pushed_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_paper_pushes_paper_id", "paper_pushes", ["paper_id"], unique=False)
    op.create_index("ix_paper_pushes_recipient_user_id", "paper_pushes", ["recipient_user_id"], unique=False)
    op.create_index("ix_paper_pushes_sent_by_user_id", "paper_pushes", ["sent_by_user_id"], unique=False)
    op.create_index("ix_paper_pushes_is_read", "paper_pushes", ["is_read"], unique=False)
    op.create_index("ix_paper_pushes_pushed_at", "paper_pushes", ["pushed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_paper_pushes_pushed_at", table_name="paper_pushes")
    op.drop_index("ix_paper_pushes_is_read", table_name="paper_pushes")
    op.drop_index("ix_paper_pushes_sent_by_user_id", table_name="paper_pushes")
    op.drop_index("ix_paper_pushes_recipient_user_id", table_name="paper_pushes")
    op.drop_index("ix_paper_pushes_paper_id", table_name="paper_pushes")
    op.drop_table("paper_pushes")

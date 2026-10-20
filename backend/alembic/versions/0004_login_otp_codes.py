"""login otp codes

Revision ID: 0004_login_otp_codes
Revises: 0003_action_logs
Create Date: 2026-10-20 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_login_otp_codes"
down_revision = "0003_action_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_otp_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("attempts_remaining", sa.Integer(), nullable=False),
        sa.Column("created_ip", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_login_otp_codes_email", "login_otp_codes", ["email"], unique=False)
    op.create_index("ix_login_otp_codes_code_hash", "login_otp_codes", ["code_hash"], unique=False)
    op.create_index("ix_login_otp_codes_created_at", "login_otp_codes", ["created_at"], unique=False)
    op.create_index("ix_login_otp_codes_expires_at", "login_otp_codes", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_login_otp_codes_expires_at", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_created_at", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_code_hash", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_email", table_name="login_otp_codes")
    op.drop_table("login_otp_codes")

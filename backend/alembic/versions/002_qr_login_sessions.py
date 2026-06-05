"""qr login sessions

Revision ID: 002
Revises: 001
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qr_login_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("qrcode_base64", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_qr_login_sessions_session_id", "qr_login_sessions", ["session_id"])
    op.create_index("ix_qr_login_sessions_user_id", "qr_login_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_qr_login_sessions_user_id", table_name="qr_login_sessions")
    op.drop_index("ix_qr_login_sessions_session_id", table_name="qr_login_sessions")
    op.drop_table("qr_login_sessions")

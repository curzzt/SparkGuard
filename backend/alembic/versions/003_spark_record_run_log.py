"""spark record run log and screenshot

Revision ID: 003
Revises: 002
Create Date: 2026-06-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("spark_records", sa.Column("run_log", sa.Text(), nullable=True))
    op.add_column("spark_records", sa.Column("screenshot_base64", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("spark_records", "screenshot_base64")
    op.drop_column("spark_records", "run_log")

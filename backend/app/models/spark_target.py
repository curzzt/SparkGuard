from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BigIntPKMixin, TimestampMixin


class SparkTarget(BigIntPKMixin, TimestampMixin, Base):
    __tablename__ = "spark_targets"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    douyin_account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("douyin_accounts.id", ondelete="CASCADE")
    )
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receiver_id: Mapped[str] = mapped_column(String(128), nullable=False)
    custom_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

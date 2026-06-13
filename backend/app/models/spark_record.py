from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BigIntPKMixin


class SparkRecord(BigIntPKMixin, Base):
    __tablename__ = "spark_records"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    douyin_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("douyin_accounts.id", ondelete="SET NULL"), nullable=True
    )
    target_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("spark_targets.id", ondelete="SET NULL"), nullable=True
    )
    execute_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    execute_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_decision: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

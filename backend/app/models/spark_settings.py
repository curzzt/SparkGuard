from datetime import date, datetime, time

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BigIntPKMixin, TimestampMixin


class SparkSettings(BigIntPKMixin, Base):
    __tablename__ = "spark_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_spark_settings_user_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    douyin_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    execute_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(9, 0))
    default_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    random_template_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    skip_today: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

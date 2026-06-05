from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spark_job_lock import SparkJobLock
from app.models.spark_record import SparkRecord
from app.models.spark_target import SparkTarget


@dataclass
class JobResult:
    ok: bool = False
    failed: bool = False
    skip: bool = False
    reason: str | None = None
    should_mark_scheduled: bool = False


class RecordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        status: str,
        channel: str = "none",
        douyin_account_id: int | None = None,
        target_id: int | None = None,
        message: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        agent_decision: dict | None = None,
        execute_date: date | None = None,
    ) -> SparkRecord:
        from app.utils.datetime import local_now

        now = local_now()
        record = SparkRecord(
            user_id=user_id,
            douyin_account_id=douyin_account_id,
            target_id=target_id,
            execute_date=execute_date or now.date(),
            execute_time=now,
            message=message,
            channel=channel,
            status=status,
            error_code=error_code,
            error_message=error_message,
            agent_decision=agent_decision,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_records(self, user_id: int, days: int = 7, page: int = 1, page_size: int = 20) -> dict:
        from app.utils.datetime import local_now

        start_date = local_now().date() - timedelta(days=days - 1)
        base = select(SparkRecord).where(SparkRecord.user_id == user_id, SparkRecord.execute_date >= start_date)
        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.scalars(
            base.order_by(SparkRecord.execute_time.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        records = result.all()
        target_ids = [r.target_id for r in records if r.target_id]
        nicknames: dict[int, str] = {}
        if target_ids:
            targets = await self.db.scalars(select(SparkTarget).where(SparkTarget.id.in_(target_ids)))
            nicknames = {t.id: t.nickname for t in targets.all()}
        items = [
            {
                "id": r.id,
                "execute_date": r.execute_date.isoformat(),
                "execute_time": r.execute_time.isoformat(),
                "target_nickname": nicknames.get(r.target_id) if r.target_id else None,
                "message": r.message,
                "channel": r.channel,
                "status": r.status,
                "error_message": r.error_message,
            }
            for r in records
        ]
        return {"items": items, "total": total or 0}

    async def get_today_status(self, user_id: int) -> dict:
        from app.utils.datetime import local_now

        today = local_now().date()
        records = await self.db.scalars(
            select(SparkRecord).where(SparkRecord.user_id == user_id, SparkRecord.execute_date == today)
        )
        all_records = records.all()
        target_count = await self.db.scalar(
            select(func.count()).select_from(SparkTarget).where(
                SparkTarget.user_id == user_id, SparkTarget.enabled.is_(True)
            )
        )
        success_count = sum(1 for r in all_records if r.status == "success")
        failed_count = sum(1 for r in all_records if r.status in ("failed", "auth_expired"))
        unsupported_count = sum(1 for r in all_records if r.status == "unsupported")
        skipped_count = sum(1 for r in all_records if r.status == "skipped")
        last_execute_at = max((r.execute_time for r in all_records), default=None)
        lock = await self.db.scalar(select(SparkJobLock).where(SparkJobLock.user_id == user_id))
        now = datetime.now(timezone.utc)
        if lock and lock.expires_at > now:
            job_status = "running"
        elif skipped_count and not success_count and not failed_count and not unsupported_count:
            job_status = "skipped"
        elif not all_records:
            job_status = "pending"
        elif success_count + failed_count + unsupported_count >= (target_count or 0) and target_count:
            if failed_count or unsupported_count:
                job_status = "partial"
            else:
                job_status = "completed"
        elif all_records:
            job_status = "partial"
        else:
            job_status = "pending"
        return {
            "execute_date": today.isoformat(),
            "target_count": target_count or 0,
            "success_count": success_count,
            "failed_count": failed_count,
            "unsupported_count": unsupported_count,
            "skipped_count": skipped_count,
            "job_status": job_status,
            "last_execute_at": last_execute_at.isoformat() if last_execute_at else None,
        }

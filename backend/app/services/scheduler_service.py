from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spark_job_lock import SparkJobLock


class SchedulerService:
    LOCK_OWNER = "sparkguard"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def try_acquire_user_lock(self, user_id: int, ttl_seconds: int = 600) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        await self.db.execute(delete(SparkJobLock).where(SparkJobLock.expires_at <= now))
        stmt = (
            insert(SparkJobLock)
            .values(user_id=user_id, locked_at=now, lock_owner=self.LOCK_OWNER, expires_at=expires_at)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def release_user_lock(self, user_id: int) -> None:
        await self.db.execute(delete(SparkJobLock).where(SparkJobLock.user_id == user_id))

    async def is_locked(self, user_id: int) -> bool:
        lock = await self.db.scalar(select(SparkJobLock).where(SparkJobLock.user_id == user_id))
        if not lock:
            return False
        if lock.expires_at <= datetime.now(timezone.utc):
            await self.release_user_lock(user_id)
            return False
        return True

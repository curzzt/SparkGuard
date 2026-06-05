import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.jobs.spark_executor import run_user_spark_job_safe
from app.models.spark_settings import SparkSettings
from app.models.user import User
from app.utils.datetime import local_now

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=get_settings().TIMEZONE)


async def scan_due_spark_jobs() -> None:
    now = local_now()
    today = now.date()
    current_time = now.time()

    async with async_session_factory() as db:
        result = await db.execute(
            select(SparkSettings, User.status)
            .join(User, User.id == SparkSettings.user_id)
            .where(
                SparkSettings.enabled.is_(True),
                SparkSettings.skip_today.is_(False),
                (SparkSettings.last_scheduled_date.is_(None) | (SparkSettings.last_scheduled_date < today)),
                SparkSettings.execute_time <= current_time,
            )
        )
        rows = result.all()

    for settings, user_status in rows:
        if user_status != "active":
            continue
        asyncio.create_task(run_user_spark_job_safe(settings.user_id, trigger="scheduler"))


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(scan_due_spark_jobs, "cron", minute="*", id="scan_due_spark_jobs", replace_existing=True)
        scheduler.start()
        logger.info("APScheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")

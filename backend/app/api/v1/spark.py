from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import job_session_factory
from app.core.deps import get_current_user, get_db
from app.core.errors import AppError, success
from app.core.rate_limit import limiter
from app.jobs.spark_executor import execute_spark_for_user
from app.models.user import User
from app.schemas.spark import (
    BatchIdsRequest,
    SparkSettingsUpdate,
    SparkTargetCreate,
    SparkTargetUpdate,
)
from app.services.record_service import RecordService
from app.services.scheduler_service import SchedulerService
from app.services.spark_settings_service import SparkSettingsService
from app.services.spark_target_service import SparkTargetService

router = APIRouter(prefix="/spark", tags=["spark"])


@router.get("/targets")
async def list_targets(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await SparkTargetService(db).list_targets(current_user.id)
    return success(data)


@router.post("/targets")
async def create_target(
    body: SparkTargetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await SparkTargetService(db).create_target(current_user.id, body.model_dump())
    return success(data)


@router.put("/targets/{target_id}")
async def update_target(
    target_id: int,
    body: SparkTargetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await SparkTargetService(db).update_target(
        current_user.id, target_id, body.model_dump(exclude_unset=True)
    )
    return success(data)


@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await SparkTargetService(db).delete_target(current_user.id, target_id)
    return success({"success": True})


@router.post("/targets/batch-enable")
async def batch_enable(
    body: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await SparkTargetService(db).batch_enable(current_user.id, body.ids, True)
    return success({"success": True})


@router.post("/targets/batch-disable")
async def batch_disable(
    body: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await SparkTargetService(db).batch_enable(current_user.id, body.ids, False)
    return success({"success": True})


@router.get("/settings")
async def get_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await SparkSettingsService(db).get_settings_dict(current_user.id)
    return success(data)


@router.put("/settings")
async def update_settings(
    body: SparkSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await SparkSettingsService(db).update_settings(
        current_user.id, body.model_dump(exclude_unset=True)
    )
    return success(data)


@router.post("/run-now")
@limiter.limit("2/hour")
async def run_now(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    async with job_session_factory() as job_db:
        scheduler_service = SchedulerService(job_db)
        if await scheduler_service.is_locked(current_user.id):
            raise AppError(4001, 409)
        acquired = await scheduler_service.try_acquire_user_lock(current_user.id)
        if not acquired:
            raise AppError(4001, 409)
        await job_db.commit()
        try:
            await execute_spark_for_user(job_db, current_user.id, trigger="manual")
            await SparkSettingsService(job_db).mark_scheduled_today(current_user.id)
            await job_db.commit()
        except Exception:
            await job_db.rollback()
            raise
        finally:
            async with job_session_factory() as release_db:
                await SchedulerService(release_db).release_user_lock(current_user.id)
                await release_db.commit()
    return success({"job_status": "running", "message": "任务已触发"})


@router.post("/skip-today")
async def skip_today(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await SparkSettingsService(db).skip_today(current_user.id)
    return success(data)


@router.get("/today-status")
async def today_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await RecordService(db).get_today_status(current_user.id)
    return success(data)


@router.get("/records")
async def records(
    days: int = Query(7, ge=1, le=30),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await RecordService(db).list_records(current_user.id, days=days, page=page, page_size=page_size)
    return success(data)

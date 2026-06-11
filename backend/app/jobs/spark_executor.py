from app.services.agent_service import AgentService
from app.services.douyin_session_service import DouyinSessionService
from app.services.record_service import JobResult, RecordService
from app.services.scheduler_service import SchedulerService
from app.services.sender_service import SenderService
from app.services.spark_settings_service import SparkSettingsService
from app.services.spark_target_service import SparkTargetService
from app.utils.content_checker import is_compliant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def _friend_label(target) -> str:
    rid = (target.receiver_id or "").strip()
    nick = (target.nickname or "").strip()
    return rid or nick


async def execute_spark_for_user(db: AsyncSession, user_id: int, trigger: str = "scheduler") -> JobResult:
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or user.status != "active":
        return JobResult(skip=True, reason="invalid_user")

    session_service = DouyinSessionService(db)
    record_service = RecordService(db)
    target_service = SparkTargetService(db)
    settings_service = SparkSettingsService(db)
    agent_service = AgentService()
    sender_service = SenderService(db)

    account = await session_service.get_account_entity(user_id)
    if not account:
        await record_service.create(user_id, status="auth_expired", error_message="未绑定抖音账号")
        return JobResult(failed=True, reason="auth_expired")

    if account.auth_status != "active":
        await record_service.create(
            user_id,
            status="auth_expired",
            douyin_account_id=account.id,
            error_message="抖音登录态已失效，请重新扫码关联",
        )
        return JobResult(failed=True, reason="auth_expired")

    session_ok = await session_service.ensure_valid_session(account)
    if not session_ok:
        await record_service.create(
            user_id,
            status="auth_expired",
            douyin_account_id=account.id,
            error_message="抖音登录态已失效，请重新扫码关联",
        )
        return JobResult(failed=True, reason="auth_expired")

    settings = await settings_service.get_or_create_settings(user_id)
    if settings.skip_today:
        await record_service.create(user_id, status="skipped", error_message="今日已跳过")
        return JobResult(ok=True, reason="skipped")

    targets = await target_service.list_enabled_targets(user_id, settings.daily_limit)
    if not targets:
        await record_service.create(user_id, status="no_target", error_message="无可执行对象")
        return JobResult(ok=True, reason="no_target", should_mark_scheduled=True)

    for target in targets:
        agent_result = await agent_service.build_message(settings, target)
        compliant, reason = is_compliant(agent_result.message)
        if not compliant:
            await record_service.create(
                user_id,
                status="failed",
                douyin_account_id=account.id,
                target_id=target.id,
                message=agent_result.message,
                error_message=reason,
                agent_decision=agent_result.to_dict(),
            )
            await target_service.update_last_run(target.id, "failed", reason)
            continue

        send_result = await sender_service.send(account, _friend_label(target), agent_result.message)
        status = send_result.status

        if status == "failed":
            retry_result = await sender_service.send(account, _friend_label(target), agent_result.message)
            if retry_result.status == "success":
                status = "success"
                send_result = retry_result
            elif retry_result.status == "auth_expired":
                status = "auth_expired"
                send_result = retry_result

        await record_service.create(
            user_id,
            status=status,
            channel=send_result.channel,
            douyin_account_id=account.id,
            target_id=target.id,
            message=agent_result.message,
            error_code=send_result.error_code,
            error_message=send_result.error_message,
            agent_decision=agent_result.to_dict(),
        )
        await target_service.update_last_run(target.id, status, send_result.error_message)

        if status == "auth_expired":
            return JobResult(failed=True, reason="auth_expired", should_mark_scheduled=True)

    return JobResult(ok=True, should_mark_scheduled=True)


async def run_user_spark_job_safe(user_id: int, trigger: str = "scheduler") -> None:
    from app.core.database import job_session_factory

    async with job_session_factory() as db:
        scheduler_service = SchedulerService(db)
        acquired = await scheduler_service.try_acquire_user_lock(user_id)
        if not acquired:
            return
        try:
            result = await execute_spark_for_user(db, user_id, trigger=trigger)
            if result.should_mark_scheduled:
                settings_service = SparkSettingsService(db)
                await settings_service.mark_scheduled_today(user_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            async with job_session_factory() as release_db:
                release_scheduler = SchedulerService(release_db)
                await release_scheduler.release_user_lock(user_id)
                await release_db.commit()

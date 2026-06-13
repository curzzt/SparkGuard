import logging

from app.services.agent_service import AgentService
from app.services.douyin_session_service import DouyinSessionService
from app.services.record_service import JobResult, RecordService
from app.services.scheduler_service import SchedulerService
from app.services.sender_service import SenderService
from app.services.spark_settings_service import SparkSettingsService
from app.services.spark_target_service import SparkTargetService
from app.utils.content_checker import is_compliant
from app.utils.datetime import local_now
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger("app.spark")


def _friend_label(target) -> str:
    rid = (target.receiver_id or "").strip()
    nick = (target.nickname or "").strip()
    return rid or nick


class _RunLog:
    def __init__(self, user_id: int, trigger: str, scope: str):
        self.user_id = user_id
        self.trigger = trigger
        self.scope = scope
        self.lines: list[str] = []

    def step(self, message: str) -> None:
        stamp = local_now().strftime("%H:%M:%S")
        self.lines.append(f"[{stamp}] {message}")
        logger.info(
            "spark_run user=%s trigger=%s scope=%s | %s",
            self.user_id,
            self.trigger,
            self.scope,
            message,
        )

    def text(self) -> str:
        return "\n".join(self.lines)


async def execute_spark_for_user(db: AsyncSession, user_id: int, trigger: str = "scheduler") -> JobResult:
    record_service = RecordService(db)
    run = _RunLog(user_id, trigger, "preflight")
    run.step(f"开始执行（触发方式={trigger}）")

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or user.status != "active":
        run.step("用户不存在或未激活，终止")
        return JobResult(skip=True, reason="invalid_user")

    session_service = DouyinSessionService(db)
    target_service = SparkTargetService(db)
    settings_service = SparkSettingsService(db)
    agent_service = AgentService()
    sender_service = SenderService(db)

    account = await session_service.get_account_entity(user_id)
    if not account:
        run.step("未绑定抖音账号，终止")
        await record_service.create(user_id, status="auth_expired", error_message="未绑定抖音账号", run_log=run.text())
        await db.commit()
        return JobResult(failed=True, reason="auth_expired")

    if account.auth_status != "active":
        run.step(f"账号登录态非 active（当前={account.auth_status}），终止")
        await record_service.create(
            user_id,
            status="auth_expired",
            douyin_account_id=account.id,
            error_message="抖音登录态已失效，请重新扫码关联",
            run_log=run.text(),
        )
        await db.commit()
        return JobResult(failed=True, reason="auth_expired")

    run.step("校验抖音登录态（启动浏览器打开抖音）…")
    session_ok = await session_service.ensure_valid_session(account)
    if not session_ok:
        run.step("登录态校验未通过（登录态失效或浏览器被风控），终止")
        await record_service.create(
            user_id,
            status="auth_expired",
            douyin_account_id=account.id,
            error_message="抖音登录态已失效，请重新扫码关联",
            run_log=run.text(),
        )
        await db.commit()
        return JobResult(failed=True, reason="auth_expired")
    run.step("登录态校验通过")

    settings = await settings_service.get_or_create_settings(user_id)
    if settings.skip_today:
        run.step("今日已设置跳过，终止")
        await record_service.create(user_id, status="skipped", error_message="今日已跳过", run_log=run.text())
        await db.commit()
        return JobResult(ok=True, reason="skipped")

    targets = await target_service.list_enabled_targets(user_id, settings.daily_limit)
    if not targets:
        run.step("没有已启用的执行对象，终止")
        await record_service.create(user_id, status="no_target", error_message="无可执行对象", run_log=run.text())
        await db.commit()
        return JobResult(ok=True, reason="no_target", should_mark_scheduled=True)

    run.step(f"共 {len(targets)} 个对象待执行（每日上限={settings.daily_limit}）")

    for target in targets:
        status = await _execute_one_target(
            db,
            record_service,
            target_service,
            agent_service,
            sender_service,
            account,
            settings,
            target,
            user_id,
            trigger,
        )
        if status == "auth_expired":
            return JobResult(failed=True, reason="auth_expired", should_mark_scheduled=True)

    return JobResult(ok=True, should_mark_scheduled=True)


async def _execute_one_target(
    db: AsyncSession,
    record_service: RecordService,
    target_service: SparkTargetService,
    agent_service: AgentService,
    sender_service: SenderService,
    account,
    settings,
    target,
    user_id: int,
    trigger: str,
) -> str:
    label = _friend_label(target)
    run = _RunLog(user_id, trigger, f"target#{target.id}")
    run.step(f"处理对象 id={target.id} 昵称={target.nickname!r} 好友标识={label!r}")

    try:
        agent_result = await agent_service.build_message(settings, target)
        run.step(f"生成文案（来源={agent_result.source}）：{agent_result.message!r}")

        compliant, reason = is_compliant(agent_result.message)
        if not compliant:
            run.step(f"合规校验未通过：{reason}")
            await record_service.create(
                user_id,
                status="failed",
                douyin_account_id=account.id,
                target_id=target.id,
                message=agent_result.message,
                error_message=reason,
                run_log=run.text(),
                agent_decision=agent_result.to_dict(),
            )
            await target_service.update_last_run(target.id, "failed", reason)
            await db.commit()
            return "failed"
        run.step("合规校验通过")

        run.step("调用发送（进入私信页定位好友并发送）…")
        send_result = await sender_service.send(account, label, agent_result.message)
        run.step(
            f"发送结果：status={send_result.status} channel={send_result.channel} "
            f"error={send_result.error_message or '无'}"
        )
        status = send_result.status

        if status == "failed":
            run.step("首次发送失败，自动重试一次…")
            retry_result = await sender_service.send(account, label, agent_result.message)
            run.step(f"重试结果：status={retry_result.status} error={retry_result.error_message or '无'}")
            if retry_result.status == "success":
                status = "success"
                send_result = retry_result
            elif retry_result.status == "auth_expired":
                status = "auth_expired"
                send_result = retry_result

        if send_result.screenshot_base64:
            run.step(f"已截图存档（{len(send_result.screenshot_base64)} 字节 base64）")
        run.step(f"对象最终状态：{status}")
        await record_service.create(
            user_id,
            status=status,
            channel=send_result.channel,
            douyin_account_id=account.id,
            target_id=target.id,
            message=agent_result.message,
            error_code=send_result.error_code,
            error_message=send_result.error_message,
            run_log=run.text(),
            screenshot_base64=send_result.screenshot_base64,
            agent_decision=agent_result.to_dict(),
        )
        await target_service.update_last_run(target.id, status, send_result.error_message)
        await db.commit()
        return status
    except Exception as exc:
        logger.exception("spark target execute crashed user=%s target=%s", user_id, target.id)
        run.step(f"执行异常：{type(exc).__name__}: {exc}")
        await db.rollback()
        try:
            await record_service.create(
                user_id,
                status="failed",
                douyin_account_id=account.id,
                target_id=target.id,
                error_code="exception",
                error_message=str(exc)[:500],
                run_log=run.text(),
            )
            await target_service.update_last_run(target.id, "failed", str(exc)[:500])
            await db.commit()
        except Exception:
            logger.exception("write crash record failed user=%s target=%s", user_id, target.id)
            await db.rollback()
        return "failed"


async def run_user_spark_job_safe(user_id: int, trigger: str = "scheduler") -> None:
    from app.core.database import job_session_factory

    async with job_session_factory() as db:
        scheduler_service = SchedulerService(db)
        acquired = await scheduler_service.try_acquire_user_lock(user_id)
        if not acquired:
            logger.info("spark job skip, lock not acquired user=%s trigger=%s", user_id, trigger)
            return
        await db.commit()
        try:
            result = await execute_spark_for_user(db, user_id, trigger=trigger)
            if result.should_mark_scheduled:
                await SparkSettingsService(db).mark_scheduled_today(user_id)
                await db.commit()
        except Exception:
            logger.exception("spark job crashed user=%s trigger=%s", user_id, trigger)
            await db.rollback()
            try:
                run = _RunLog(user_id, trigger, "job")
                run.step("任务整体异常，写入兜底失败记录（详见后台日志）")
                await RecordService(db).create(
                    user_id,
                    status="failed",
                    error_code="job_exception",
                    error_message="执行任务异常，请查看后台日志",
                    run_log=run.text(),
                )
                await db.commit()
            except Exception:
                logger.exception("write job crash record failed user=%s", user_id)
                await db.rollback()
        finally:
            async with job_session_factory() as release_db:
                release_scheduler = SchedulerService(release_db)
                await release_scheduler.release_user_lock(user_id)
                await release_db.commit()

import asyncio
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.errors import AppError
from app.core.security import decrypt_token, encrypt_token
from app.integrations.douyin.browser_runtime import run_browser_task, run_in_browser_thread
from app.integrations.douyin.web_browser import (
    close_context,
    fetch_recent_contacts_sync,
    poll_qr_login_sync,
    send_private_message_sync,
    start_qr_login_sync,
    validate_qr_image_base64,
    validate_session_sync,
)
from app.models.douyin_account import DouyinAccount
from app.models.qr_login_session import QrLoginSession
from app.services.audit_service import AuditService
from app.utils.masking import mask_open_id

logger = logging.getLogger(__name__)


@dataclass
class _ActiveBrowser:
    session_id: str
    user_id: int
    context: object
    page: object


_active_browsers: dict[str, _ActiveBrowser] = {}
_browser_lock = asyncio.Lock()
_user_qr_start_locks: dict[int, asyncio.Lock] = {}
_user_qr_start_locks_guard = asyncio.Lock()


async def _user_qr_start_lock(user_id: int) -> asyncio.Lock:
    async with _user_qr_start_locks_guard:
        lock = _user_qr_start_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            _user_qr_start_locks[user_id] = lock
        return lock


class DouyinSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    async def start_qrcode_login(self, user_id: int) -> dict:
        lock = await _user_qr_start_lock(user_id)
        async with lock:
            return await self._start_qrcode_login_locked(user_id)

    async def _start_qrcode_login_locked(self, user_id: int) -> dict:
        logger.info("qrcode_start begin user_id=%s", user_id)
        await self._close_user_active_sessions(user_id)
        session_id = secrets.token_urlsafe(24)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        row = QrLoginSession(
            session_id=session_id,
            user_id=user_id,
            status="loading",
            qrcode_base64=None,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.flush()

        _spawn_qr_capture(session_id, user_id)
        logger.info("qrcode_start loading user_id=%s session_id=%s", user_id, session_id)
        return {
            "session_id": session_id,
            "status": "loading",
            "qrcode_image": None,
            "expires_in": 300,
            "already_logged_in": False,
        }

    async def apply_qr_capture_result(self, session_id: str, user_id: int, result) -> None:
        row = await self.db.scalar(
            select(QrLoginSession).where(
                QrLoginSession.session_id == session_id,
                QrLoginSession.user_id == user_id,
            )
        )
        if not row or row.status != "loading":
            await run_in_browser_thread(close_context, result.context)
            return

        if result.already_logged_in and result.storage_state:
            account = await self._save_account(user_id, result.storage_state, result.profile or {})
            await run_in_browser_thread(close_context, result.context)
            row.status = "confirmed"
            await self.audit.log(
                user_id,
                "douyin_qr_success",
                resource="douyin_account",
                resource_id=account.id,
            )
            await self.db.flush()
            return

        qr = result.qrcode_base64 or ""
        ok, reason = validate_qr_image_base64(qr) if qr else (False, "empty")
        if not ok:
            logger.error("qr capture invalid image session_id=%s reason=%s", session_id, reason)
            await run_in_browser_thread(close_context, result.context)
            row.status = "error"
            row.error_message = "未能识别登录二维码，请稍后重试"
            await self.db.flush()
            return

        async with _browser_lock:
            _active_browsers[session_id] = _ActiveBrowser(
                session_id=session_id,
                user_id=user_id,
                context=result.context,
                page=result.page,
            )
        row.qrcode_base64 = qr
        row.status = "pending"
        await self.db.flush()
        logger.info("qr capture ready session_id=%s png=%s", session_id, reason)

    async def poll_qrcode_status(self, user_id: int, session_id: str) -> dict:
        row = await self._get_session_row(user_id, session_id)
        if row.status == "confirmed":
            account = await self.get_account_entity(user_id)
            return {
                "status": "confirmed",
                "bound": True,
                "nickname": account.nickname if account else None,
                "avatar_url": account.avatar_url if account else None,
            }
        if row.status == "error":
            return {
                "status": "error",
                "bound": False,
                "message": row.error_message or "二维码获取失败，请稍后重试",
                "qrcode_image": None,
            }
        if row.expires_at < datetime.now(timezone.utc):
            await self._expire_session(session_id, row)
            return {"status": "expired", "bound": False, "message": "二维码已过期，请刷新", "qrcode_image": None}
        if row.status == "loading":
            return {"status": "loading", "bound": False, "qrcode_image": None}

        qrcode_image = row.qrcode_base64 if row.status in ("pending", "scanned") else None
        active = _active_browsers.get(session_id)
        if not active or active.user_id != user_id:
            row.status = "expired"
            row.error_message = "扫码会话已关闭"
            await self.db.flush()
            return {
                "status": "expired",
                "bound": False,
                "message": row.error_message,
                "qrcode_image": qrcode_image,
            }

        poll = await run_in_browser_thread(poll_qr_login_sync, active.page)
        if poll.status == "confirmed" and poll.storage_state:
            account = await self._save_account(user_id, poll.storage_state, poll.profile or {})
            await self._finish_session(session_id, row, "confirmed")
            await self.audit.log(
                user_id,
                "douyin_qr_success",
                resource="douyin_account",
                resource_id=account.id,
            )
            return {
                "status": "confirmed",
                "bound": True,
                "nickname": account.nickname,
                "avatar_url": account.avatar_url,
            }

        if poll.status == "scanned" and row.status != "scanned":
            row.status = "scanned"
            await self.db.flush()

        return {"status": poll.status, "bound": False, "qrcode_image": qrcode_image}

    async def cancel_qrcode_login(self, user_id: int, session_id: str) -> dict:
        row = await self.db.scalar(
            select(QrLoginSession).where(
                QrLoginSession.session_id == session_id,
                QrLoginSession.user_id == user_id,
            )
        )
        if row:
            await self._finish_session(session_id, row, "cancelled")
        return {"success": True}

    async def get_account(self, user_id: int) -> dict:
        account = await self.get_account_entity(user_id)
        if not account or account.auth_status == "revoked":
            return {"bound": False, "auth_method": "qrcode"}
        return {
            "bound": True,
            "auth_method": "qrcode",
            "open_id": mask_open_id(account.open_id),
            "nickname": account.nickname,
            "avatar_url": account.avatar_url,
            "auth_status": account.auth_status,
            "session_valid": account.auth_status == "active",
        }

    async def get_account_entity(self, user_id: int) -> DouyinAccount | None:
        return await self.db.scalar(
            select(DouyinAccount).where(DouyinAccount.user_id == user_id, DouyinAccount.auth_status != "revoked")
        )

    async def ensure_valid_session(self, account: DouyinAccount) -> str | None:
        if not account.encrypted_access_token:
            account.auth_status = "expired"
            await self.db.flush()
            return None
        try:
            plain = decrypt_token(account.encrypted_access_token)
        except ValueError:
            account.auth_status = "expired"
            await self.db.flush()
            return None
        result = await run_browser_task(validate_session_sync, plain)
        if not result.valid:
            account.auth_status = "expired"
            await self.db.flush()
            return None
        account.auth_status = "active"
        await self.db.flush()
        await self._persist_session_state(account, result.storage_state)
        return plain

    def _load_session_token(self, account: DouyinAccount) -> str | None:
        if not account.encrypted_access_token:
            return None
        try:
            return decrypt_token(account.encrypted_access_token)
        except ValueError:
            return None

    async def unbind(self, user_id: int) -> dict:
        account = await self.get_account_entity(user_id)
        if not account:
            raise AppError(3001, 400)
        account.encrypted_access_token = ""
        account.encrypted_refresh_token = None
        account.auth_status = "revoked"
        await self.db.flush()
        await self.audit.log(user_id, "douyin_unbind", resource="douyin_account", resource_id=account.id)
        return {"success": True}

    async def send_message(self, account: DouyinAccount, friend_label: str, message: str) -> dict:
        session_json = self._load_session_token(account)
        if not session_json:
            account.auth_status = "expired"
            await self.db.flush()
            return {
                "success": False,
                "error_message": "抖音登录态已失效，请重新扫码关联",
            }
        result = await run_browser_task(send_private_message_sync, session_json, friend_label, message)
        if result.success:
            await self._persist_session_state(account, result.storage_state)
        elif result.error_message and "失效" in result.error_message:
            account.auth_status = "expired"
            await self.db.flush()
        return {
            "success": result.success,
            "error_message": result.error_message,
            "screenshot_base64": result.screenshot_base64,
        }

    async def list_recent_contacts(self, user_id: int, limit: int = 10) -> dict:
        account = await self.get_account_entity(user_id)
        if not account:
            raise AppError(3001, 400)
        session_json = self._load_session_token(account)
        if not session_json:
            account.auth_status = "expired"
            await self.db.flush()
            raise AppError(3002, 401, "抖音登录态已失效，请重新扫码关联")
        cap = max(1, min(limit, 10))
        result = await run_browser_task(fetch_recent_contacts_sync, session_json, cap)
        if not result.success:
            if result.error_message and "失效" in result.error_message:
                account.auth_status = "expired"
                await self.db.flush()
                raise AppError(3002, 401, result.error_message)
            raise AppError(3003, 502, result.error_message or "获取最近联系人失败")
        await self._persist_session_state(account, result.storage_state)
        return {
            "items": [{"display_name": c.display_name} for c in result.contacts],
            "total": len(result.contacts),
        }

    async def _persist_session_state(self, account: DouyinAccount, storage_state: dict | None) -> None:
        if not storage_state:
            return
        try:
            account.encrypted_access_token = encrypt_token(json.dumps(storage_state, ensure_ascii=False))
            account.auth_status = "active"
            await self.db.flush()
        except Exception:
            logger.warning("persist session state failed account_id=%s", account.id, exc_info=True)

    async def _save_account(self, user_id: int, storage_state: dict, profile: dict) -> DouyinAccount:
        now = datetime.now(timezone.utc)
        encrypted = encrypt_token(json.dumps(storage_state, ensure_ascii=False))
        open_id = profile.get("open_id") or f"web_{user_id}"
        account = await self.db.scalar(select(DouyinAccount).where(DouyinAccount.user_id == user_id))
        if account:
            account.open_id = open_id
            account.nickname = profile.get("nickname")
            account.avatar_url = profile.get("avatar_url")
            account.scope = "web_session"
            account.encrypted_access_token = encrypted
            account.encrypted_refresh_token = None
            account.access_token_expires_at = None
            account.refresh_token_expires_at = None
            account.auth_status = "active"
        else:
            account = DouyinAccount(
                user_id=user_id,
                open_id=open_id,
                nickname=profile.get("nickname"),
                avatar_url=profile.get("avatar_url"),
                scope="web_session",
                encrypted_access_token=encrypted,
                auth_status="active",
            )
            self.db.add(account)
        await self.db.flush()
        return account

    async def _get_session_row(self, user_id: int, session_id: str) -> QrLoginSession:
        row = await self.db.scalar(
            select(QrLoginSession).where(
                QrLoginSession.session_id == session_id,
                QrLoginSession.user_id == user_id,
            )
        )
        if not row:
            raise AppError(1003, 404, "扫码会话不存在")
        return row

    async def _finish_session(self, session_id: str, row: QrLoginSession, status: str) -> None:
        row.status = status
        active = _active_browsers.pop(session_id, None)
        if active:
            await run_in_browser_thread(close_context, active.context)
        await self.db.flush()

    async def _expire_session(self, session_id: str, row: QrLoginSession) -> None:
        row.status = "expired"
        await self._finish_session(session_id, row, "expired")

    async def _close_user_active_sessions(self, user_id: int) -> None:
        to_close = [sid for sid, a in _active_browsers.items() if a.user_id == user_id]
        for sid in to_close:
            active = _active_browsers.pop(sid, None)
            if active:
                await run_in_browser_thread(close_context, active.context)
        await self.db.execute(
            delete(QrLoginSession).where(
                QrLoginSession.user_id == user_id,
                QrLoginSession.status.in_(("pending", "scanned", "loading")),
            )
        )


_qr_capture_tasks: set[asyncio.Task] = set()


def _spawn_qr_capture(session_id: str, user_id: int) -> None:
    task = asyncio.create_task(_qr_capture_worker(session_id, user_id))
    _qr_capture_tasks.add(task)
    task.add_done_callback(_qr_capture_tasks.discard)


async def _qr_capture_worker(session_id: str, user_id: int) -> None:
    try:
        result = await run_browser_task(start_qr_login_sync)
    except Exception:
        logger.exception("qr capture failed session_id=%s", session_id)
        await _mark_qr_session_failed(session_id, "二维码获取失败，请稍后重试")
        return
    async with async_session_factory() as db:
        try:
            await DouyinSessionService(db).apply_qr_capture_result(session_id, user_id, result)
            await db.commit()
        except Exception:
            logger.exception("qr capture apply failed session_id=%s", session_id)
            await db.rollback()
            await run_in_browser_thread(close_context, result.context)


async def _mark_qr_session_failed(session_id: str, message: str) -> None:
    async with async_session_factory() as db:
        row = await db.scalar(select(QrLoginSession).where(QrLoginSession.session_id == session_id))
        if row and row.status == "loading":
            row.status = "error"
            row.error_message = message
            await db.commit()


async def shutdown_active_browsers() -> None:
    async with _browser_lock:
        items = list(_active_browsers.values())
        _active_browsers.clear()
    for active in items:
        await run_in_browser_thread(close_context, active.context)

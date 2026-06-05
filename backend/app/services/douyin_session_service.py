import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decrypt_token, encrypt_token
from app.integrations.douyin.web_browser import (
    close_browser_session,
    poll_qr_login_sync,
    send_private_message_sync,
    start_qr_login_sync,
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
    playwright: object
    browser: object
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

        try:
            result = await asyncio.to_thread(start_qr_login_sync)
        except Exception as exc:
            logger.exception("start_qr_login_sync failed for user_id=%s", user_id)
            raise AppError(3003, 502, "二维码获取失败，请稍后重试") from exc

        qr_len = len(result.qrcode_base64 or "")
        logger.info(
            "qrcode_start playwright done user_id=%s already_logged_in=%s qrcode_len=%s",
            user_id,
            result.already_logged_in,
            qr_len,
        )

        if result.already_logged_in and result.storage_state:
            account = await self._save_account(
                user_id,
                result.storage_state,
                result.profile or {},
            )
            close_browser_session(result.playwright, result.browser)
            await self.audit.log(
                user_id,
                "douyin_qr_success",
                resource="douyin_account",
                resource_id=account.id,
            )
            return {
                "session_id": session_id,
                "status": "confirmed",
                "qrcode_image": None,
                "expires_in": 0,
                "already_logged_in": True,
            }

        async with _browser_lock:
            _active_browsers[session_id] = _ActiveBrowser(
                session_id=session_id,
                user_id=user_id,
                playwright=result.playwright,
                browser=result.browser,
                page=result.page,
            )

        row = QrLoginSession(
            session_id=session_id,
            user_id=user_id,
            status="pending",
            qrcode_base64=result.qrcode_base64,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.flush()

        if not result.qrcode_base64 or qr_len < 3000:
            logger.error(
                "qrcode_start invalid image user_id=%s session_id=%s qrcode_len=%s",
                user_id,
                session_id,
                qr_len,
            )
            await self._finish_session(session_id, row, "cancelled")
            raise AppError(3003, 502, "未能识别登录二维码，请稍后重试")

        logger.info(
            "qrcode_start ok user_id=%s session_id=%s qrcode_len=%s",
            user_id,
            session_id,
            qr_len,
        )
        return {
            "session_id": session_id,
            "status": "pending",
            "qrcode_image": result.qrcode_base64,
            "expires_in": 300,
            "already_logged_in": False,
        }

    async def poll_qrcode_status(self, user_id: int, session_id: str) -> dict:
        row = await self._get_session_row(user_id, session_id)
        if row.status == "confirmed":
            return {"status": "confirmed", "bound": True}
        qrcode_image = row.qrcode_base64 if row.status in ("pending", "scanned") else None
        if row.expires_at < datetime.now(timezone.utc):
            await self._expire_session(session_id, row)
            return {"status": "expired", "bound": False, "message": "二维码已过期，请刷新", "qrcode_image": None}

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

        poll = await asyncio.to_thread(poll_qr_login_sync, active.page)
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
        valid = await asyncio.to_thread(validate_session_sync, plain)
        if not valid:
            account.auth_status = "expired"
            await self.db.flush()
            return None
        account.auth_status = "active"
        await self.db.flush()
        return plain

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
        session_json = await self.ensure_valid_session(account)
        if not session_json:
            return {
                "success": False,
                "error_message": "抖音登录态已失效，请重新扫码关联",
            }
        result = await asyncio.to_thread(send_private_message_sync, session_json, friend_label, message)
        if not result.success:
            if result.error_message and "失效" in result.error_message:
                account.auth_status = "expired"
                await self.db.flush()
        return {
            "success": result.success,
            "error_message": result.error_message,
            "screenshot_base64": result.screenshot_base64,
        }

    async def _save_account(self, user_id: int, storage_state: dict, profile: dict) -> DouyinAccount:
        import json

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
            await asyncio.to_thread(close_browser_session, active.playwright, active.browser)
        await self.db.flush()

    async def _expire_session(self, session_id: str, row: QrLoginSession) -> None:
        row.status = "expired"
        await self._finish_session(session_id, row, "expired")

    async def _close_user_active_sessions(self, user_id: int) -> None:
        to_close = [sid for sid, a in _active_browsers.items() if a.user_id == user_id]
        for sid in to_close:
            active = _active_browsers.pop(sid, None)
            if active:
                await asyncio.to_thread(close_browser_session, active.playwright, active.browser)
        await self.db.execute(
            delete(QrLoginSession).where(
                QrLoginSession.user_id == user_id,
                QrLoginSession.status.in_(("pending", "scanned")),
            )
        )


async def shutdown_active_browsers() -> None:
    async with _browser_lock:
        items = list(_active_browsers.values())
        _active_browsers.clear()
    for active in items:
        await asyncio.to_thread(close_browser_session, active.playwright, active.browser)

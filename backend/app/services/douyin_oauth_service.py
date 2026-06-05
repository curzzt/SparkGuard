import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decrypt_token, encrypt_token
from app.integrations.douyin.client import DouyinClient
from app.models.douyin_account import DouyinAccount, OAuthState
from app.services.audit_service import AuditService
from app.utils.masking import mask_open_id


class DouyinOAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = DouyinClient()
        self.audit = AuditService(db)

    async def get_auth_url(self, user_id: int) -> dict:
        state = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        self.db.add(OAuthState(state=state, user_id=user_id, expires_at=expires_at))
        await self.db.flush()
        auth_url = self.client.build_auth_url(state)
        return {"auth_url": auth_url, "state": state}

    async def handle_callback(self, code: str, state: str, ip: str | None = None) -> tuple[int, bool, str | None]:
        oauth_state = await self.db.scalar(select(OAuthState).where(OAuthState.state == state))
        if not oauth_state or oauth_state.expires_at < datetime.now(timezone.utc):
            return oauth_state.user_id if oauth_state else 0, False, "invalid_state"
        user_id = oauth_state.user_id
        await self.db.execute(delete(OAuthState).where(OAuthState.id == oauth_state.id))

        token_resp = await self.client.exchange_code(code)
        if not token_resp.ok or not token_resp.access_token:
            await self.audit.log(user_id, "douyin_oauth_failed", detail={"reason": token_resp.error_message}, ip=ip)
            return user_id, False, "token_exchange_failed"

        user_info = await self.client.get_user_info(token_resp.access_token, token_resp.open_id or "")
        now = datetime.now(timezone.utc)
        account = await self.db.scalar(select(DouyinAccount).where(DouyinAccount.user_id == user_id))
        if account:
            account.open_id = token_resp.open_id or account.open_id
            account.union_id = user_info.union_id
            account.nickname = user_info.nickname
            account.avatar_url = user_info.avatar_url
            account.scope = token_resp.scope
            account.encrypted_access_token = encrypt_token(token_resp.access_token)
            account.encrypted_refresh_token = (
                encrypt_token(token_resp.refresh_token) if token_resp.refresh_token else None
            )
            account.access_token_expires_at = now + timedelta(seconds=token_resp.expires_in)
            account.refresh_token_expires_at = now + timedelta(seconds=token_resp.refresh_expires_in)
            account.auth_status = "active"
        else:
            account = DouyinAccount(
                user_id=user_id,
                open_id=token_resp.open_id or "",
                union_id=user_info.union_id,
                nickname=user_info.nickname,
                avatar_url=user_info.avatar_url,
                scope=token_resp.scope,
                encrypted_access_token=encrypt_token(token_resp.access_token),
                encrypted_refresh_token=(
                    encrypt_token(token_resp.refresh_token) if token_resp.refresh_token else None
                ),
                access_token_expires_at=now + timedelta(seconds=token_resp.expires_in),
                refresh_token_expires_at=now + timedelta(seconds=token_resp.refresh_expires_in),
                auth_status="active",
            )
            self.db.add(account)
        await self.db.flush()
        await self.audit.log(user_id, "douyin_oauth_success", resource="douyin_account", resource_id=account.id, ip=ip)
        return user_id, True, None

    async def get_account(self, user_id: int) -> dict:
        account = await self.db.scalar(select(DouyinAccount).where(DouyinAccount.user_id == user_id))
        if not account or account.auth_status == "revoked":
            return {"bound": False}
        scopes = account.scope.split(",") if account.scope else []
        return {
            "bound": True,
            "open_id": mask_open_id(account.open_id),
            "nickname": account.nickname,
            "avatar_url": account.avatar_url,
            "auth_status": account.auth_status,
            "access_token_expires_at": (
                account.access_token_expires_at.isoformat() if account.access_token_expires_at else None
            ),
            "scopes": scopes,
        }

    async def get_account_entity(self, user_id: int) -> DouyinAccount | None:
        return await self.db.scalar(
            select(DouyinAccount).where(DouyinAccount.user_id == user_id, DouyinAccount.auth_status != "revoked")
        )

    async def refresh_access_token(self, user_id: int) -> dict:
        account = await self.get_account_entity(user_id)
        if not account:
            raise AppError(3001, 400)
        if not account.encrypted_refresh_token:
            account.auth_status = "expired"
            await self.db.flush()
            raise AppError(3002, 401)
        refresh = decrypt_token(account.encrypted_refresh_token)
        resp = await self.client.refresh_token(refresh)
        if not resp.ok or not resp.access_token:
            account.auth_status = "expired"
            await self.db.flush()
            raise AppError(3002, 401)
        now = datetime.now(timezone.utc)
        account.encrypted_access_token = encrypt_token(resp.access_token)
        if resp.refresh_token:
            account.encrypted_refresh_token = encrypt_token(resp.refresh_token)
        account.access_token_expires_at = now + timedelta(seconds=resp.expires_in)
        account.refresh_token_expires_at = now + timedelta(seconds=resp.refresh_expires_in)
        account.auth_status = "active"
        await self.db.flush()
        return {
            "auth_status": account.auth_status,
            "access_token_expires_at": account.access_token_expires_at.isoformat(),
        }

    async def ensure_valid_access_token(self, account: DouyinAccount) -> str | None:
        now = datetime.now(timezone.utc)
        if account.access_token_expires_at and account.access_token_expires_at > now + timedelta(minutes=5):
            return decrypt_token(account.encrypted_access_token)
        if not account.encrypted_refresh_token:
            account.auth_status = "expired"
            await self.db.flush()
            return None
        refresh = decrypt_token(account.encrypted_refresh_token)
        resp = await self.client.refresh_token(refresh)
        if not resp.ok or not resp.access_token:
            account.auth_status = "expired"
            await self.db.flush()
            return None
        account.encrypted_access_token = encrypt_token(resp.access_token)
        if resp.refresh_token:
            account.encrypted_refresh_token = encrypt_token(resp.refresh_token)
        account.access_token_expires_at = now + timedelta(seconds=resp.expires_in)
        account.auth_status = "active"
        await self.db.flush()
        return resp.access_token

    async def unbind(self, user_id: int) -> dict:
        account = await self.get_account_entity(user_id)
        if not account:
            raise AppError(3001, 400)
        account.encrypted_access_token = ""
        account.encrypted_refresh_token = None
        account.access_token_expires_at = None
        account.refresh_token_expires_at = None
        account.auth_status = "revoked"
        await self.db.flush()
        await self.audit.log(user_id, "douyin_unbind", resource="douyin_account", resource_id=account.id)
        return {"success": True}

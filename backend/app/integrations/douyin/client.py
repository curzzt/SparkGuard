from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.integrations.douyin.constants import (
    DEFAULT_SCOPES,
    DOUYIN_OAUTH_URL,
    DOUYIN_REFRESH_URL,
    DOUYIN_TOKEN_URL,
    DOUYIN_USER_INFO_URL,
)


@dataclass
class TokenResponse:
    ok: bool
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int = 0
    refresh_expires_in: int = 0
    open_id: str | None = None
    scope: str | None = None
    error_message: str | None = None


@dataclass
class UserInfoResponse:
    ok: bool
    open_id: str | None = None
    union_id: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    error_message: str | None = None


@dataclass
class SendMessageResponse:
    success: bool
    error_code: str | None = None
    error_message: str | None = None


class DouyinClient:
    def __init__(self):
        self.settings = get_settings()

    def _ensure_configured(self) -> None:
        if not self.settings.DOUYIN_CLIENT_KEY or not self.settings.DOUYIN_CLIENT_SECRET:
            raise AppError(3003, 502, "请配置 DOUYIN_CLIENT_KEY 与 DOUYIN_CLIENT_SECRET")

    def build_auth_url(self, state: str) -> str:
        self._ensure_configured()
        params = {
            "client_key": self.settings.DOUYIN_CLIENT_KEY,
            "response_type": "code",
            "scope": ",".join(DEFAULT_SCOPES),
            "redirect_uri": self.settings.DOUYIN_REDIRECT_URI,
            "state": state,
        }
        return f"{DOUYIN_OAUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> TokenResponse:
        self._ensure_configured()
        payload = {
            "client_key": self.settings.DOUYIN_CLIENT_KEY,
            "client_secret": self.settings.DOUYIN_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(DOUYIN_TOKEN_URL, json=payload)
            data = resp.json()
            if data.get("data", {}).get("error_code", 0) != 0:
                return TokenResponse(ok=False, error_message=str(data))
            d = data["data"]
            return TokenResponse(
                ok=True,
                access_token=d.get("access_token"),
                refresh_token=d.get("refresh_token"),
                expires_in=d.get("expires_in", 86400),
                refresh_expires_in=d.get("refresh_expires_in", 2592000),
                open_id=d.get("open_id"),
                scope=d.get("scope"),
            )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        self._ensure_configured()
        payload = {
            "client_key": self.settings.DOUYIN_CLIENT_KEY,
            "client_secret": self.settings.DOUYIN_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(DOUYIN_REFRESH_URL, json=payload)
            data = resp.json()
            if data.get("data", {}).get("error_code", 0) != 0:
                return TokenResponse(ok=False, error_message=str(data))
            d = data["data"]
            return TokenResponse(
                ok=True,
                access_token=d.get("access_token"),
                refresh_token=d.get("refresh_token"),
                expires_in=d.get("expires_in", 86400),
                refresh_expires_in=d.get("refresh_expires_in", 2592000),
                open_id=d.get("open_id"),
                scope=d.get("scope"),
            )

    async def get_user_info(self, access_token: str, open_id: str) -> UserInfoResponse:
        self._ensure_configured()
        payload = {"access_token": access_token, "open_id": open_id}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(DOUYIN_USER_INFO_URL, json=payload)
            data = resp.json()
            if data.get("data", {}).get("error_code", 0) != 0:
                return UserInfoResponse(ok=False, error_message=str(data))
            d = data["data"]
            return UserInfoResponse(
                ok=True,
                open_id=d.get("open_id"),
                union_id=d.get("union_id"),
                nickname=d.get("nickname"),
                avatar_url=d.get("avatar"),
            )

    async def send_message(
        self, access_token: str, receiver_id: str, content: str, msg_type: str = "text"
    ) -> SendMessageResponse:
        self._ensure_configured()
        return SendMessageResponse(
            success=False,
            error_code="unsupported",
            error_message="当前账号类型与开放平台 scope 不支持向该 receiver 自动发送消息",
        )

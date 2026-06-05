from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.douyin_account import DouyinAccount
from app.services.douyin_session_service import DouyinSessionService


@dataclass
class SendResult:
    status: str
    channel: str
    error_code: str | None = None
    error_message: str | None = None
    screenshot_base64: str | None = None


class SenderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = DouyinSessionService(db)

    async def send(
        self,
        account: DouyinAccount,
        friend_label: str,
        message: str,
    ) -> SendResult:
        label = (friend_label or "").strip()
        if not label:
            return SendResult(
                status="failed",
                channel="none",
                error_message="好友标识为空，请填写会话列表中的显示名",
            )

        result = await self.session_service.send_message(account, label, message)
        if result.get("success"):
            return SendResult(
                status="success",
                channel="douyin_web",
                screenshot_base64=result.get("screenshot_base64"),
            )
        error = result.get("error_message") or "发送失败"
        if "失效" in error:
            return SendResult(
                status="auth_expired",
                channel="none",
                error_code="session_expired",
                error_message=error,
            )
        return SendResult(
            status="failed",
            channel="douyin_web",
            error_message=error,
        )

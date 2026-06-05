from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.spark_settings import SparkSettings
from app.services.douyin_session_service import DouyinSessionService
from app.utils.datetime import format_time_hhmm, parse_time_hhmm


class SparkSettingsService:
    DEFAULTS = {
        "enabled": False,
        "execute_time": "09:00",
        "default_template": "今天也要续火花～",
        "random_template_enabled": False,
        "daily_limit": 10,
        "skip_today": False,
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session = DouyinSessionService(db)

    async def get_settings(self, user_id: int) -> SparkSettings | None:
        return await self.db.scalar(select(SparkSettings).where(SparkSettings.user_id == user_id))

    async def get_or_create_settings(self, user_id: int) -> SparkSettings:
        settings = await self.get_settings(user_id)
        if settings:
            return settings
        settings = SparkSettings(user_id=user_id, execute_time=time(9, 0))
        self.db.add(settings)
        await self.db.flush()
        return settings

    async def get_settings_dict(self, user_id: int) -> dict:
        settings = await self.get_settings(user_id)
        if not settings:
            return dict(self.DEFAULTS)
        return self._to_dict(settings)

    async def update_settings(self, user_id: int, data: dict) -> dict:
        settings = await self.get_or_create_settings(user_id)
        if data.get("enabled"):
            account = await self.session.get_account_entity(user_id)
            if not account or account.auth_status != "active":
                raise AppError(3001, 400, "请先扫码关联抖音号并确保登录态有效后再开启自动续火花")
            settings.douyin_account_id = account.id
        if "enabled" in data and data["enabled"] is not None:
            settings.enabled = data["enabled"]
        if data.get("execute_time"):
            settings.execute_time = parse_time_hhmm(data["execute_time"])
        if "default_template" in data:
            settings.default_template = data["default_template"]
        if data.get("random_template_enabled") is not None:
            settings.random_template_enabled = data["random_template_enabled"]
        if data.get("daily_limit") is not None:
            settings.daily_limit = data["daily_limit"]
        await self.db.flush()
        return self._to_dict(settings)

    async def skip_today(self, user_id: int) -> dict:
        settings = await self.get_or_create_settings(user_id)
        settings.skip_today = True
        await self.db.flush()
        return {"skip_today": True}

    async def mark_scheduled_today(self, user_id: int) -> None:
        from app.utils.datetime import local_now

        settings = await self.get_or_create_settings(user_id)
        settings.last_scheduled_date = local_now().date()
        settings.skip_today = False
        await self.db.flush()

    def _to_dict(self, settings: SparkSettings) -> dict:
        return {
            "enabled": settings.enabled,
            "execute_time": format_time_hhmm(settings.execute_time),
            "default_template": settings.default_template,
            "random_template_enabled": settings.random_template_enabled,
            "daily_limit": settings.daily_limit,
            "skip_today": settings.skip_today,
        }

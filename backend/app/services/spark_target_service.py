from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.spark_target import SparkTarget
from app.services.douyin_session_service import DouyinSessionService


class SparkTargetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session = DouyinSessionService(db)

    async def list_targets(self, user_id: int) -> dict:
        result = await self.db.scalars(
            select(SparkTarget).where(SparkTarget.user_id == user_id).order_by(SparkTarget.id.desc())
        )
        items = [self._to_dict(t) for t in result.all()]
        return {"items": items, "total": len(items)}

    async def create_target(self, user_id: int, data: dict) -> dict:
        account = await self.session.get_account_entity(user_id)
        if not account:
            raise AppError(3001, 400)
        target = SparkTarget(
            user_id=user_id,
            douyin_account_id=account.id,
            nickname=data["nickname"],
            remark=data.get("remark"),
            receiver_id=(data.get("receiver_id") or data["nickname"]).strip(),
            custom_template=data.get("custom_template"),
            enabled=data.get("enabled", True),
        )
        self.db.add(target)
        await self.db.flush()
        return self._to_dict(target)

    async def update_target(self, user_id: int, target_id: int, data: dict) -> dict:
        target = await self._get_owned_target(user_id, target_id)
        for key in ("nickname", "remark", "receiver_id", "custom_template", "enabled"):
            if key in data and data[key] is not None:
                setattr(target, key, data[key])
        await self.db.flush()
        return self._to_dict(target)

    async def delete_target(self, user_id: int, target_id: int) -> None:
        target = await self._get_owned_target(user_id, target_id)
        await self.db.delete(target)

    async def batch_enable(self, user_id: int, ids: list[int], enabled: bool) -> None:
        if not ids:
            return
        await self._validate_ids(user_id, ids)
        await self.db.execute(
            update(SparkTarget).where(SparkTarget.user_id == user_id, SparkTarget.id.in_(ids)).values(enabled=enabled)
        )

    async def list_enabled_targets(self, user_id: int, limit: int) -> list[SparkTarget]:
        result = await self.db.scalars(
            select(SparkTarget)
            .where(SparkTarget.user_id == user_id, SparkTarget.enabled.is_(True))
            .order_by(SparkTarget.id.asc())
            .limit(limit)
        )
        return list(result.all())

    async def update_last_run(self, target_id: int, status: str, error: str | None = None) -> None:
        from app.utils.datetime import local_now

        await self.db.execute(
            update(SparkTarget)
            .where(SparkTarget.id == target_id)
            .values(last_status=status, last_run_at=local_now(), last_error=error)
        )

    async def _get_owned_target(self, user_id: int, target_id: int) -> SparkTarget:
        target = await self.db.scalar(select(SparkTarget).where(SparkTarget.id == target_id))
        if not target or target.user_id != user_id:
            raise AppError(1003, 404)
        return target

    async def _validate_ids(self, user_id: int, ids: list[int]) -> None:
        count = await self.db.scalar(
            select(func.count()).select_from(SparkTarget).where(
                SparkTarget.user_id == user_id, SparkTarget.id.in_(ids)
            )
        )
        if count != len(ids):
            raise AppError(1003, 404)

    def _to_dict(self, target: SparkTarget) -> dict:
        return {
            "id": target.id,
            "nickname": target.nickname,
            "remark": target.remark,
            "receiver_id": target.receiver_id,
            "custom_template": target.custom_template,
            "enabled": target.enabled,
            "last_status": target.last_status,
            "last_run_at": target.last_run_at.isoformat() if target.last_run_at else None,
            "last_error": target.last_error,
        }

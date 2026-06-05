from sqlalchemy.ext.asyncio import AsyncSession


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        user_id: int | None,
        action: str,
        resource: str | None = None,
        resource_id: int | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        detail: dict | None = None,
    ) -> None:
        from app.models.audit_log import AuditLog

        self.db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip=ip,
                user_agent=user_agent,
                detail=detail,
            )
        )

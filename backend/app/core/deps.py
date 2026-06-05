from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.errors import AppError
from app.models.user import User
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    settings = get_settings()
    if settings.DEV_BYPASS_AUTH and settings.APP_ENV == "development":
        result = await db.execute(select(User).where(User.status == "active").limit(1))
        dev_user = result.scalar_one_or_none()
        if dev_user:
            return dev_user

    if not credentials or not credentials.credentials:
        raise AppError(1001, 401)
    user = await AuthService(db).get_user_from_token(credentials.credentials)
    if not user:
        raise AppError(1001, 401)
    if user.status != "active":
        raise AppError(2003, 403)
    return user

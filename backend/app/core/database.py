from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.APP_ENV == "development")
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

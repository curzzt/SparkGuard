from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_size=20,
    max_overflow=10,
    pool_timeout=5,
    pool_pre_ping=True,
    pool_recycle=1800,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

job_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_size=5,
    max_overflow=5,
    pool_timeout=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
job_session_factory = async_sessionmaker(job_engine, class_=AsyncSession, expire_on_commit=False)

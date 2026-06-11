from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import success
from app.core.rate_limit import limiter
from app.models.user import User
from app.services.douyin_session_service import DouyinSessionService

router = APIRouter(prefix="/douyin", tags=["douyin"])


@router.post("/qrcode/start")
@limiter.limit("5/minute")
async def qrcode_start(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await DouyinSessionService(db).start_qrcode_login(current_user.id)
    return success(data)


@router.get("/qrcode/status")
async def qrcode_status(
    session_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await DouyinSessionService(db).poll_qrcode_status(current_user.id, session_id)
    return success(data)


@router.post("/qrcode/cancel")
async def qrcode_cancel(
    session_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await DouyinSessionService(db).cancel_qrcode_login(current_user.id, session_id)
    return success(data)


@router.get("/account")
async def account(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await DouyinSessionService(db).get_account(current_user.id)
    return success(data)


@router.get("/recent-contacts")
@limiter.limit("10/minute")
async def recent_contacts(
    request: Request,
    limit: int = Query(10, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await DouyinSessionService(db).list_recent_contacts(current_user.id, limit)
    return success(data)


@router.post("/unbind")
async def unbind(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await DouyinSessionService(db).unbind(current_user.id)
    return success(data)

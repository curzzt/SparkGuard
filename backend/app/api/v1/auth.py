from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import success
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import LoginRequest, LogoutResponse, RegisterRequest
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    data = await AuthService(db).register(body.phone, body.password, body.password_confirm)
    await AuditService(db).log(data["user"]["id"], "register", ip=request.client.host if request.client else None)
    return success(data)


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    data = await AuthService(db).login(body.phone, body.password)
    await AuditService(db).log(data["user"]["id"], "login", ip=request.client.host if request.client else None)
    return success(data)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await AuthService(db).get_me(current_user)
    return success(data)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return success(LogoutResponse().model_dump())

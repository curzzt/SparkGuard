from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User
from app.utils.masking import mask_phone


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def register(self, phone: str, password: str, password_confirm: str) -> dict:
        if password != password_confirm:
            raise AppError(1004, 422, "两次密码不一致")
        existing = await self.db.scalar(select(User).where(User.phone == phone))
        if existing:
            raise AppError(2001, 400)
        user = User(phone=phone, password_hash=hash_password(password))
        self.db.add(user)
        await self.db.flush()
        token = create_access_token(user.id)
        return self._auth_response(user, token)

    async def login(self, phone: str, password: str) -> dict:
        user = await self.db.scalar(select(User).where(User.phone == phone))
        if not user or not verify_password(password, user.password_hash):
            raise AppError(2002, 401)
        if user.status != "active":
            raise AppError(2003, 403)
        token = create_access_token(user.id)
        return self._auth_response(user, token)

    async def get_user_from_token(self, token: str) -> User | None:
        payload = decode_access_token(token)
        if not payload:
            return None
        user_id = int(payload["sub"])
        return await self.db.scalar(select(User).where(User.id == user_id))

    async def get_me(self, user: User) -> dict:
        return {
            "id": user.id,
            "phone": mask_phone(user.phone),
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    def _auth_response(self, user: User, token: str) -> dict:
        return {
            "user": {
                "id": user.id,
                "phone": mask_phone(user.phone),
                "status": user.status,
            },
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.settings.JWT_EXPIRE_HOURS * 3600,
        }

from pydantic import BaseModel, Field, field_validator

from app.utils.masking import PHONE_PATTERN, PASSWORD_PATTERN


class RegisterRequest(BaseModel):
    phone: str
    password: str
    password_confirm: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not PHONE_PATTERN.match(v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError("密码至少8位且包含字母和数字")
        return v


class LoginRequest(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    id: int
    phone: str
    status: str
    created_at: str | None = None


class AuthResponse(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    success: bool = True

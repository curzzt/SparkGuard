from pydantic import BaseModel


class QrcodeStartResponse(BaseModel):
    session_id: str
    status: str
    qrcode_image: str | None = None
    expires_in: int
    already_logged_in: bool = False


class QrcodeStatusResponse(BaseModel):
    status: str
    bound: bool = False
    nickname: str | None = None
    avatar_url: str | None = None
    message: str | None = None


class DouyinAccountResponse(BaseModel):
    bound: bool
    auth_method: str = "qrcode"
    open_id: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    auth_status: str | None = None
    session_valid: bool | None = None


class UnbindResponse(BaseModel):
    success: bool = True

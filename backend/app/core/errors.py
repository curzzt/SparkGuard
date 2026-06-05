from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: int, http_status: int, message: str = "error", data: Any = None):
        self.code = code
        self.http_status = http_status
        self.message = message
        self.data = data
        super().__init__(message)


ERROR_MESSAGES = {
    1001: "未登录或 Token 无效",
    1002: "无权限访问该资源",
    1003: "资源不存在",
    1004: "参数校验失败",
    1005: "请求过于频繁",
    2001: "手机号已注册",
    2002: "手机号或密码错误",
    2003: "账号已禁用",
    3001: "未绑定抖音账号",
    3002: "抖音授权已失效",
    3003: "抖音 API 调用失败",
    4001: "今日任务正在执行中",
    4002: "今日已跳过",
    4003: "无可执行对象",
    5000: "服务器内部错误",
}


def success(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "data": exc.data},
    )


async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": 1004, "message": str(exc.detail), "data": None},
    )


async def generic_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "message": ERROR_MESSAGES[5000], "data": None},
    )

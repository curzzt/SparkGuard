import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, generic_error_handler
from app.core.rate_limit import limiter
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.services.douyin_session_service import shutdown_active_browsers


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    message = exc.errors()[0].get("msg", "参数校验失败") if exc.errors() else "参数校验失败"
    return JSONResponse(status_code=422, content={"code": 1004, "message": message, "data": None})


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler()
    yield
    await shutdown_active_browsers()
    stop_scheduler()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    settings = get_settings()
    app = FastAPI(title="SparkGuard API", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()

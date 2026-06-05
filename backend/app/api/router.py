from fastapi import APIRouter

from app.api.v1 import auth, douyin, spark

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(douyin.router)
api_router.include_router(spark.router)

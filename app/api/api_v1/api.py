from fastapi import APIRouter

from app.api.api_v1.endpoints import feature_flags, user

api_router = APIRouter()

api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(
    feature_flags.router, prefix="/feature_flags", tags=["feature_flags"]
)

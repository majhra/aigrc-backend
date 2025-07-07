from fastapi import APIRouter

from app.api.api_v1.endpoints import configurations, feature_flags, prompts, reports, tests, user

api_router = APIRouter()

api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(
    feature_flags.router, prefix="/feature_flags", tags=["feature_flags"]
)
api_router.include_router(
    prompts.router, prefix="/prompts", tags=["prompts"]
)
api_router.include_router(
    configurations.router, prefix="/configurations", tags=["configurations"]
)
api_router.include_router(tests.router, prefix="/tests", tags=["tests"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])


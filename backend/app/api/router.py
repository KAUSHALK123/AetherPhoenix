from fastapi import APIRouter

from app.api.endpoints import dashboard, notifications, permissions, planner

api_router = APIRouter()

api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(
    permissions.router, prefix="/permissions", tags=["permissions"]
)
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)


from fastapi import APIRouter

from app.api.endpoints import browser_extension, dashboard, permissions, planner

api_router = APIRouter()

api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(
    permissions.router, prefix="/permissions", tags=["permissions"]
)
api_router.include_router(
    browser_extension.router, prefix="/browser-extension", tags=["browser-extension"]
)


from fastapi import APIRouter

from app.api.endpoints import dashboard, planner

api_router = APIRouter()

api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

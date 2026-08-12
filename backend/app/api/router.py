from fastapi import APIRouter

from app.api.endpoints import planner

api_router = APIRouter()

api_router.include_router(planner.router, prefix="/planner", tags=["planner"])

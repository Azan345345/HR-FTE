"""
Digital FTE - Main API Router
Aggregates all sub-routers.
"""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.cv import router as cv_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.applications import router as applications_router
from app.api.routes.interview import router as interview_router
from app.api.routes.chat import router as chat_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.observability import router as observability_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.quota import router as quota_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(cv_router)
api_router.include_router(jobs_router)
api_router.include_router(applications_router)
api_router.include_router(interview_router)
api_router.include_router(chat_router)
api_router.include_router(integrations_router)
api_router.include_router(observability_router)
api_router.include_router(dashboard_router)
api_router.include_router(quota_router)

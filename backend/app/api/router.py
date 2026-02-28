"""Main API router — aggregates all route modules."""

from fastapi import APIRouter
from app.api.routes import auth, cv, jobs, applications, chat, dashboard, observability, interview, integrations, settings

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(cv.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(observability.router)
api_router.include_router(interview.router)
api_router.include_router(integrations.router)
api_router.include_router(settings.router)

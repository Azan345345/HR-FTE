"""FastAPI application entry point — Digital FTE Backend."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from app.config import settings
from app.api.router import api_router
from app.api.websocket.handler import websocket_endpoint
from app.db.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Create directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.GENERATED_DIR, exist_ok=True)

    is_postgres = "postgresql" in str(settings.DATABASE_URL)
    json_type = "JSONB" if is_postgres else "JSON"

    # ── Step 1: create tables ────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ── Step 2: ADD COLUMN migrations — each in its own transaction so a
    #    "column already exists" failure doesn't abort the whole block.
    new_columns = [
        ("interview_preps", "questions_to_ask",        json_type),
        ("interview_preps", "system_design_questions", json_type),
        ("interview_preps", "coding_challenges",       json_type),
        ("interview_preps", "cultural_questions",      json_type),
        ("interview_preps", "study_plan",              json_type),
        ("hr_contacts",     "additional_emails",       json_type),
    ]
    for table, column, col_type in new_columns:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        except Exception:
            pass  # Column already exists — safe to ignore

    # ── Step 3: make tailored_cvs.job_id nullable (general CV improvements
    #    have no associated job).  Runs in its own transaction so it is never
    #    affected by the "column already exists" failures above.
    if is_postgres:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "ALTER TABLE tailored_cvs ALTER COLUMN job_id DROP NOT NULL"
                ))
        except Exception:
            pass  # Already nullable — safe to ignore

    # Start Gmail watcher
    from app.agents.gmail_watcher import gmail_watcher
    await gmail_watcher.start()

    yield

    # Shutdown
    await gmail_watcher.stop()
    await engine.dispose()


app = FastAPI(
    title="Digital FTE API",
    description="AI-powered multi-agent job application assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins (add FRONTEND_URL env var for production)
_default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:3000",
]
_frontend_url = os.getenv("FRONTEND_URL", "")
_allowed_origins = _default_origins + [u.strip() for u in _frontend_url.split(",") if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)

# WebSocket endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": "Digital FTE",
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Digital FTE API is running",
        "docs": "/docs",
        "health": "/health",
    }

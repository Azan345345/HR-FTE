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

    # Create database tables (for SQLite dev or first run)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migrate: add new columns if missing (SQLite doesn't support IF NOT EXISTS on ALTER TABLE)
        # Use JSONB for PostgreSQL, JSON for SQLite (TEXT fallback)
        is_postgres = "postgresql" in str(settings.DATABASE_URL)
        json_type = "JSONB" if is_postgres else "JSON"
        new_columns = [
            ("interview_preps", "questions_to_ask",        json_type),
            ("interview_preps", "system_design_questions", json_type),
            ("interview_preps", "coding_challenges",       json_type),
            ("interview_preps", "cultural_questions",      json_type),
            ("interview_preps", "study_plan",              json_type),
        ]
        for table, column, col_type in new_columns:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            except Exception:
                pass  # Column already exists

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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:3000",
        "http://192.168.100.11:5173",
        "http://192.168.100.11:5174",
    ],
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

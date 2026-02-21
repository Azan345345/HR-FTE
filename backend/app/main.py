"""
Digital FTE - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.router import api_router
from app.api.websocket.handler import websocket_endpoint

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── Startup ──────────────────────────────────────
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.GENERATED_DIR, exist_ok=True)
    yield
    # ── Shutdown ─────────────────────────────────────


app = FastAPI(
    title="Digital FTE",
    description="AI-powered multi-agent job application assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST routes ──────────────────────────────────────
app.include_router(api_router, prefix="/api")

# ── WebSocket ────────────────────────────────────────
app.add_api_websocket_route("/ws/{session_id}", websocket_endpoint)


# ── Health check ─────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "digital-fte"}

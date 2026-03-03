"""Authentication routes: signup, login, current user, forgot/reset password."""

import secrets
import base64
from email.mime.text import MIMEText

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.redis_client import redis_client
from app.api.deps import get_current_user
from app.config import settings
from app.schemas.schemas import (
    SignupRequest, LoginRequest, TokenResponse, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
)

import structlog
logger = structlog.get_logger()

_RESET_TTL = 3600  # 1 hour


async def _get_gmail_access_token() -> str | None:
    """Exchange system GOOGLE_REFRESH_TOKEN for a fresh access token."""
    if not settings.GOOGLE_REFRESH_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id":     settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        })
    return resp.json().get("access_token") if resp.status_code == 200 else None


async def _send_reset_email(to_email: str, to_name: str, reset_url: str) -> bool:
    """Send password-reset email via Gmail API using the system OAuth token."""
    access_token = await _get_gmail_access_token()
    if not access_token:
        logger.warning("reset_email_skipped_no_token")
        return False

    body = f"""Hi {to_name or 'there'},

You requested a password reset for your CareerAgent account.

Click the link below to set a new password (valid for 1 hour):

{reset_url}

If you didn't request this, you can safely ignore this email.

— The CareerAgent Team
"""
    msg = MIMEText(body, "plain")
    msg["To"]      = to_email
    msg["From"]    = "CareerAgent <me>"
    msg["Subject"] = "Reset your CareerAgent password"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
        )
    ok = resp.status_code == 200
    if not ok:
        logger.error("reset_email_send_failed", status=resp.status_code, body=resp.text[:200])
    return ok

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        preferences={"onboarding_completed": False},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            preferences=user.preferences or {},
            created_at=str(user.created_at) if user.created_at else None,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            preferences=user.preferences or {},
            created_at=str(user.created_at) if user.created_at else None,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        preferences=current_user.preferences or {},
        created_at=str(current_user.created_at) if current_user.created_at else None,
    )


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password-reset link to the user's email."""
    _OK = {"message": "If that email is registered, you'll receive a reset link shortly."}

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        return _OK  # Don't leak whether email exists

    if not redis_client:
        raise HTTPException(500, "Password reset is temporarily unavailable.")

    token = secrets.token_urlsafe(32)
    redis_client.setex(f"pwd_reset:{token}", _RESET_TTL, str(user.id))

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    await _send_reset_email(user.email, user.name, reset_url)
    logger.info("password_reset_requested", user_id=user.id)
    return _OK


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Validate reset token and update the user's password."""
    if not redis_client:
        raise HTTPException(500, "Password reset is temporarily unavailable.")

    user_id = redis_client.get(f"pwd_reset:{body.token}")
    if not user_id:
        raise HTTPException(400, "Reset link is invalid or has expired.")

    result = await db.execute(select(User).where(User.id == str(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "User not found.")

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    redis_client.delete(f"pwd_reset:{body.token}")
    logger.info("password_reset_success", user_id=user.id)
    return {"message": "Password reset successfully. You can now sign in."}

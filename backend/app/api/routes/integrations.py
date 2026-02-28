"""Integrations routes — Google OAuth, service connections."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, UserIntegration
from app.api.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/integrations", tags=["Integrations"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
]


@router.get("/google/auth-url")
async def get_google_auth_url(
    current_user: User = Depends(get_current_user),
):
    """Get Google OAuth2 authorization URL."""
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    from app.core.google_auth import get_google_auth_url as build_url
    redirect_uri = "http://localhost:5173/settings/google-callback"
    url = await build_url(redirect_uri, GOOGLE_SCOPES)
    return {"auth_url": url}


@router.post("/google/callback")
async def google_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exchange Google authorization code for tokens."""
    from app.core.google_auth import exchange_code_for_tokens

    redirect_uri = "http://localhost:5173/settings/google-callback"
    tokens = await exchange_code_for_tokens(code, redirect_uri, GOOGLE_SCOPES)

    # Store integration
    result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == current_user.id,
            UserIntegration.service_name == "google",
        )
    )
    integration = result.scalar_one_or_none()

    if integration:
        integration.access_token = tokens.get("access_token")
        integration.refresh_token = tokens.get("refresh_token")
        integration.is_active = True
        integration.token_expiry = None  # reset; will be managed by the OAuth library
    else:
        integration = UserIntegration(
            user_id=current_user.id,
            service_name="google",
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            scopes=GOOGLE_SCOPES,
            is_active=True,
        )
        db.add(integration)

    # Store tokens on user as well
    current_user.google_oauth_token = tokens
    current_user.google_refresh_token = tokens.get("refresh_token")

    await db.commit()
    return {"status": "connected"}


@router.get("/status")
async def get_integration_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of all integrations."""
    result = await db.execute(
        select(UserIntegration).where(UserIntegration.user_id == current_user.id)
    )
    integrations = result.scalars().all()

    services = {
        "google_gmail": False,
        "google_drive": False,
        "supabase": bool(settings.SUPABASE_URL),
        "upstash_redis": bool(settings.UPSTASH_REDIS_URL),
    }
    for i in integrations:
        if i.service_name == "google" and i.is_active:
            services["google_gmail"] = True
            services["google_drive"] = True

    # Also treat env-level or user-level refresh token as connected
    # (matches the same logic used by the settings page)
    if not services["google_gmail"] and (
        current_user.google_refresh_token or settings.GOOGLE_REFRESH_TOKEN
    ):
        services["google_gmail"] = True

    return {"integrations": services}


@router.delete("/google")
async def disconnect_google(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke and clear stored Google OAuth tokens so the user can reconnect."""
    result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == current_user.id,
            UserIntegration.service_name.in_(["google", "gmail"]),
        )
    )
    for integration in result.scalars().all():
        integration.is_active = False
        integration.access_token = None
        integration.refresh_token = None

    current_user.google_refresh_token = None
    current_user.google_oauth_token = None

    await db.commit()
    return {"status": "disconnected"}

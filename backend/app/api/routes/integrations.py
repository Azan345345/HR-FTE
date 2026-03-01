"""Integrations routes — Google OAuth, service connections."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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


def _redirect_uri() -> str:
    return f"{settings.FRONTEND_URL}/settings/google-callback"


def _get_user_google_creds(user: User):
    """Return (client_id, client_secret) from user preferences or env, or raise."""
    prefs = user.preferences or {}
    client_id = prefs.get("google_client_id") or settings.GOOGLE_OAUTH_CLIENT_ID
    client_secret = prefs.get("google_client_secret") or settings.GOOGLE_OAUTH_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth credentials not configured. Please add your Client ID and Secret in Settings → Integrations.",
        )
    return client_id, client_secret


# ── Credentials ──────────────────────────────────────────────────────────────

class GoogleCredentialsBody(BaseModel):
    client_id: str
    client_secret: str


@router.post("/google/credentials")
async def save_google_credentials(
    body: GoogleCredentialsBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save user's own Google OAuth Client ID and Client Secret."""
    from sqlalchemy.orm.attributes import flag_modified

    client_id = body.client_id.strip()
    client_secret = body.client_secret.strip()

    prefs = dict(current_user.preferences or {})
    prefs["google_client_id"] = client_id
    prefs["google_client_secret"] = client_secret
    current_user.preferences = prefs
    flag_modified(current_user, "preferences")
    await db.commit()

    # Also update the live settings object so OAuth works immediately
    settings.GOOGLE_OAUTH_CLIENT_ID = client_id
    settings.GOOGLE_OAUTH_CLIENT_SECRET = client_secret

    return {"status": "saved"}


@router.get("/google/credentials")
async def get_google_credentials(
    current_user: User = Depends(get_current_user),
):
    """Return whether user has saved Google credentials (never expose the secret)."""
    prefs = current_user.preferences or {}
    client_id = prefs.get("google_client_id", "")
    has_secret = bool(prefs.get("google_client_secret"))
    return {
        "client_id": client_id,
        "has_secret": has_secret,
        "configured": bool(client_id and has_secret),
    }


# ── OAuth Flow ────────────────────────────────────────────────────────────────

@router.get("/google/auth-url")
async def get_google_auth_url(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Google OAuth2 authorization URL using user credentials or env fallback."""
    client_id, client_secret = _get_user_google_creds(current_user)

    from app.core.google_auth import get_google_auth_url as build_url
    url = await build_url(
        _redirect_uri(),
        GOOGLE_SCOPES,
        client_id=client_id,
        client_secret=client_secret,
    )
    return {"auth_url": url}


@router.post("/google/callback")
async def google_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exchange Google authorization code for tokens."""
    client_id, client_secret = _get_user_google_creds(current_user)

    from app.core.google_auth import exchange_code_for_tokens
    tokens = await exchange_code_for_tokens(
        code,
        _redirect_uri(),
        GOOGLE_SCOPES,
        client_id=client_id,
        client_secret=client_secret,
    )

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
        integration.token_expiry = None
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
    """Revoke and clear stored Google OAuth tokens."""
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

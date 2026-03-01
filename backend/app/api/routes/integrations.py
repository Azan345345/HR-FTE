"""Integrations routes — Google OAuth, service connections.

OAuth flow (backend-callback):
  GET /integrations/google/auth-url     → returns auth URL (user redirected to Google)
  GET /integrations/google/callback     → Google redirects here with ?code&state
                                          backend exchanges code, saves tokens,
                                          redirects to FRONTEND_URL/?gmail_connected=1
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, UserIntegration
from app.api.deps import get_current_user
from app.config import settings

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/integrations", tags=["Integrations"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
]

# The single redirect URI registered in Google Cloud Console
def _backend_callback_uri() -> str:
    return f"{settings.BACKEND_URL}/api/integrations/google/callback"


# ── Step 1: generate auth URL ─────────────────────────────────────────────────

@router.get("/google/auth-url")
async def get_google_auth_url(
    current_user: User = Depends(get_current_user),
):
    """Return the Google OAuth2 authorization URL.

    Encodes the current user's ID in a signed `state` parameter so the
    backend callback can identify them without needing a session cookie.
    """
    from app.core.google_auth import get_google_auth_url as build_url, create_oauth_state

    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        logger.error("google_oauth_not_configured")
        return {"auth_url": None, "error": "Google OAuth credentials not configured on the server."}

    redirect_uri = _backend_callback_uri()
    state = create_oauth_state(str(current_user.id), settings.SECRET_KEY)
    auth_url = await build_url(
        redirect_uri=redirect_uri,
        scopes=GOOGLE_SCOPES,
        state=state,
    )
    logger.info("google_auth_url_generated", user_id=current_user.id, redirect_uri=redirect_uri)
    # redirect_uri is returned so the UI can show users exactly what to register
    # in Google Cloud Console → Credentials → Authorized redirect URIs
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


# ── Step 2: backend callback (Google redirects here) ─────────────────────────

@router.get("/google/callback")
async def google_oauth_backend_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google's OAuth2 redirect.

    This endpoint is called by Google — NO Authorization header is present.
    User identity is recovered from the signed `state` token.
    After saving tokens the user is redirected back to the frontend.
    """
    from app.core.google_auth import decode_oauth_state, exchange_code_for_tokens

    frontend = settings.FRONTEND_URL

    # ── Error from Google consent screen ──────────────────────────────────
    if error:
        logger.warning("google_oauth_user_denied", error=error)
        return RedirectResponse(f"{frontend}/?gmail_error={error}", status_code=302)

    if not code or not state:
        logger.warning("google_oauth_missing_params")
        return RedirectResponse(f"{frontend}/?gmail_error=missing_params", status_code=302)

    # ── Verify CSRF state & extract user_id ───────────────────────────────
    try:
        user_id = decode_oauth_state(state, settings.SECRET_KEY)
    except ValueError as exc:
        logger.warning("google_oauth_invalid_state", error=str(exc))
        return RedirectResponse(f"{frontend}/?gmail_error=invalid_state", status_code=302)

    # ── Load user ─────────────────────────────────────────────────────────
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error("google_oauth_user_not_found", user_id=user_id)
        return RedirectResponse(f"{frontend}/?gmail_error=user_not_found", status_code=302)

    # ── Exchange code for tokens ───────────────────────────────────────────
    try:
        tokens = await exchange_code_for_tokens(
            code=code,
            redirect_uri=_backend_callback_uri(),
            scopes=GOOGLE_SCOPES,
        )
    except Exception as exc:
        logger.error("google_oauth_token_exchange_failed", error=str(exc), user_id=user_id)
        return RedirectResponse(f"{frontend}/?gmail_error=token_exchange_failed", status_code=302)

    if not tokens.get("refresh_token"):
        # refresh_token is absent when the user has already granted once.
        # force revoke + reconnect by returning a helpful error.
        logger.warning("google_oauth_no_refresh_token", user_id=user_id)
        return RedirectResponse(f"{frontend}/?gmail_error=no_refresh_token", status_code=302)

    # ── Save / update UserIntegration ─────────────────────────────────────
    stmt = select(UserIntegration).where(
        UserIntegration.user_id == user.id,
        UserIntegration.service_name == "google",
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()

    if integration:
        integration.access_token  = tokens.get("access_token")
        integration.refresh_token = tokens.get("refresh_token")
        integration.is_active     = True
    else:
        integration = UserIntegration(
            user_id       = user.id,
            service_name  = "google",
            access_token  = tokens.get("access_token"),
            refresh_token = tokens.get("refresh_token"),
            scopes        = GOOGLE_SCOPES,
            is_active     = True,
        )
        db.add(integration)

    user.google_oauth_token    = tokens
    user.google_refresh_token  = tokens.get("refresh_token")
    await db.commit()

    logger.info("google_oauth_connected", user_id=user.id)
    return RedirectResponse(f"{frontend}/?gmail_connected=1", status_code=302)


# ── Integration status ────────────────────────────────────────────────────────

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
        "google_gmail":  False,
        "google_drive":  False,
        "supabase":      bool(settings.SUPABASE_URL),
        "upstash_redis": bool(settings.UPSTASH_REDIS_URL),
    }
    for i in integrations:
        if i.service_name == "google" and i.is_active:
            services["google_gmail"] = True
            services["google_drive"] = True

    # Fallback: env-level refresh token counts as connected
    if not services["google_gmail"] and (
        current_user.google_refresh_token or settings.GOOGLE_REFRESH_TOKEN
    ):
        services["google_gmail"] = True

    return {"integrations": services}


# ── Disconnect ────────────────────────────────────────────────────────────────

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
        integration.is_active     = False
        integration.access_token  = None
        integration.refresh_token = None

    current_user.google_refresh_token = None
    current_user.google_oauth_token   = None
    await db.commit()
    logger.info("google_oauth_disconnected", user_id=current_user.id)
    return {"status": "disconnected"}

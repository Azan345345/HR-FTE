"""Google OAuth2 helper for Gmail / Drive integration.

Flow (backend-callback):
  1. /integrations/google/auth-url  → builds URL with redirect_uri = BACKEND_URL/api/integrations/google/callback
                                       and a signed `state` JWT containing user_id
  2. User approves → Google redirects GET /api/integrations/google/callback?code=...&state=...
  3. Backend verifies state, exchanges code, saves tokens, redirects to FRONTEND_URL/?gmail_connected=1
"""

import base64
import hashlib
import hmac
import json
import time
import structlog
from typing import Optional

from app.config import settings

logger = structlog.get_logger()

# ── State parameter (CSRF protection) ────────────────────────────────────────

def create_oauth_state(user_id: str, secret: str) -> str:
    """Create a compact signed state token encoding user_id + timestamp.

    Format (base64url-encoded): JSON_payload.hex_signature
    """
    payload = json.dumps({"uid": str(user_id), "ts": int(time.time())})
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:20]
    raw = f"{payload}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_oauth_state(state: str, secret: str) -> str:
    """Decode and verify state token. Returns user_id string.

    Raises ValueError on tampered or expired state.
    """
    # Restore padding
    padding = (4 - len(state) % 4) % 4
    state_padded = state + "=" * padding
    try:
        raw = base64.urlsafe_b64decode(state_padded.encode()).decode()
    except Exception:
        raise ValueError("State token is not valid base64")

    try:
        payload_str, sig = raw.rsplit(".", 1)
    except ValueError:
        raise ValueError("State token missing signature")

    expected = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()[:20]
    if not hmac.compare_digest(sig, expected):
        raise ValueError("State signature mismatch — possible CSRF attempt")

    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        raise ValueError("State payload is not valid JSON")

    if int(time.time()) - data.get("ts", 0) > 900:  # 15-minute window
        raise ValueError("State token expired")

    return str(data["uid"])


# ── OAuth flow helpers ────────────────────────────────────────────────────────

def _client_config(client_id: str, client_secret: str) -> dict:
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{settings.BACKEND_URL}/api/integrations/google/callback"],
        }
    }


async def get_google_auth_url(
    redirect_uri: str,
    scopes: list[str],
    state: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> str:
    """Generate Google OAuth2 authorization URL."""
    from google_auth_oauthlib.flow import Flow

    cid = client_id or settings.GOOGLE_OAUTH_CLIENT_ID
    csecret = client_secret or settings.GOOGLE_OAUTH_CLIENT_SECRET

    flow = Flow.from_client_config(
        _client_config(cid, csecret),
        scopes=scopes,
        redirect_uri=redirect_uri,
    )
    kwargs: dict = {"prompt": "consent", "access_type": "offline"}
    if state:
        kwargs["state"] = state
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url


async def exchange_code_for_tokens(
    code: str,
    redirect_uri: str,
    scopes: list[str],
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    from google_auth_oauthlib.flow import Flow

    cid = client_id or settings.GOOGLE_OAUTH_CLIENT_ID
    csecret = client_secret or settings.GOOGLE_OAUTH_CLIENT_SECRET

    flow = Flow.from_client_config(
        _client_config(cid, csecret),
        scopes=scopes,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token":  creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "expiry":        creds.expiry.isoformat() if creds.expiry else None,
    }

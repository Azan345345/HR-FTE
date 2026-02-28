#!/usr/bin/env python3
"""
Gmail OAuth2 Token Generator — works with any credential type.
Tries InstalledAppFlow first (no GCP changes needed for Desktop-app credentials).
Falls back with exact GCP instructions if Web-app credentials require a registered URI.

Usage:
    cd "D:/Projects/FTE HR/backend"
    python scripts/generate_gmail_token.py
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
ROOT_DIR    = BACKEND_DIR.parent
ENV_PATH    = ROOT_DIR / ".env"
DB_PATH     = BACKEND_DIR / "digital_fte.db"

# ── Load env ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
except ImportError:
    pass

CLIENT_ID     = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print(f"\n[ERROR] GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET missing in {ENV_PATH}")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# ── Save helpers ──────────────────────────────────────────────────────────────

def save_to_env(refresh_token: str):
    if not ENV_PATH.exists():
        print(f"WARNING: {ENV_PATH} not found — add manually: GOOGLE_REFRESH_TOKEN=\"{refresh_token}\"")
        return
    content = ENV_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    if any(l.startswith("GOOGLE_REFRESH_TOKEN") for l in lines):
        new_lines = [
            f'GOOGLE_REFRESH_TOKEN="{refresh_token}"' if l.startswith("GOOGLE_REFRESH_TOKEN") else l
            for l in lines
        ]
        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        with ENV_PATH.open("a", encoding="utf-8") as f:
            f.write(f'\nGOOGLE_REFRESH_TOKEN="{refresh_token}"\n')
    print(f"[OK] .env updated: GOOGLE_REFRESH_TOKEN written")


def save_to_db(refresh_token: str):
    if not DB_PATH.exists():
        print(f"INFO: DB not found at {DB_PATH} — skipping DB update")
        return
    try:
        con = sqlite3.connect(str(DB_PATH))
        cur = con.cursor()
        cur.execute(
            "UPDATE user_integrations SET refresh_token=?, access_token=NULL, is_active=1, updated_at=datetime('now') WHERE service_name IN ('google','gmail')",
            (refresh_token,),
        )
        rows = cur.rowcount
        cur.execute(
            "UPDATE users SET google_refresh_token=?, google_oauth_token=NULL",
            (refresh_token,),
        )
        con.commit()
        con.close()
        print(f"[OK] DB updated: {rows} integration row(s) reactivated, users table updated")
    except Exception as e:
        print(f"WARNING: DB update failed — {e}")


def finish(refresh_token: str):
    print("\n" + "=" * 60)
    print("  SUCCESS — New refresh token obtained")
    print("=" * 60)
    print(f"\n  {refresh_token}\n")
    save_to_env(refresh_token)
    save_to_db(refresh_token)
    print("\nNext steps:")
    print("  1. Restart backend:  uvicorn app.main:app --reload")
    print("  2. Restart frontend: npm run dev  (if it was stopped)")
    print("  3. Settings → Data Sources → Gmail should show Connected")
    print("  4. Retry sending the email\n")
    sys.exit(0)


# ── Method 1: InstalledAppFlow (works for Desktop-app credentials) ────────────

def try_installed_flow():
    """
    Uses google-auth-oauthlib InstalledAppFlow with a random localhost port.
    Google allows any localhost port for Desktop-app type credentials — no URI
    registration needed.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("INFO: google-auth-oauthlib not available, skipping InstalledAppFlow")
        return None

    client_config = {
        "installed": {
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    print("Opening browser for Google authorization...")
    print("(If browser does not open automatically, copy the URL printed below)\n")

    try:
        # port=0 picks a random free port — works for Desktop-app credentials
        creds = flow.run_local_server(
            port=0,
            prompt="consent",
            access_type="offline",
            open_browser=True,
        )
        return creds.refresh_token
    except Exception as e:
        err = str(e)
        if "redirect_uri_mismatch" in err or "400" in err:
            print(f"\nINFO: InstalledAppFlow failed (likely Web-app credentials): {err[:120]}")
            return None
        raise


# ── Method 2: Manual flow with step-by-step GCP instructions ──────────────────

def manual_flow():
    """
    Guides user to add http://localhost:8765/callback to Google Cloud Console,
    then runs a local server to capture the OAuth code automatically.
    """
    import webbrowser
    import threading
    from urllib.parse import urlencode, urlparse, parse_qs
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.request

    REDIRECT_URI = "http://localhost:8765/callback"

    print("\n" + "=" * 60)
    print("  Manual setup required (Web-app credentials)")
    print("=" * 60)
    print("""
You need to add ONE redirect URI to your Google Cloud Console.
This takes about 30 seconds and only needs to be done ONCE.

STEPS:
  1. Open: https://console.cloud.google.com/apis/credentials
  2. Click your OAuth 2.0 Client ID (starts with 669017541627)
  3. Under "Authorized redirect URIs" click "+ ADD URI"
  4. Paste exactly:  http://localhost:8765/callback
  5. Click SAVE (blue button at bottom)
""")
    input("  Press ENTER once you have saved in Google Cloud Console... ")

    # Build auth URL
    params = {
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

    # Local callback server
    _result: dict = {}
    _ready = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            code  = qs.get("code",  [None])[0]
            error = qs.get("error", [None])[0]
            if code:
                _result["code"] = code
                body = b"<h2 style='font-family:sans-serif;color:green'>Success! Return to the terminal.</h2>"
                self.send_response(200)
            else:
                _result["error"] = error or "unknown"
                body = f"<h2 style='color:red'>Error: {error}</h2>".encode()
                self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            _ready.set()
        def log_message(self, *a): pass

    try:
        server = HTTPServer(("localhost", 8765), Handler)
    except OSError as e:
        print(f"\n[ERROR] Cannot bind port 8765: {e}")
        print("Kill any process using port 8765 and retry.")
        sys.exit(1)

    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    print(f"\nOpening browser...\n  {auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        print("Copy the URL above into your browser.\n")

    print("Waiting for authorization (sign in + Allow in browser)...\n")
    ok = _ready.wait(timeout=180)
    server.server_close()

    if not ok or "code" not in _result:
        print(f"[ERROR] Authorization failed or timed out. Error: {_result.get('error')}")
        sys.exit(1)

    code = _result["code"]
    print("Code received. Exchanging for tokens...")

    data = urlencode({
        "code":          code,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read().decode())

    rt = tokens.get("refresh_token")
    if not rt:
        print("\n[ERROR] No refresh_token returned.")
        print("Revoke app at https://myaccount.google.com/permissions then retry.")
        sys.exit(1)

    return rt


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Gmail OAuth2 Token Generator")
    print("=" * 60)
    print(f"\n  Client ID: {CLIENT_ID[:28]}...\n")

    # Try Method 1: InstalledAppFlow (no GCP changes needed)
    print("Attempting InstalledAppFlow (Desktop-app credentials)...\n")
    rt = try_installed_flow()
    if rt:
        finish(rt)

    # Fall back to Method 2: manual flow with GCP URI registration
    print("\nFalling back to manual flow (Web-app credentials)...")
    rt = manual_flow()
    finish(rt)

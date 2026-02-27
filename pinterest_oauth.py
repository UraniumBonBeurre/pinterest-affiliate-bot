"""
pinterest_oauth.py
------------------
Script de démonstration du flux OAuth Pinterest v5.
À lancer UNE FOIS pour obtenir un access token + refresh token.
Le token est ensuite sauvegardé dans .env pour les GitHub Actions.

Usage:
    python pinterest_oauth.py

Prérequis:
    pip install requests python-dotenv

Config requise dans .env:
    PINTEREST_APP_ID=your_app_id
    PINTEREST_APP_SECRET=your_app_secret
    PINTEREST_REDIRECT_URI=http://localhost:8080/callback
"""

import os
import sys
import json
import base64
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
APP_ID       = os.getenv("PINTEREST_APP_ID")
APP_SECRET   = os.getenv("PINTEREST_APP_SECRET")
REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI", "http://localhost:8080/callback")
SCOPES       = "pins:read,pins:write,boards:read,boards:write,user_accounts:read"

AUTH_URL     = "https://www.pinterest.com/oauth/"
TOKEN_URL    = "https://api.pinterest.com/v5/oauth/token"
DOTENV_PATH  = ".env"

# ── Shared state ──────────────────────────────────────────────────────────────
auth_code = None

# ── Local callback server ─────────────────────────────────────────────────────
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:sans-serif;text-align:center;padding:60px">
                <h2 style="color:#E60023">&#10003; Pinterest authorization received!</h2>
                <p>You can close this tab and return to your terminal.</p>
                </body></html>
            """)
            print(f"\n✅  Authorization code received: {auth_code[:12]}...")
        else:
            error = params.get("error", ["Unknown"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"OAuth error: {error}".encode())
            print(f"\n❌  OAuth error received: {error}")

    def log_message(self, *args):
        pass  # Silence les logs HTTP pour la démo


def start_local_server():
    port = int(REDIRECT_URI.split(":")[-1].split("/")[0])
    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()
    return server


# ── OAuth flow ────────────────────────────────────────────────────────────────
def build_auth_url():
    params = {
        "client_id":     APP_ID,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code_for_token(code):
    credentials = base64.b64encode(f"{APP_ID}:{APP_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": REDIRECT_URI,
    }
    print("\n🔄  Exchanging authorization code for access token...")
    print(f"    → POST {TOKEN_URL}")

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    print(f"    ← HTTP {response.status_code}")

    if response.status_code != 200:
        print(f"\n❌  Error: {response.text}")
        sys.exit(1)

    return response.json()


def save_tokens(token_data):
    access_token  = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in    = token_data.get("expires_in", "N/A")

    set_key(DOTENV_PATH, "PINTEREST_ACCESS_TOKEN",  access_token)
    set_key(DOTENV_PATH, "PINTEREST_REFRESH_TOKEN", refresh_token)

    print(f"\n💾  Tokens saved to {DOTENV_PATH}")
    print(f"    access_token  : {access_token[:20]}...")
    print(f"    refresh_token : {refresh_token[:20]}...")
    print(f"    expires_in    : {expires_in}s")
    return access_token


def verify_token(access_token):
    print("\n🔍  Verifying token via GET /v5/user_account...")
    resp = requests.get(
        "https://api.pinterest.com/v5/user_account",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(f"    ← HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n✅  Authenticated as: @{data.get('username', '?')}")
    else:
        print(f"\n⚠️  Unexpected response: {resp.text}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Pinterest OAuth 2.0 — Full Authorization Flow")
    print("=" * 60)

    # Validate config
    if not APP_ID or not APP_SECRET:
        print("\n❌  PINTEREST_APP_ID and PINTEREST_APP_SECRET are required in .env")
        sys.exit(1)

    print(f"\n📋  App ID      : {APP_ID}")
    print(f"    Redirect URI: {REDIRECT_URI}")
    print(f"    Scopes      : {SCOPES}")

    # Step 1: Start local callback server
    print("\n⏳  Starting local callback server...")
    start_local_server()
    print(f"    Listening on {REDIRECT_URI}")

    # Step 2: Open browser
    auth_url = build_auth_url()
    print(f"\n🌐  Opening browser for Pinterest authorization...")
    print(f"    URL : {auth_url[:80]}...")
    webbrowser.open(auth_url)

    # Step 3: Wait for callback
    print("\n⏳  Waiting for Pinterest callback (authorize the app in your browser)...")
    import time
    timeout = 120
    elapsed = 0
    while auth_code is None and elapsed < timeout:
        time.sleep(1)
        elapsed += 1

    if auth_code is None:
        print("\n❌  Timeout — no authorization code received after 120 seconds.")
        sys.exit(1)

    # Step 4: Exchange code for token
    token_data = exchange_code_for_token(auth_code)

    # Step 5: Save tokens
    access_token = save_tokens(token_data)

    # Step 6: Verify
    verify_token(access_token)

    print("\n" + "=" * 60)
    print("  ✅  OAuth flow complete — Token saved and ready for GitHub Actions")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
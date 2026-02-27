"""
refresh_pinterest_token.py
--------------------------
Refreshes the Pinterest access token using the refresh token.
Automatically updates the GitHub Actions secret via the GitHub API.

Run this script as a scheduled GitHub Actions job (e.g. every 20 days)
to keep the token valid indefinitely without any manual intervention.

Usage:
    python3 refresh_pinterest_token.py

Required environment variables (GitHub Actions secrets):
    PINTEREST_APP_ID
    PINTEREST_APP_SECRET
    PINTEREST_REFRESH_TOKEN
    GH_TOKEN              ← GitHub personal access token with repo secrets write access
    GH_REPO               ← e.g. "nicolasmalpot/pinterest-affiliate-bot"
"""

import os
import sys
import base64
import json
import requests
from base64 import b64encode
from nacl import encoding, public  # pip install PyNaCl

# ── Config ────────────────────────────────────────────────────────────────────
APP_ID        = os.getenv("PINTEREST_APP_ID")
APP_SECRET    = os.getenv("PINTEREST_APP_SECRET")
REFRESH_TOKEN = os.getenv("PINTEREST_REFRESH_TOKEN")
GH_TOKEN      = os.getenv("GH_TOKEN")
GH_REPO       = os.getenv("GH_REPO")  # "owner/repo"

PINTEREST_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
GITHUB_API_BASE     = "https://api.github.com"


# ── Pinterest token refresh ───────────────────────────────────────────────────
def refresh_access_token():
    print("🔄  Refreshing Pinterest access token...")
    credentials = base64.b64encode(f"{APP_ID}:{APP_SECRET}".encode()).decode()
    response = requests.post(
        PINTEREST_TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        data={
            "grant_type":    "refresh_token",
            "refresh_token": REFRESH_TOKEN,
        }
    )
    print(f"    ← HTTP {response.status_code}")
    if response.status_code != 200:
        print(f"❌  Pinterest refresh error: {response.text}")
        sys.exit(1)

    data = response.json()
    print(f"    ✅  New access_token  : {data['access_token'][:20]}...")
    print(f"    ✅  New refresh_token : {data['refresh_token'][:20]}...")
    print(f"    ✅  Expires in        : {data['expires_in']}s")
    return data["access_token"], data["refresh_token"]


# ── GitHub secret update ──────────────────────────────────────────────────────
def get_repo_public_key():
    url = f"{GITHUB_API_BASE}/repos/{GH_REPO}/actions/secrets/public-key"
    resp = requests.get(url, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
    })
    if resp.status_code != 200:
        print(f"❌  GitHub public key error: {resp.text}")
        sys.exit(1)
    return resp.json()["key_id"], resp.json()["key"]


def encrypt_secret(public_key_str: str, secret_value: str) -> str:
    public_key_obj = public.PublicKey(public_key_str.encode(), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key_obj)
    encrypted = sealed_box.encrypt(secret_value.encode())
    return b64encode(encrypted).decode()


def update_github_secret(secret_name: str, secret_value: str, key_id: str, public_key: str):
    encrypted = encrypt_secret(public_key, secret_value)
    url = f"{GITHUB_API_BASE}/repos/{GH_REPO}/actions/secrets/{secret_name}"
    resp = requests.put(url, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
    }, json={
        "encrypted_value": encrypted,
        "key_id": key_id,
    })
    if resp.status_code in (201, 204):
        print(f"    ✅  GitHub secret '{secret_name}' updated")
    else:
        print(f"❌  Failed to update '{secret_name}': {resp.text}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Pinterest Token Auto-Refresh")
    print("=" * 60)

    for var in ["APP_ID", "APP_SECRET", "REFRESH_TOKEN", "GH_TOKEN", "GH_REPO"]:
        if not globals().get(var) and not os.getenv(f"PINTEREST_{var}") and not os.getenv(f"GH_{var}"):
            pass  # checked below
    missing = [v for v in ["APP_ID", "APP_SECRET", "REFRESH_TOKEN"] if not os.getenv(f"PINTEREST_{v}")]
    missing += [v for v in ["GH_TOKEN", "GH_REPO"] if not os.getenv(v)]
    if missing:
        print(f"❌  Missing env vars: {missing}")
        sys.exit(1)

    # Step 1: Refresh Pinterest token
    new_access_token, new_refresh_token = refresh_access_token()

    # Step 2: Get GitHub repo public key for encryption
    print("\n🔑  Fetching GitHub repo public key...")
    key_id, public_key = get_repo_public_key()

    # Step 3: Update both secrets in GitHub
    print("\n📤  Updating GitHub Actions secrets...")
    update_github_secret("PINTEREST_ACCESS_TOKEN",  new_access_token,  key_id, public_key)
    update_github_secret("PINTEREST_REFRESH_TOKEN", new_refresh_token, key_id, public_key)

    print("\n" + "=" * 60)
    print("  ✅  Tokens refreshed and GitHub secrets updated automatically")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

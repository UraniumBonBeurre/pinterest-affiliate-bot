"""
direct_test_public_posting_pinterest.py
----------------------------------------
Quick test: publishes one pin to your real Pinterest board
using the production API (Standard Access).

Usage:
    python3 direct_test_public_posting_pinterest.py

.env required:
    PINTEREST_ACCESS_TOKEN=pina_...
    PINTEREST_BOARD_ID=...
    PINTEREST_API_BASE=https://api.pinterest.com/v5
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
BOARD_ID     = os.getenv("PINTEREST_BOARD_ID")
API_BASE     = os.getenv("PINTEREST_API_BASE", "https://api.pinterest.com/v5")

# ── Pin data ──────────────────────────────────────────────────────────────────
PIN = {
    "title":       "Modern Scandinavian Living Room — Warm Oak & Linen",
    "description": "Minimalist home decor: oak coffee table, linen sofa, warm lighting. Shop via Amazon affiliate link.",
    "link":        "https://www.amazon.com/your-affiliate-link",
    "board_id":    BOARD_ID,
    "media_source": {
        "source_type": "image_url",
        "url": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800"
    }
}

# ── Post ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Pinterest API — Production Pin Test (Standard Access)")
    print("=" * 60)

    if not ACCESS_TOKEN or not BOARD_ID:
        print("\n❌  Missing PINTEREST_ACCESS_TOKEN or PINTEREST_BOARD_ID in .env")
        sys.exit(1)

    print(f"\n📋  API      : {API_BASE}")
    print(f"    Board ID : {BOARD_ID}")
    print(f"    Token    : {ACCESS_TOKEN[:15]}...")

    print(f"\n📌  Posting pin...")
    print(f"    → POST {API_BASE}/pins")

    response = requests.post(
        f"{API_BASE}/pins",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type":  "application/json",
        },
        json=PIN,
    )

    print(f"    ← HTTP {response.status_code}")

    if response.status_code == 201:
        data = response.json()
        pin_id = data.get("id")
        print(f"\n✅  Success!")
        print(f"    Pin ID  : {pin_id}")
        print(f"    Pin URL : https://www.pinterest.com/pin/{pin_id}/")
    else:
        try:
            err = response.json()
            print(f"\n❌  Error {err.get('code')}: {err.get('message')}")
        except Exception:
            print(f"\n❌  {response.text}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  ✅  Pin live on Pinterest — Standard Access confirmed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

"""
publish_pins.py
---------------
Publishes an original AI-generated home decor pin to Pinterest
using the POST /v5/pins endpoint.

This is a private internal CLI tool — I am the sole user.
Authentication uses the OAuth access token obtained via pinterest_oauth.py.

Usage:
    python publish_pins.py

Requirements:
    pip install requests python-dotenv pillow

.env required keys:
    PINTEREST_ACCESS_TOKEN=your_access_token
    PINTEREST_BOARD_ID=your_board_id
    PINTEREST_API_BASE=https://api.pinterest.com/v5
"""

import os
import sys
import json
import base64
import textwrap
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
BOARD_ID     = os.getenv("PINTEREST_BOARD_ID")
API_BASE     = os.getenv("PINTEREST_API_BASE", "https://api.pinterest.com/v5")

PINS_ENDPOINT = f"{API_BASE}/pins"

# ── Sample pin data (would normally come from AI generation pipeline) ─────────
SAMPLE_PIN = {
    "title": "Modern Scandinavian Living Room — Warm Oak & Linen Sofa Set",
    "description": (
        "Minimalist home decor inspiration: oak coffee table, linen sofa, "
        "and warm ambient lighting. All items available via Amazon affiliate links."
    ),
    "link": "https://www.amazon.com/your-affiliate-link",  # affiliate destination URL
    "board_id": BOARD_ID,
    "media_source": {
        "source_type": "image_url",
        # Using a placeholder public image for demo purposes
        "url": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800"
    }
}


# ── Pin creation ──────────────────────────────────────────────────────────────
def create_pin(pin_data: dict) -> dict:
    """
    Calls POST /v5/pins to publish a pin on Pinterest.
    Returns the API response as a dict.
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type":  "application/json",
    }

    print(f"\n📌  Creating pin via Pinterest API...")
    print(f"    → POST {PINS_ENDPOINT}")
    print(f"    → Board ID  : {pin_data['board_id']}")
    print(f"    → Title     : {pin_data['title'][:60]}...")
    print(f"    → Link      : {pin_data['link']}")
    print(f"    → Image URL : {pin_data['media_source']['url'][:60]}...")

    response = requests.post(
        PINS_ENDPOINT,
        headers=headers,
        json=pin_data,
    )

    print(f"\n    ← HTTP {response.status_code}")
    return response


def handle_response(response):
    if response.status_code == 201:
        data = response.json()
        pin_id = data.get("id", "N/A")
        print(f"\n✅  Pinterest Publish Success!")
        print(f"    Pin ID   : {pin_id}")
        print(f"    Pin URL  : https://www.pinterest.com/pin/{pin_id}/")
        print(f"    Board ID : {data.get('board_id', 'N/A')}")
        return data
    else:
        print(f"\n❌  Pinterest API error:")
        try:
            error = response.json()
            print(f"    Code    : {error.get('code', 'N/A')}")
            print(f"    Message : {error.get('message', response.text)}")
        except Exception:
            print(f"    Response: {response.text}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Pinterest Pin Publisher — POST /v5/pins")
    print("=" * 60)

    # Validate config
    if not ACCESS_TOKEN:
        print("\n❌  PINTEREST_ACCESS_TOKEN not found in .env")
        print("    Run pinterest_oauth.py first to obtain a token.")
        sys.exit(1)

    if not BOARD_ID:
        print("\n❌  PINTEREST_BOARD_ID not found in .env")
        sys.exit(1)

    print(f"\n📋  API Base     : {API_BASE}")
    print(f"    Board ID    : {BOARD_ID}")
    print(f"    Token       : {ACCESS_TOKEN[:15]}...")

    # Create the pin
    response = create_pin(SAMPLE_PIN)

    # Handle result
    handle_response(response)

    print("\n" + "=" * 60)
    print("  ✅  Workflow complete — Pin live on Pinterest")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

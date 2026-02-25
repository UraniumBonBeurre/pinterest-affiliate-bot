import json
import logging
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POOL_FILE = DATA_DIR / "asin_pool.json"

def load_pool():
    if not POOL_FILE.exists():
        return []
    with open(POOL_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_pool(pool_data):
    with open(POOL_FILE, 'w', encoding='utf-8') as f:
        json.dump(pool_data, f, indent=4, ensure_ascii=False)

def get_available_asins():
    pool = load_pool()
    return [item for item in pool if not item.get("used", False)]

def mark_as_used(asin):
    pool = load_pool()
    for item in pool:
        if item.get("asin") == asin:
            item["used"] = True
            break
    save_pool(pool)

def check_pool_health():
    """Returns True if pool has < 50 items available, to trigger notifications"""
    available = len(get_available_asins())
    logging.info(f"ASIN pool health check: {available} unused ASINs available.")
    return available < 50

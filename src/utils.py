import json
import re
from datetime import datetime
from pathlib import Path

def slugify(text: str) -> str:
    """
    Clean a string to make it a slug
    """
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

def save_json(path: Path, data: dict):
    """
    Save dict to a JSON file
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(path: Path) -> dict:
    """
    Load dict from a JSON file
    """
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def now_ts() -> str:
    """
    Current timestamp formatted for logs
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

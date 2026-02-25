import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
LOGS_DIR = OUTPUT_DIR / "logs"

# Ensure directories exist
for directory in [DATA_DIR, IMAGES_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys for Image Generation
HF_TOKEN = os.getenv("HF_TOKEN")# Pinterest Settings
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
PINTEREST_API_BASE = os.getenv("PINTEREST_API_BASE", "https://api-sandbox.pinterest.com/v5").rstrip('/')
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID")

# Affiliates Settings
AMAZON_ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "")
DEFAULT_NICHE = os.getenv("DEFAULT_NICHE", "general")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "fr")
PUBLISH_DRY_RUN = os.getenv("PUBLISH_DRY_RUN", "true").lower() in ["true", "1", "yes"]
PINS_PER_DAY = int(os.getenv("PINS_PER_DAY", "5"))

# Cloudflare R2 Settings
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_HASH = os.getenv("R2_PUBLIC_HASH")


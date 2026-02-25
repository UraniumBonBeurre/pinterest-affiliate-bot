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

# Together API Settings
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Pinterest Settings
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
PINTEREST_API_BASE = os.getenv("PINTEREST_API_BASE", "https://api-sandbox.pinterest.com/v5").rstrip('/')
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID")

# Affiliates Settings
AMAZON_ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "")
DEFAULT_NICHE = os.getenv("DEFAULT_NICHE", "general")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "fr")
PUBLISH_DRY_RUN = os.getenv("PUBLISH_DRY_RUN", "true").lower() in ["true", "1", "yes"]

# Cloudinary Settings
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "pinterest_pins")

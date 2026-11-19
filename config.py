import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Project and Database configuration from README
DEFAULT_PROJECT_ID = "gen-lang-client-0880363053"
DEFAULT_DATABASE_ID = "ai-studio-android-volthabi-49d89ac7-d707-4fd5-8572-478243a64893"

PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", DEFAULT_PROJECT_ID)
DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID", DEFAULT_DATABASE_ID)
USER_ID = os.getenv("FIREBASE_USER_ID") or os.getenv("USER_ID", "")
SERVICE_ACCOUNT_KEY = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# Optional Web API / User Auth (if using Firebase REST or user tokens)
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
FIREBASE_USER_EMAIL = os.getenv("FIREBASE_USER_EMAIL", "")
FIREBASE_USER_PASSWORD = os.getenv("FIREBASE_USER_PASSWORD", "")
FIREBASE_ID_TOKEN = os.getenv("FIREBASE_ID_TOKEN", "")

# UI Design Tokens
COLOR_PITCH_BLACK = "#09090B"
COLOR_DARK_ZINC = "#18181B"
COLOR_CARD_BG = "#121215"
COLOR_CRISP_WHITE = "#FAFAFA"
COLOR_MUTED_TEXT = "#A1A1AA"
COLOR_NEON_GREEN = "#39FF14"
COLOR_NEON_GLOW = "rgba(57, 255, 20, 0.45)"
COLOR_BORDER_GREEN = "#39FF14"
COLOR_ERROR_RED = "#EF4444"

# Window Dimension Tokens
WIDGET_WIDTH = 300
WIDGET_HEIGHT = 380

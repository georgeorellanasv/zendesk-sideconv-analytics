"""
Configuration module — loads .env and exposes typed constants.
Fails fast with a clear error if required variables are missing.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is two levels up from this file (src/config.py -> src/ -> root/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from project root (no-op if already loaded or file missing)
load_dotenv(PROJECT_ROOT / ".env")


def _require(var: str) -> str:
    """Return env var value or raise with a helpful message."""
    value = os.getenv(var, "").strip()
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: {var}\n"
            f"Copy .env.example to .env and fill in your credentials."
        )
    return value


# --- Required credentials ---
ZENDESK_SUBDOMAIN: str = _require("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL: str = _require("ZENDESK_EMAIL")
ZENDESK_TOKEN: str = _require("ZENDESK_TOKEN")

# --- Derived constants ---
BASE_URL: str = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com"
AUTH: tuple[str, str] = (f"{ZENDESK_EMAIL}/token", ZENDESK_TOKEN)

# --- Custom field IDs (optional until Fase 1+) ---
FIELD_ID_REASON_FOR_CONTACT: str = os.getenv("FIELD_ID_REASON_FOR_CONTACT", "")
FIELD_ID_CORRESPONDENT: str = os.getenv("FIELD_ID_CORRESPONDENT", "")
FIELD_ID_CORRESPONDENT_NUMBER: str = os.getenv("FIELD_ID_CORRESPONDENT_NUMBER", "")
FIELD_ID_COUNTRY: str = os.getenv("FIELD_ID_COUNTRY", "")
FIELD_ID_PRODUCT: str = os.getenv("FIELD_ID_PRODUCT", "")

# --- View IDs ---
VIEW_ID_US_CARE: str = os.getenv("VIEW_ID_US_CARE", "")

# --- Proxy (optional, for corporate environments) ---
HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "")

PROXIES: dict[str, str] | None = (
    {"http": HTTP_PROXY, "https": HTTPS_PROXY}
    if HTTP_PROXY or HTTPS_PROXY
    else None
)

# --- Paths ---
DB_PATH: Path = PROJECT_ROOT / "data" / "sideconv.db"
LOG_PATH: Path = PROJECT_ROOT / "logs" / "extractor.log"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"

# Ensure directories exist at import time
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(REPORTS_DIR / "discovery").mkdir(parents=True, exist_ok=True)

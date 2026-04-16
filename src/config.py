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


# --- Credentials (only needed by the extractor / discovery scripts) ---
# Not required for the dashboard, which only reads the local DB.
# The ZendeskClient will raise a clear error if credentials are missing when
# an API call is actually attempted.
ZENDESK_SUBDOMAIN: str = os.getenv("ZENDESK_SUBDOMAIN", "").strip()
ZENDESK_EMAIL: str    = os.getenv("ZENDESK_EMAIL", "").strip()
ZENDESK_TOKEN: str    = os.getenv("ZENDESK_TOKEN", "").strip()


def require_zendesk_credentials() -> None:
    """Raise if Zendesk credentials are missing. Call this from the extractor only."""
    missing = [
        name for name, val in {
            "ZENDESK_SUBDOMAIN": ZENDESK_SUBDOMAIN,
            "ZENDESK_EMAIL":     ZENDESK_EMAIL,
            "ZENDESK_TOKEN":     ZENDESK_TOKEN,
        }.items() if not val
    ]
    if missing:
        raise EnvironmentError(
            "Missing required environment variables: " + ", ".join(missing)
            + "\nCopy .env.example to .env and fill in your credentials."
        )

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

# --- SSL (set to "false" in corporate environments with SSL inspection) ---
SSL_VERIFY: bool | str = os.getenv("SSL_VERIFY", "true").lower() != "false"

PROXIES: dict[str, str] | None = (
    {"http": HTTP_PROXY, "https": HTTPS_PROXY}
    if HTTP_PROXY or HTTPS_PROXY
    else None
)

# --- Paths ---
# Use the real DB if present, otherwise fall back to the demo (anonymized) DB.
# Override with SIDECONV_DB env var if needed.
_DEFAULT_DB = PROJECT_ROOT / "data" / "sideconv.db"
_DEMO_DB    = PROJECT_ROOT / "data" / "sideconv_demo.db"
_DB_OVERRIDE = os.getenv("SIDECONV_DB", "").strip()

if _DB_OVERRIDE:
    DB_PATH: Path = Path(_DB_OVERRIDE)
elif _DEFAULT_DB.exists():
    DB_PATH = _DEFAULT_DB
else:
    DB_PATH = _DEMO_DB

LOG_PATH: Path = PROJECT_ROOT / "logs" / "extractor.log"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"

# Ensure directories exist at import time
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(REPORTS_DIR / "discovery").mkdir(parents=True, exist_ok=True)

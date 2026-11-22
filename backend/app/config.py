"""Application configuration and defaults for KPSS Radar."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
PROJECT_ROOT = BASE_DIR.parent  # .../kpss
DATA_DIR = Path(os.getenv("KPSS_DATA_DIR") or (BASE_DIR / "data"))
DB_PATH = Path(os.getenv("KPSS_DB_PATH") or (DATA_DIR / "kpss_radar.db"))
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

_DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
_cors_env = os.getenv("KPSS_CORS_ORIGINS", "").strip()
CORS_ORIGINS: list[str] = (
    [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
    if _cors_env
    else _DEFAULT_CORS_ORIGINS
)

DEFAULT_SCAN_INTERVAL_MINUTES: int = 60
MIN_SCAN_INTERVAL_MINUTES: int = 10
MAX_SCAN_INTERVAL_MINUTES: int = 1440

DEADLINE_SOON_DAYS: int = 5
NEW_ANNOUNCEMENT_HOURS: int = 48

DEFAULT_PREFERRED_CATEGORIES: list[str] = [
    "memur",
    "sozlesmeli_4b",
    "merkezi_atama",
    "kpss_a",
    "isci",
    "akademik",
    "sydv",
]

DEFAULT_PROFILE_DICT: dict = {
    "is_configured": False,
    "full_name": "Aday",
    "kpss_year": 2026,
    "education_level": "lisans",
    "scores": {
        "P3": None,
        "P93": None,
        "P94": None,
        "P1": None,
        "P2": None,
        "P10": None,
        "P121": None,
        "EKPSS": None,
        "YDS": None,
    },
    "departments": [],
    "qualification_codes": [],
    "birth_year": None,
    "gender": "belirtmek_istemiyorum",
    "military_status": "muaf_veya_yapildi",
    "driver_licenses": [],
    "certificates": [],
    "preferred_cities": [],
    "all_cities": True,
    "preferred_categories": list(DEFAULT_PREFERRED_CATEGORIES),
    "include_no_kpss": True,
    "scan_interval_minutes": DEFAULT_SCAN_INTERVAL_MINUTES,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "webhook_url": "",
}

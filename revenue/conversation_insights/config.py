from __future__ import annotations
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_MB = int(os.getenv("CONV_MAX_UPLOAD_MB", "500"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_CHAT_TEXT_MB = int(os.getenv("CONV_MAX_CHAT_TEXT_MB", "100"))
MAX_CHAT_TEXT_BYTES = MAX_CHAT_TEXT_MB * 1024 * 1024
MAX_MESSAGES = int(os.getenv("CONV_MAX_MESSAGES", "1000000"))
SESSION_TTL_MINUTES = int(os.getenv("CONV_SESSION_TTL_MINUTES", "45"))
DB_PATH = Path(os.getenv("CONV_REPORT_DB", str(DATA_DIR / "reports.sqlite3")))

SUPPORTED_RELATIONSHIPS = [
    {"id":"dating","label_en":"Dating / relationship","label_he":"זוגיות / דייטינג"},
    {"id":"ex","label_en":"Ex","label_he":"אקס / אקסית"},
    {"id":"friends","label_en":"Friends","label_he":"חברים"},
    {"id":"family","label_en":"Family","label_he":"משפחה"},
    {"id":"work","label_en":"Work","label_he":"עבודה"},
    {"id":"other","label_en":"Other","label_he":"אחר"},
]
REPORT_LANGUAGES = [
    {"id":"auto","label_he":"אוטומטי","label_en":"Auto"},
    {"id":"he","label_he":"עברית","label_en":"Hebrew"},
    {"id":"en","label_he":"אנגלית","label_en":"English"},
]

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "legacies-realty-change-me-in-production-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'legacies.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Legacies2026!")

    # Public base URL used inside QR codes
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000")

    # WhatsApp business number (digits only, with country code) e.g. 265991234567
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "265999000000")

    QR_FOLDER = BASE_DIR / "app" / "static" / "qrcodes"
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "plots"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

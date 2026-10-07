import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "legacies-realty-change-me-in-production-2026")

    # Prefer Postgres on Render (DATABASE_URL). Local default = SQLite in instance/
    _db = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'instance' / 'legacies.db'}"
    if _db.startswith("postgres://"):
        _db = _db.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep DB connections alive on hosted Postgres
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Legacies2026!")

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "265991134404")

    # Cloudinary URL required on Render so plot photos survive redeploys
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")

    QR_FOLDER = BASE_DIR / "app" / "static" / "qrcodes"
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "plots"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

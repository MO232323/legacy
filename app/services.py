"""Business logic: reference numbers, QR codes, uploads, WhatsApp."""
from datetime import datetime
from pathlib import Path
import uuid
import re
import os

import segno
from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import Agreement


CITY_CODES = {
    "Blantyre": "BLY",
    "Lilongwe": "LLW",
    "Mzuzu": "MZZ",
    "Mangochi": "MGC",
}


def generate_reference(city: str, sequence: int) -> str:
    year = datetime.now().year
    code = CITY_CODES.get(city, city[:3].upper())
    return f"LR-{year}-{code}-{sequence:04d}"


def create_qr_for_agreement(agreement: Agreement) -> str:
    base = current_app.config["PUBLIC_BASE_URL"].rstrip("/")
    url = f"{base}/verify?ref={agreement.reference}"

    qr_dir: Path = Path(current_app.config["QR_FOLDER"])
    qr_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{agreement.reference}.png"
    filepath = qr_dir / filename

    qr = segno.make(url, error="m")
    qr.save(
        str(filepath),
        kind="png",
        scale=8,
        border=2,
        dark="#0a1628",
        light="white",
    )

    agreement.qr_filename = f"qrcodes/{filename}"
    db.session.add(agreement)
    return agreement.qr_filename


def format_price(mwk):
    if mwk is None:
        return "On request"
    return f"MK {mwk:,}"


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = current_app.config.get("ALLOWED_EXTENSIONS") or {"png", "jpg", "jpeg", "webp", "gif"}
    return ext in allowed


def save_plot_image(file_storage):
    """
    Save uploaded image to static/uploads/plots/.
    Returns relative path under static/ (e.g. uploads/plots/abc123.jpg) or None.
    """
    if file_storage is None:
        return None
    # Werkzeug may give empty FileStorage when no file chosen
    filename = getattr(file_storage, "filename", None) or ""
    if not filename.strip():
        return None
    if not allowed_file(filename):
        return None

    original = secure_filename(filename)
    # If secure_filename stripped everything (odd names), keep extension only
    if not original or "." not in original:
        ext = filename.rsplit(".", 1)[-1].lower()
        original = f"image.{ext}"

    ext = original.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex[:16]}.{ext}"

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / name

    try:
        file_storage.save(str(dest))
    except Exception as e:
        current_app.logger.error("Image save failed: %s", e)
        return None

    if not dest.is_file() or dest.stat().st_size == 0:
        current_app.logger.error("Image file missing or empty after save: %s", dest)
        return None

    return f"uploads/plots/{name}"


def whatsapp_link(plot_code: str = "", title: str = "", city: str = "") -> str:
    number = re.sub(r"\D", "", str(current_app.config.get("WHATSAPP_NUMBER", "265999000000")))
    if plot_code:
        text = (
            f"Hello Legacies Realty, I'm interested in plot {plot_code}"
            f" ({title}, {city}). Please share more details."
        )
    else:
        text = "Hello Legacies Realty, I'd like to enquire about available plots."
    from urllib.parse import quote
    return f"https://wa.me/{number}?text={quote(text)}"

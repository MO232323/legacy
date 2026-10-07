"""Business logic: reference numbers, QR codes, uploads, WhatsApp."""
from datetime import datetime
from pathlib import Path
import uuid
import re
import io
import base64

import segno
from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import Certificate


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


def _verify_url(reference: str) -> str:
    base = current_app.config["PUBLIC_BASE_URL"].rstrip("/")
    return f"{base}/verify?ref={reference}"


def create_qr_for_certificate(certificate: Certificate) -> str:
    """Generate QR PNG on disk and keep path on the certificate."""
    url = _verify_url(certificate.reference)
    qr_dir = Path(current_app.config["QR_FOLDER"])
    qr_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{certificate.reference}.png"
    filepath = qr_dir / filename

    qr = segno.make(url, error="m")
    qr.save(str(filepath), kind="png", scale=8, border=2, dark="#0a1628", light="white")

    certificate.qr_filename = f"qrcodes/{filename}"
    db.session.add(certificate)
    return certificate.qr_filename


# Backward-compatible alias
create_qr_for_agreement = create_qr_for_certificate


def qr_data_uri(reference: str) -> str:
    """Build QR as data URI so certificates work even if disk files were wiped."""
    url = _verify_url(reference)
    qr = segno.make(url, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=8, border=2, dark="#0a1628", light="white")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def format_price(mwk, price_is_from=False):
    if mwk is None:
        return "On request"
    label = f"MK {mwk:,}"
    if price_is_from:
        return f"From {label}"
    return label


def format_plot_price(plot):
    """Format price for a Plot object (supports starting-from prices)."""
    is_from = bool(getattr(plot, "price_is_from", False))
    return format_price(plot.price_mwk, price_is_from=is_from)


def format_site_price(site):
    """Site listing price: fixed amount, 'Varies', or derived from plots."""
    if getattr(site, "price_fixed", False) and site.price_mwk is not None:
        return format_price(site.price_mwk)
    prices = [p.price_mwk for p in site.plots if p.price_mwk is not None]
    if not prices:
        if site.price_mwk is not None:
            return format_price(site.price_mwk)
        return "On request"
    if len(set(prices)) > 1:
        return "Varies"
    return format_price(prices[0])


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = current_app.config.get("ALLOWED_EXTENSIONS") or {"png", "jpg", "jpeg", "webp", "gif"}
    return ext in allowed


def media_url(path_or_url):
    if not path_or_url:
        return None
    s = str(path_or_url)
    if s.startswith("http://") or s.startswith("https://") or s.startswith("data:"):
        return s
    from flask import url_for
    return url_for("static", filename=s)


def save_plot_image(file_storage):
    if file_storage is None:
        return None
    filename = (getattr(file_storage, "filename", None) or "").strip()
    if not filename or not allowed_file(filename):
        return None

    cloudinary_url = (current_app.config.get("CLOUDINARY_URL") or "").strip()
    if cloudinary_url:
        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(cloudinary_url=cloudinary_url)
            result = cloudinary.uploader.upload(
                file_storage, folder="legacies-realty/plots", resource_type="image"
            )
            return result.get("secure_url") or result.get("url")
        except Exception as exc:
            current_app.logger.exception("Cloudinary upload failed: %s", exc)
            return None

    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "jpeg":
        ext = "jpg"
    name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / name
    try:
        file_storage.save(str(dest))
    except Exception as exc:
        current_app.logger.exception("Local upload failed: %s", exc)
        return None
    if not dest.is_file() or dest.stat().st_size == 0:
        return None
    return f"uploads/plots/{name}"


def whatsapp_link(plot_code: str = "", title: str = "", city: str = "") -> str:
    number = re.sub(r"\D", "", str(current_app.config.get("WHATSAPP_NUMBER", "265991134404")))
    if plot_code:
        text = (
            f"Hello Legacies Realty, I'm interested in plot {plot_code}"
            f" ({title}, {city}). Please share more details."
        )
    else:
        text = "Hello Legacies Realty, I'd like to enquire about available plots."
    from urllib.parse import quote
    return f"https://wa.me/{number}?text={quote(text)}"

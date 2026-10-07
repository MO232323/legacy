from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config, BASE_DIR

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    from pathlib import Path as _Path
    upload_dir = _Path(app.root_path) / "static" / "uploads" / "plots"
    qr_dir = _Path(app.root_path) / "static" / "qrcodes"
    upload_dir.mkdir(parents=True, exist_ok=True)
    qr_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_dir)
    app.config["QR_FOLDER"] = str(qr_dir)
    (BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes_public import public_bp
    from app.routes_admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_globals():
        from app.services import whatsapp_link, media_url, format_plot_price, format_price, format_site_price
        return {
            "whatsapp_link": whatsapp_link,
            "media_url": media_url,
            "format_plot_price": format_plot_price,
            "format_price": format_price,
            "format_site_price": format_site_price,
            "company_name": "Legacies Realty",
        }

    with app.app_context():
        db.create_all()
        _ensure_site_price_columns()
        _seed_if_empty()

    return app


def _ensure_site_price_columns():
    """Add site price columns on existing DBs."""
    from sqlalchemy import text, inspect
    eng = db.engine
    insp = inspect(eng)
    if "sites" not in set(insp.get_table_names()):
        return
    existing = {c["name"] for c in insp.get_columns("sites")}
    alters = []
    if "price_fixed" not in existing:
        alters.append("ALTER TABLE sites ADD COLUMN price_fixed BOOLEAN DEFAULT 0")
    if "price_mwk" not in existing:
        alters.append("ALTER TABLE sites ADD COLUMN price_mwk INTEGER")
    if not alters:
        return
    with eng.begin() as conn:
        for sql in alters:
            try:
                conn.execute(text(sql))
            except Exception:
                pass


def _seed_if_empty():
    from app.models import Admin, Site, Plot, Certificate
    from datetime import date
    from app.services import generate_reference, create_qr_for_certificate
    from config import Config

    if not Admin.query.first():
        admin = Admin(username=Config.ADMIN_USERNAME)
        admin.set_password(Config.ADMIN_PASSWORD)
        db.session.add(admin)

    if Site.query.count() == 0:
        # Site 1 — Blantyre
        s1 = Site(
            name="Sector 3 Residential Estate",
            site_code="BLY-SEC3",
            city="Blantyre",
            coordinates="15.78°S, 35.01°E",
            location_note="About 700 metres from M1 road",
            description="Quiet residential estate with road access and clear boundaries. Ideal for family homes.",
        )
        db.session.add(s1)
        db.session.flush()
        plots_s1 = [
            Plot(site_id=s1.id, plot_code="BLY-SEC3-042", size_sqm=450, plot_type="Residential", price_mwk=4_200_000, status="Sold"),
            Plot(site_id=s1.id, plot_code="BLY-SEC3-043", size_sqm=400, plot_type="Residential", price_mwk=3_900_000, status="Available"),
            Plot(site_id=s1.id, plot_code="BLY-SEC3-044", size_sqm=500, plot_type="Residential", price_mwk=4_500_000, status="Available"),
        ]
        db.session.add_all(plots_s1)

        # Site 2 — Lilongwe
        s2 = Site(
            name="Area 49 Investment Block",
            site_code="LLW-AREA49",
            city="Lilongwe",
            coordinates="13.98°S, 33.77°E",
            description="Prime growth corridor plots ideal for family home or investment.",
        )
        db.session.add(s2)
        db.session.flush()
        plots_s2 = [
            Plot(site_id=s2.id, plot_code="LLW-AREA49-018", size_sqm=600, plot_type="Residential / Investment", price_mwk=5_800_000, status="Sold"),
            Plot(site_id=s2.id, plot_code="LLW-AREA49-019", size_sqm=700, plot_type="Investment", price_mwk=8_000_000, status="Available"),
        ]
        db.session.add_all(plots_s2)

        # Site 3 — Mzuzu
        s3 = Site(
            name="Northern Extension",
            site_code="MZZ-NORTH",
            city="Mzuzu",
            coordinates="11.46°S, 34.02°E",
            description="Affordable entry into Mzuzu's expanding northern suburbs.",
        )
        db.session.add(s3)
        db.session.flush()
        plots_s3 = [
            Plot(site_id=s3.id, plot_code="MZZ-NORTH-007", size_sqm=500, plot_type="Residential", price_mwk=2_900_000, status="Sold"),
            Plot(site_id=s3.id, plot_code="MZZ-NORTH-008", size_sqm=480, plot_type="Residential", price_mwk=3_100_000, status="Available"),
        ]
        db.session.add_all(plots_s3)

        # Site 4 — Mangochi
        s4 = Site(
            name="Lakeside Parcels",
            site_code="MGC-LAKE",
            city="Mangochi",
            coordinates="14.47°S, 35.26°E",
            description="Spacious lakeside land — ideal for holiday home or lodge.",
        )
        db.session.add(s4)
        db.session.flush()
        plots_s4 = [
            Plot(site_id=s4.id, plot_code="MGC-LAKE-005", size_sqm=900, plot_type="Residential", price_mwk=6_500_000, status="Available"),
            Plot(site_id=s4.id, plot_code="MGC-LAKE-006", size_sqm=850, plot_type="Residential", price_mwk=6_200_000, status="Available"),
        ]
        db.session.add_all(plots_s4)

        db.session.flush()

        sold = [
            ("Grace Banda", "0999 111 222", "grace@example.com", "BLY-SEC3-042", date(2026, 8, 12)),
            ("James Phiri", "0888 333 444", "james@example.com", "LLW-AREA49-018", date(2026, 9, 3)),
            ("Tendai Mwale", "0991 555 666", None, "MZZ-NORTH-007", date(2026, 7, 21)),
        ]
        for name, phone, email, code, adate in sold:
            plot = Plot.query.filter_by(plot_code=code).first()
            if not plot:
                continue
            ref = generate_reference(plot.site.city, plot.id)
            cert = Certificate(
                reference=ref,
                buyer_name=name,
                buyer_phone=phone,
                buyer_email=email,
                plot_id=plot.id,
                status="Certificate issued",
                certificate_date=adate,
            )
            db.session.add(cert)
            db.session.flush()
            create_qr_for_certificate(cert)

    db.session.commit()

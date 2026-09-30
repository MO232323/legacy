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
    # Ensure upload limits apply
    app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)

    app.config["QR_FOLDER"].mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes_public import public_bp
    from app.routes_admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_globals():
        from app.services import whatsapp_link
        return {
            "whatsapp_link": whatsapp_link,
            "company_name": "Legacies Realty",
        }

    with app.app_context():
        db.create_all()
        _seed_if_empty()

    return app


def _seed_if_empty():
    from app.models import Admin, Plot, Agreement
    from datetime import date
    from app.services import generate_reference, create_qr_for_agreement
    from config import Config

    if not Admin.query.first():
        admin = Admin(username=Config.ADMIN_USERNAME)
        admin.set_password(Config.ADMIN_PASSWORD)
        db.session.add(admin)

    if Plot.query.count() == 0:
        samples = [
            Plot(
                plot_code="BLY-SEC3-042",
                city="Blantyre",
                title="Sector 3 Residential Plot",
                size_sqm=450,
                plot_type="Residential",
                price_mwk=4_200_000,
                status="Sold",
                coordinates="15.78°S, 35.01°E",
                description="Quiet residential plot with road access and clear boundaries.",
            ),
            Plot(
                plot_code="LLW-AREA49-018",
                city="Lilongwe",
                title="Area 49 Investment Block",
                size_sqm=600,
                plot_type="Residential / Investment",
                price_mwk=5_800_000,
                status="Sold",
                coordinates="13.98°S, 33.77°E",
                description="Prime growth corridor plot ideal for family home or investment.",
            ),
            Plot(
                plot_code="MZZ-NORTH-007",
                city="Mzuzu",
                title="Northern Extension Plot",
                size_sqm=500,
                plot_type="Residential",
                price_mwk=2_900_000,
                status="Sold",
                coordinates="11.46°S, 34.02°E",
                description="Affordable entry into Mzuzu's expanding northern suburbs.",
            ),
            Plot(
                plot_code="BLY-SEC2-011",
                city="Blantyre",
                title="Sector 2 Corner Plot",
                size_sqm=400,
                plot_type="Residential",
                price_mwk=3_900_000,
                status="Available",
                coordinates="15.79°S, 35.00°E",
                description="Corner plot with excellent access roads.",
            ),
            Plot(
                plot_code="LLW-AREA25-033",
                city="Lilongwe",
                title="Area 25 Growth Corridor",
                size_sqm=700,
                plot_type="Investment",
                price_mwk=8_000_000,
                status="Available",
                description="Large investment plot in a high-demand corridor.",
            ),
            Plot(
                plot_code="MGC-LAKE-005",
                city="Mangochi",
                title="Lakeside Parcel",
                size_sqm=900,
                plot_type="Residential",
                price_mwk=6_500_000,
                status="Available",
                coordinates="14.47°S, 35.26°E",
                description="Spacious lakeside land — ideal for holiday home or lodge.",
            ),
            Plot(
                plot_code="MZZ-SOUTH-019",
                city="Mzuzu",
                title="South Extension Plot",
                size_sqm=480,
                plot_type="Residential",
                price_mwk=3_100_000,
                status="Available",
                description="Well-positioned residential plot with surveyed boundaries.",
            ),
            Plot(
                plot_code="BLY-COM-008",
                city="Blantyre",
                title="Commercial Corner",
                size_sqm=350,
                plot_type="Commercial",
                price_mwk=7_100_000,
                status="Available",
                description="High-visibility commercial corner in a busy corridor.",
            ),
        ]
        db.session.add_all(samples)
        db.session.flush()

        sold = [
            ("Grace Banda", "0999 111 222", "grace@example.com", "BLY-SEC3-042", date(2026, 8, 12)),
            ("James Phiri", "0888 333 444", "james@example.com", "LLW-AREA49-018", date(2026, 9, 3)),
            ("Tendai Mwale", "0991 555 666", None, "MZZ-NORTH-007", date(2026, 7, 21)),
        ]
        for name, phone, email, code, adate in sold:
            plot = Plot.query.filter_by(plot_code=code).first()
            ref = generate_reference(plot.city, plot.id)
            agr = Agreement(
                reference=ref,
                buyer_name=name,
                buyer_phone=phone,
                buyer_email=email,
                plot_id=plot.id,
                status="Agreement signed",
                agreement_date=adate,
            )
            db.session.add(agr)
            db.session.flush()
            create_qr_for_agreement(agr)

    db.session.commit()

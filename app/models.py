from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


class Site(db.Model):
    """A development / estate that contains many individual plots.

    Description, photos, layout plan and location live on the site.
    """
    __tablename__ = "sites"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # e.g. "Mpemba ESCOM Right Turn"
    site_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g. MPEMBA
    city = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    coordinates = db.Column(db.String(80))
    location_note = db.Column(db.String(200))  # e.g. "About 700m from M1 road"
    image1 = db.Column(db.String(500))
    image2 = db.Column(db.String(500))
    image3 = db.Column(db.String(500))
    site_plan = db.Column(db.String(500))  # layout / site plan image
    # Site-level pricing: if price_fixed, all plots share price_mwk
    price_fixed = db.Column(db.Boolean, default=False)
    price_mwk = db.Column(db.Integer, nullable=True)  # fixed price when price_fixed=True
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    plots = db.relationship("Plot", back_populates="site", cascade="all, delete-orphan", order_by="Plot.plot_code")

    def images(self):
        out = []
        for field in (self.image1, self.image2, self.image3):
            if field:
                out.append(field)
        return out

    def cover_image(self):
        imgs = self.images()
        return imgs[0] if imgs else None

    def available_count(self):
        return sum(1 for p in self.plots if p.status in ("Available", "Reserved"))

    def min_price(self):
        prices = [p.price_mwk for p in self.plots if p.price_mwk is not None]
        return min(prices) if prices else None

    def prices_vary(self):
        """True when plot prices are not all the same (and not marked fixed)."""
        if self.price_fixed:
            return False
        prices = [p.price_mwk for p in self.plots if p.price_mwk is not None]
        return len(set(prices)) > 1 if prices else False

    def __repr__(self):
        return f"<Site {self.site_code}>"


class Plot(db.Model):
    """Individual plot within a site. Certificate is issued per plot."""
    __tablename__ = "plots"
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False)
    plot_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g. MPEMBA-01
    size_sqm = db.Column(db.Integer, nullable=True)
    size_label = db.Column(db.String(120), nullable=True)
    plot_type = db.Column(db.String(50), default="Residential")
    price_mwk = db.Column(db.Integer)
    price_is_from = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default="Available")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    site = db.relationship("Site", back_populates="plots")
    certificate = db.relationship("Certificate", back_populates="plot", uselist=False)

    def display_size(self):
        if self.size_label:
            return self.size_label
        if self.size_sqm:
            return f"{self.size_sqm} m²"
        return "Size on request"

    @property
    def city(self):
        return self.site.city if self.site else ""

    @property
    def title(self):
        return self.site.name if self.site else self.plot_code

    def __repr__(self):
        return f"<Plot {self.plot_code}>"


class Certificate(db.Model):
    """Land Purchase Certificate — one per sold plot."""
    __tablename__ = "certificates"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    buyer_name = db.Column(db.String(120), nullable=False)
    buyer_phone = db.Column(db.String(30))
    buyer_email = db.Column(db.String(120))
    plot_id = db.Column(db.Integer, db.ForeignKey("plots.id"), unique=True, nullable=False)
    status = db.Column(db.String(50), default="Certificate issued")
    certificate_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    qr_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    plot = db.relationship("Plot", back_populates="certificate")

    def __repr__(self):
        return f"<Certificate {self.reference}>"


class ViewingRequest(db.Model):
    __tablename__ = "viewing_requests"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120))
    city = db.Column(db.String(50))
    message = db.Column(db.Text)
    status = db.Column(db.String(30), default="New")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

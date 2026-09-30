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


class Plot(db.Model):
    __tablename__ = "plots"
    id = db.Column(db.Integer, primary_key=True)
    plot_code = db.Column(db.String(50), unique=True, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    size_sqm = db.Column(db.Integer, nullable=False)
    plot_type = db.Column(db.String(50), default="Residential")
    price_mwk = db.Column(db.Integer)
    status = db.Column(db.String(30), default="Available")
    description = db.Column(db.Text)
    coordinates = db.Column(db.String(80))
    image1 = db.Column(db.String(200))
    image2 = db.Column(db.String(200))
    image3 = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    agreement = db.relationship("Agreement", back_populates="plot", uselist=False)

    def images(self):
        out = []
        for field in (self.image1, self.image2, self.image3):
            if field:
                out.append(field)
        return out

    def cover_image(self):
        imgs = self.images()
        return imgs[0] if imgs else None

    def __repr__(self):
        return f"<Plot {self.plot_code}>"


class Agreement(db.Model):
    __tablename__ = "agreements"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    buyer_name = db.Column(db.String(120), nullable=False)
    buyer_phone = db.Column(db.String(30))
    buyer_email = db.Column(db.String(120))
    plot_id = db.Column(db.Integer, db.ForeignKey("plots.id"), unique=True, nullable=False)
    status = db.Column(db.String(50), default="Agreement signed")
    agreement_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    qr_filename = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    plot = db.relationship("Plot", back_populates="agreement")

    def __repr__(self):
        return f"<Agreement {self.reference}>"


class ViewingRequest(db.Model):
    __tablename__ = "viewing_requests"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(30), default="New")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

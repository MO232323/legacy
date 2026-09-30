from datetime import date
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Admin, Plot, Agreement, ViewingRequest
from app.services import (
    generate_reference,
    create_qr_for_agreement,
    format_price,
    save_plot_image,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    stats = {
        "plots": Plot.query.count(),
        "available": Plot.query.filter_by(status="Available").count(),
        "sold": Plot.query.filter_by(status="Sold").count(),
        "agreements": Agreement.query.count(),
        "leads": ViewingRequest.query.filter_by(status="New").count(),
    }
    recent_agreements = Agreement.query.order_by(Agreement.created_at.desc()).limit(5).all()
    recent_leads = ViewingRequest.query.order_by(ViewingRequest.created_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_agreements=recent_agreements,
        recent_leads=recent_leads,
    )


@admin_bp.route("/plots")
@login_required
def plots():
    plots = Plot.query.order_by(Plot.city, Plot.plot_code).all()
    return render_template("admin/plots.html", plots=plots, format_price=format_price)


def _apply_images(plot, form_files):
    """Attach up to 3 uploaded images to plot fields. Returns count saved."""
    saved = 0
    for i, key in enumerate(("image1", "image2", "image3"), start=1):
        f = form_files.get(key)
        if f is None:
            continue
        path = save_plot_image(f)
        if path:
            setattr(plot, f"image{i}", path)
            saved += 1
    return saved


@admin_bp.route("/plots/new", methods=["GET", "POST"])
@login_required
def plot_new():
    if request.method == "POST":
        plot = Plot(
            plot_code=request.form["plot_code"].strip().upper(),
            city=request.form["city"].strip(),
            title=request.form["title"].strip(),
            size_sqm=int(request.form["size_sqm"]),
            plot_type=request.form.get("plot_type", "Residential").strip(),
            price_mwk=int(request.form["price_mwk"]) if request.form.get("price_mwk") else None,
            status=request.form.get("status", "Available"),
            description=request.form.get("description") or None,
            coordinates=request.form.get("coordinates") or None,
        )
        if Plot.query.filter_by(plot_code=plot.plot_code).first():
            flash(f"Plot code {plot.plot_code} already exists.", "error")
            return render_template("admin/plot_form.html", plot=None)
        n = _apply_images(plot, request.files)
        db.session.add(plot)
        db.session.commit()
        if n:
            flash(f"Plot created with {n} photo(s).", "success")
        else:
            flash("Plot created. No photos uploaded — you can add them by editing the plot.", "warning")
        return redirect(url_for("admin.plots"))
    return render_template("admin/plot_form.html", plot=None)


@admin_bp.route("/plots/<int:plot_id>/edit", methods=["GET", "POST"])
@login_required
def plot_edit(plot_id):
    plot = db.session.get(Plot, plot_id) or abort(404)
    if request.method == "POST":
        plot.plot_code = request.form["plot_code"].strip().upper()
        plot.city = request.form["city"].strip()
        plot.title = request.form["title"].strip()
        plot.size_sqm = int(request.form["size_sqm"])
        plot.plot_type = request.form.get("plot_type", "Residential").strip()
        plot.price_mwk = int(request.form["price_mwk"]) if request.form.get("price_mwk") else None
        plot.status = request.form.get("status", "Available")
        plot.description = request.form.get("description") or None
        plot.coordinates = request.form.get("coordinates") or None
        n = _apply_images(plot, request.files)
        db.session.commit()
        if n:
            flash(f"Plot updated. {n} new photo(s) saved.", "success")
        else:
            flash("Plot updated.", "success")
        return redirect(url_for("admin.plots"))
    return render_template("admin/plot_form.html", plot=plot)


@admin_bp.route("/plots/<int:plot_id>/delete", methods=["POST"])
@login_required
def plot_delete(plot_id):
    plot = db.session.get(Plot, plot_id) or abort(404)
    if plot.agreement:
        flash("Cannot delete a plot that has a sale agreement. Delete the agreement first.", "error")
        return redirect(url_for("admin.plots"))
    db.session.delete(plot)
    db.session.commit()
    flash("Plot deleted.", "success")
    return redirect(url_for("admin.plots"))


@admin_bp.route("/agreements")
@login_required
def agreements():
    items = Agreement.query.order_by(Agreement.created_at.desc()).all()
    return render_template("admin/agreements.html", agreements=items)


@admin_bp.route("/agreements/new", methods=["GET", "POST"])
@login_required
def agreement_new():
    available_plots = (
        Plot.query.filter(Plot.status.in_(["Available", "Reserved"]))
        .order_by(Plot.city, Plot.plot_code)
        .all()
    )
    if request.method == "POST":
        plot_id = int(request.form["plot_id"])
        plot = db.session.get(Plot, plot_id)
        if not plot:
            flash("Plot not found.", "error")
            return redirect(url_for("admin.agreement_new"))
        if plot.agreement:
            flash("This plot already has an agreement.", "error")
            return redirect(url_for("admin.agreement_new"))

        ref = generate_reference(plot.city, plot.id)
        while Agreement.query.filter_by(reference=ref).first():
            ref = generate_reference(plot.city, plot.id + 1000)

        agr_date_str = request.form.get("agreement_date") or date.today().isoformat()
        agr = Agreement(
            reference=ref,
            buyer_name=request.form["buyer_name"].strip(),
            buyer_phone=request.form.get("buyer_phone", "").strip() or None,
            buyer_email=request.form.get("buyer_email", "").strip() or None,
            plot_id=plot.id,
            status=request.form.get("status", "Agreement signed"),
            agreement_date=date.fromisoformat(agr_date_str),
            notes=request.form.get("notes") or None,
        )
        db.session.add(agr)
        plot.status = "Sold"
        db.session.flush()
        create_qr_for_agreement(agr)
        db.session.commit()
        flash(f"Agreement {ref} created. QR code generated.", "success")
        return redirect(url_for("admin.agreement_detail", agr_id=agr.id))

    return render_template(
        "admin/agreement_form.html",
        available_plots=available_plots,
        today=date.today().isoformat(),
    )


@admin_bp.route("/agreements/<int:agr_id>")
@login_required
def agreement_detail(agr_id):
    agr = db.session.get(Agreement, agr_id) or abort(404)
    return render_template("admin/agreement_detail.html", agreement=agr)


@admin_bp.route("/agreements/<int:agr_id>/delete", methods=["POST"])
@login_required
def agreement_delete(agr_id):
    agr = db.session.get(Agreement, agr_id) or abort(404)
    plot = agr.plot
    if plot:
        plot.status = "Available"
    db.session.delete(agr)
    db.session.commit()
    flash("Agreement deleted. Plot marked Available.", "success")
    return redirect(url_for("admin.agreements"))


@admin_bp.route("/leads")
@login_required
def leads():
    items = ViewingRequest.query.order_by(ViewingRequest.created_at.desc()).all()
    return render_template("admin/leads.html", leads=items)


@admin_bp.route("/leads/<int:lead_id>/status", methods=["POST"])
@login_required
def lead_status(lead_id):
    lead = db.session.get(ViewingRequest, lead_id) or abort(404)
    lead.status = request.form.get("status", lead.status)
    db.session.commit()
    flash("Lead updated.", "success")
    return redirect(url_for("admin.leads"))

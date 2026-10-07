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
from app.models import Admin, Site, Plot, Certificate, ViewingRequest
from app.services import (
    generate_reference,
    create_qr_for_certificate,
    format_price,
    format_plot_price,
    format_site_price,
    save_plot_image,
    qr_data_uri,
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
        "sites": Site.query.count(),
        "plots": Plot.query.count(),
        "available": Plot.query.filter_by(status="Available").count(),
        "sold": Plot.query.filter_by(status="Sold").count(),
        "certificates": Certificate.query.count(),
        "leads": ViewingRequest.query.filter_by(status="New").count(),
    }
    recent_certificates = Certificate.query.order_by(Certificate.created_at.desc()).limit(5).all()
    recent_leads = ViewingRequest.query.order_by(ViewingRequest.created_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_certificates=recent_certificates,
        recent_leads=recent_leads,
    )


# ── Sites ──────────────────────────────────────────────────────────────────


@admin_bp.route("/sites")
@login_required
def sites():
    sites = Site.query.order_by(Site.city, Site.name).all()
    return render_template(
        "admin/sites.html",
        sites=sites,
        format_price=format_price,
        format_site_price=format_site_price,
    )


def _parse_optional_int(val):
    val = (val or "").strip().replace(",", "")
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _apply_site_images(site, form_files):
    """Save up to 3 gallery images + optional site plan."""
    saved = 0
    for i, key in enumerate(("image1", "image2", "image3"), start=1):
        f = form_files.get(key)
        if f is None or not getattr(f, "filename", None):
            continue
        path = save_plot_image(f)
        if path:
            setattr(site, f"image{i}", path)
            saved += 1
        else:
            flash(f"Could not save photo: {f.filename} (use JPG/PNG/WEBP under 16MB)", "error")
    sp = form_files.get("site_plan")
    if sp is not None and getattr(sp, "filename", None):
        path = save_plot_image(sp)
        if path:
            site.site_plan = path
        else:
            flash(f"Could not save site plan: {sp.filename}", "error")
    return saved


def _apply_site_fields(site, form):
    site.name = form["name"].strip()
    site.site_code = form["site_code"].strip().upper()
    site.city = form["city"].strip()
    site.description = form.get("description") or None
    site.coordinates = form.get("coordinates") or None
    site.location_note = (form.get("location_note") or "").strip() or None
    site.price_fixed = form.get("price_fixed") == "1"
    site.price_mwk = _parse_optional_int(form.get("price_mwk"))


@admin_bp.route("/sites/new", methods=["GET", "POST"])
@login_required
def site_new():
    if request.method == "POST":
        site = Site()
        _apply_site_fields(site, request.form)
        if Site.query.filter_by(site_code=site.site_code).first():
            flash(f"Site code {site.site_code} already exists.", "error")
            return render_template("admin/site_form.html", site=None)

        num_plots = _parse_optional_int(request.form.get("num_plots")) or 0
        if num_plots < 1:
            flash("Please enter at least 1 plot.", "error")
            return render_template("admin/site_form.html", site=None)

        _apply_site_images(site, request.files)
        db.session.add(site)
        db.session.flush()  # get site.id

        # Create individual plots from form rows
        fixed_price = site.price_mwk if site.price_fixed else None
        created = 0
        for i in range(1, num_plots + 1):
            code = (request.form.get(f"plot_code_{i}") or "").strip().upper()
            if not code:
                code = f"{site.site_code}-{i:02d}"
            if Plot.query.filter_by(plot_code=code).first():
                flash(f"Plot code {code} already exists — skipped.", "warning")
                continue
            # If site has a fixed price, use it for every plot; otherwise use per-plot input
            plot_price = fixed_price if fixed_price is not None else _parse_optional_int(request.form.get(f"price_mwk_{i}"))
            plot = Plot(
                site_id=site.id,
                plot_code=code,
                size_sqm=_parse_optional_int(request.form.get(f"size_sqm_{i}")),
                size_label=(request.form.get(f"size_label_{i}") or "").strip() or None,
                plot_type=(request.form.get(f"plot_type_{i}") or "Residential").strip(),
                price_mwk=plot_price,
                price_is_from=False if fixed_price is not None else (request.form.get(f"price_is_from_{i}") == "1"),
                status=(request.form.get(f"status_{i}") or "Available").strip(),
            )
            db.session.add(plot)
            created += 1

        db.session.commit()
        flash(f"Site “{site.name}” created with {created} plot(s).", "success")
        return redirect(url_for("admin.sites"))

    return render_template("admin/site_form.html", site=None)


@admin_bp.route("/sites/<int:site_id>/edit", methods=["GET", "POST"])
@login_required
def site_edit(site_id):
    site = db.session.get(Site, site_id) or abort(404)
    if request.method == "POST":
        _apply_site_fields(site, request.form)
        other = Site.query.filter(Site.site_code == site.site_code, Site.id != site.id).first()
        if other:
            flash(f"Site code {site.site_code} already used by another site.", "error")
            return render_template("admin/site_form.html", site=site)
        n = _apply_site_images(site, request.files)
        # Optionally apply fixed price to all existing plots
        if site.price_fixed and site.price_mwk is not None and request.form.get("apply_price_to_plots") == "1":
            for p in site.plots:
                p.price_mwk = site.price_mwk
                p.price_is_from = False
        db.session.commit()
        if n:
            flash(f"Site updated. {n} new photo(s) saved.", "success")
        else:
            flash("Site updated.", "success")
        return redirect(url_for("admin.sites"))
    return render_template("admin/site_form.html", site=site)


@admin_bp.route("/sites/<int:site_id>/delete", methods=["POST"])
@login_required
def site_delete(site_id):
    site = db.session.get(Site, site_id) or abort(404)
    for p in site.plots:
        if p.certificate:
            flash("Cannot delete a site that has plots with certificates. Delete certificates first.", "error")
            return redirect(url_for("admin.sites"))
    db.session.delete(site)
    db.session.commit()
    flash("Site and its plots deleted.", "success")
    return redirect(url_for("admin.sites"))


@admin_bp.route("/sites/<int:site_id>/plots")
@login_required
def site_plots(site_id):
    site = db.session.get(Site, site_id) or abort(404)
    return render_template(
        "admin/site_plots.html",
        site=site,
        format_price=format_price,
        format_plot_price=format_plot_price,
    )


@admin_bp.route("/sites/<int:site_id>/plots/new", methods=["GET", "POST"])
@login_required
def plot_new_for_site(site_id):
    site = db.session.get(Site, site_id) or abort(404)
    if request.method == "POST":
        code = request.form["plot_code"].strip().upper()
        if Plot.query.filter_by(plot_code=code).first():
            flash(f"Plot code {code} already exists.", "error")
            return render_template("admin/plot_form.html", site=site, plot=None)
        plot = Plot(
            site_id=site.id,
            plot_code=code,
            size_sqm=_parse_optional_int(request.form.get("size_sqm")),
            size_label=(request.form.get("size_label") or "").strip() or None,
            plot_type=request.form.get("plot_type", "Residential").strip(),
            price_mwk=_parse_optional_int(request.form.get("price_mwk")),
            price_is_from=request.form.get("price_is_from") == "1",
            status=request.form.get("status", "Available"),
        )
        db.session.add(plot)
        db.session.commit()
        flash(f"Plot {code} added to {site.name}.", "success")
        return redirect(url_for("admin.site_plots", site_id=site.id))
    return render_template("admin/plot_form.html", site=site, plot=None)


@admin_bp.route("/plots/<int:plot_id>/edit", methods=["GET", "POST"])
@login_required
def plot_edit(plot_id):
    plot = db.session.get(Plot, plot_id) or abort(404)
    site = plot.site
    if request.method == "POST":
        code = request.form["plot_code"].strip().upper()
        other = Plot.query.filter(Plot.plot_code == code, Plot.id != plot.id).first()
        if other:
            flash(f"Plot code {code} already exists.", "error")
            return render_template("admin/plot_form.html", site=site, plot=plot)
        plot.plot_code = code
        plot.size_sqm = _parse_optional_int(request.form.get("size_sqm"))
        plot.size_label = (request.form.get("size_label") or "").strip() or None
        plot.plot_type = request.form.get("plot_type", "Residential").strip()
        plot.price_mwk = _parse_optional_int(request.form.get("price_mwk"))
        plot.price_is_from = request.form.get("price_is_from") == "1"
        plot.status = request.form.get("status", "Available")
        db.session.commit()
        flash("Plot updated.", "success")
        return redirect(url_for("admin.site_plots", site_id=site.id))
    return render_template("admin/plot_form.html", site=site, plot=plot)


@admin_bp.route("/plots/<int:plot_id>/delete", methods=["POST"])
@login_required
def plot_delete(plot_id):
    plot = db.session.get(Plot, plot_id) or abort(404)
    site_id = plot.site_id
    if plot.certificate:
        flash("Cannot delete a plot that has a certificate. Delete the certificate first.", "error")
        return redirect(url_for("admin.site_plots", site_id=site_id))
    db.session.delete(plot)
    db.session.commit()
    flash("Plot deleted.", "success")
    return redirect(url_for("admin.site_plots", site_id=site_id))


# ── Certificates (Land Purchase Certificates) ───────────────────────────────


@admin_bp.route("/certificates")
@login_required
def certificates():
    items = Certificate.query.order_by(Certificate.created_at.desc()).all()
    return render_template("admin/certificates.html", certificates=items)


@admin_bp.route("/certificates/new", methods=["GET", "POST"])
@login_required
def certificate_new():
    available_plots = (
        Plot.query.filter(Plot.status.in_(["Available", "Reserved"]))
        .order_by(Plot.plot_code)
        .all()
    )
    if request.method == "POST":
        plot_id = int(request.form["plot_id"])
        plot = db.session.get(Plot, plot_id)
        if not plot:
            flash("Plot not found.", "error")
            return redirect(url_for("admin.certificate_new"))
        if plot.certificate:
            flash("This plot already has a certificate.", "error")
            return redirect(url_for("admin.certificate_new"))

        ref = generate_reference(plot.site.city, plot.id)
        while Certificate.query.filter_by(reference=ref).first():
            ref = generate_reference(plot.site.city, plot.id + 1000)

        cert_date_str = request.form.get("certificate_date") or date.today().isoformat()
        cert = Certificate(
            reference=ref,
            buyer_name=request.form["buyer_name"].strip(),
            buyer_phone=request.form.get("buyer_phone", "").strip() or None,
            buyer_email=request.form.get("buyer_email", "").strip() or None,
            plot_id=plot.id,
            status=request.form.get("status", "Certificate issued"),
            certificate_date=date.fromisoformat(cert_date_str),
            notes=request.form.get("notes") or None,
        )
        try:
            db.session.add(cert)
            plot.status = "Sold"
            db.session.flush()
            create_qr_for_certificate(cert)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save certificate: {exc}", "error")
            return redirect(url_for("admin.certificate_new"))
        flash(f"Land Purchase Certificate {ref} created. QR code generated.", "success")
        return redirect(url_for("admin.certificate_detail", cert_id=cert.id))

    return render_template(
        "admin/certificate_form.html",
        available_plots=available_plots,
        today=date.today().isoformat(),
    )


@admin_bp.route("/certificates/<int:cert_id>")
@login_required
def certificate_detail(cert_id):
    cert = db.session.get(Certificate, cert_id) or abort(404)
    return render_template(
        "admin/certificate_detail.html",
        certificate=cert,
        qr_src=qr_data_uri(cert.reference),
    )


@admin_bp.route("/certificates/<int:cert_id>/delete", methods=["POST"])
@login_required
def certificate_delete(cert_id):
    cert = db.session.get(Certificate, cert_id) or abort(404)
    plot = cert.plot
    if plot:
        plot.status = "Available"
    db.session.delete(cert)
    db.session.commit()
    flash("Certificate deleted. Plot marked Available.", "success")
    return redirect(url_for("admin.certificates"))


# ── Leads ───────────────────────────────────────────────────────────────────


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

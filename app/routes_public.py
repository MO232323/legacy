from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db
from app.models import Site, Plot, Certificate, ViewingRequest
from app.services import format_price, format_plot_price, format_site_price, whatsapp_link, qr_data_uri

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    sites = (
        Site.query.join(Plot)
        .filter(Plot.status.in_(["Available", "Reserved"]))
        .order_by(Site.city, Site.name)
        .distinct()
        .limit(6)
        .all()
    )
    return render_template(
        "index.html",
        sites=sites,
        format_price=format_price,
        format_plot_price=format_plot_price,
        format_site_price=format_site_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/sites")
def sites_list():
    city = request.args.get("city", "").strip()
    q = Site.query
    if city:
        q = q.filter_by(city=city)
    sites = q.order_by(Site.city, Site.name).all()
    cities = [r[0] for r in db.session.query(Site.city).distinct().order_by(Site.city)]
    return render_template(
        "sites.html",
        sites=sites,
        cities=cities,
        selected_city=city,
        format_price=format_price,
        format_site_price=format_site_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/sites/<int:site_id>")
def site_detail(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        flash("Site not found.", "error")
        return redirect(url_for("public.sites_list"))
    return render_template(
        "site_detail.html",
        site=site,
        format_price=format_price,
        format_plot_price=format_plot_price,
        format_site_price=format_site_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/plots/<int:plot_id>")
def plot_detail(plot_id):
    plot = db.session.get(Plot, plot_id)
    if not plot:
        flash("Plot not found.", "error")
        return redirect(url_for("public.sites_list"))
    return render_template(
        "plot_detail.html",
        plot=plot,
        site=plot.site,
        format_price=format_price,
        format_plot_price=format_plot_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/verify")
def verify():
    ref = request.args.get("ref", "").strip().upper()
    certificate = None
    error = None
    if ref:
        certificate = Certificate.query.filter_by(reference=ref).first()
        if not certificate:
            error = f"No record found for reference “{ref}”. Check the number on your certificate."
    return render_template("verify.html", certificate=certificate, ref=ref, error=error)


@public_bp.route("/api/verify/<ref>")
def api_verify(ref):
    cert = Certificate.query.filter_by(reference=ref.strip().upper()).first()
    if not cert:
        return jsonify({"ok": False, "error": "Not found"}), 404
    p = cert.plot
    s = p.site
    return jsonify(
        {
            "ok": True,
            "reference": cert.reference,
            "buyer_name": cert.buyer_name,
            "plot_code": p.plot_code,
            "site_name": s.name,
            "location": f"{s.city} — {s.name}",
            "size_sqm": p.size_sqm,
            "plot_type": p.plot_type,
            "status": cert.status,
            "certificate_date": cert.certificate_date.isoformat(),
            "coordinates": s.coordinates,
        }
    )


@public_bp.route("/certificate/<ref>")
def certificate_view(ref):
    cert = Certificate.query.filter_by(reference=ref.strip().upper()).first_or_404()
    return render_template(
        "certificate.html",
        certificate=cert,
        format_price=format_price,
        format_plot_price=format_plot_price,
        qr_src=qr_data_uri(cert.reference),
    )


@public_bp.route("/book", methods=["POST"])
def book_viewing():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    city = request.form.get("city", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not phone or not city:
        flash("Please fill in name, phone and preferred city.", "error")
        return redirect(url_for("public.home") + "#contact")
    email = (request.form.get("email") or "").strip() or None
    req = ViewingRequest(name=name, phone=phone, email=email, city=city, message=message or None)
    db.session.add(req)
    db.session.commit()
    flash("Thank you — we will contact you shortly to arrange a free viewing.", "success")
    return redirect(url_for("public.home") + "#contact")

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db
from app.models import Plot, Agreement, ViewingRequest
from app.services import format_price, whatsapp_link

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    available = (
        Plot.query.filter(Plot.status.in_(["Available", "Reserved"]))
        .order_by(Plot.city, Plot.plot_code)
        .limit(6)
        .all()
    )
    return render_template(
        "index.html",
        plots=available,
        format_price=format_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/plots")
def plots_list():
    city = request.args.get("city", "").strip()
    q = Plot.query.filter(Plot.status.in_(["Available", "Reserved", "Sold"]))
    if city:
        q = q.filter_by(city=city)
    plots = q.order_by(Plot.status, Plot.city, Plot.plot_code).all()
    cities = [r[0] for r in db.session.query(Plot.city).distinct().order_by(Plot.city)]
    return render_template(
        "plots.html",
        plots=plots,
        cities=cities,
        selected_city=city,
        format_price=format_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/plots/<int:plot_id>")
def plot_detail(plot_id):
    plot = db.session.get(Plot, plot_id)
    if not plot:
        flash("Plot not found.", "error")
        return redirect(url_for("public.plots_list"))
    return render_template(
        "plot_detail.html",
        plot=plot,
        format_price=format_price,
        whatsapp_link=whatsapp_link,
    )


@public_bp.route("/verify")
def verify():
    ref = request.args.get("ref", "").strip().upper()
    agreement = None
    error = None
    if ref:
        agreement = Agreement.query.filter_by(reference=ref).first()
        if not agreement:
            error = f"No record found for reference “{ref}”. Check the number on your agreement."
    return render_template("verify.html", agreement=agreement, ref=ref, error=error)


@public_bp.route("/api/verify/<ref>")
def api_verify(ref):
    agr = Agreement.query.filter_by(reference=ref.strip().upper()).first()
    if not agr:
        return jsonify({"ok": False, "error": "Not found"}), 404
    p = agr.plot
    return jsonify(
        {
            "ok": True,
            "reference": agr.reference,
            "buyer_name": agr.buyer_name,
            "plot_code": p.plot_code,
            "location": f"{p.city} — {p.title}",
            "size_sqm": p.size_sqm,
            "plot_type": p.plot_type,
            "status": agr.status,
            "agreement_date": agr.agreement_date.isoformat(),
            "coordinates": p.coordinates,
        }
    )


@public_bp.route("/agreement/<ref>")
def agreement_view(ref):
    agr = Agreement.query.filter_by(reference=ref.strip().upper()).first_or_404()
    return render_template("agreement.html", agreement=agr, format_price=format_price)


@public_bp.route("/book", methods=["POST"])
def book_viewing():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    city = request.form.get("city", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not phone or not city:
        flash("Please fill in name, phone and preferred city.", "error")
        return redirect(url_for("public.home") + "#contact")
    req = ViewingRequest(name=name, phone=phone, city=city, message=message or None)
    db.session.add(req)
    db.session.commit()
    flash("Thank you — we will contact you shortly to arrange a free viewing.", "success")
    return redirect(url_for("public.home") + "#contact")

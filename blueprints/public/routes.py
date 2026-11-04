"""
Public portfolio routes — homepage, project detail, contact, SEO endpoints.
"""
import json
import logging
import os
import re
from datetime import datetime, timezone
from flask import (
    render_template, request, jsonify, make_response,
    current_app, abort, url_for,
)
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError

from blueprints.public import public_bp
from extensions import db, mail, limiter
from models import Project, Skill, Education, Experience, Certification, Message, SiteSettings

logger = logging.getLogger(__name__)


def _get_settings():
    """Return the singleton SiteSettings row, creating defaults if absent."""
    s = SiteSettings.query.first()
    if not s:
        s = SiteSettings()
        db.session.add(s)
        db.session.commit()
    return s


def _parse_json_field(text, default):
    """Safely parse a JSON text field from the DB."""
    try:
        return json.loads(text) if text else default
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Homepage
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route("/")
def index():
    settings = _get_settings()
    projects = (
        Project.query.filter_by(published=True)
        .order_by(Project.featured.desc(), Project.display_order.asc(), Project.created_at.desc())
        .all()
    )
    skills = Skill.query.order_by(Skill.display_order.asc()).all()
    education = Education.query.order_by(Education.display_order.asc()).all()
    experience = Experience.query.order_by(Experience.display_order.asc()).all()
    certifications = Certification.query.order_by(Certification.display_order.asc()).all()

    # Parse JSON fields for skills
    for skill in skills:
        skill.tags_list = _parse_json_field(skill.tags, [])

    # Parse technologies in experience
    for exp in experience:
        exp.tech_list = _parse_json_field(exp.technologies, [])

    return render_template(
        "index.html",
        settings=settings,
        projects=projects,
        skills=skills,
        education=education,
        experience=experience,
        certifications=certifications,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Project Detail
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route("/projects/<slug>")
def project_detail(slug):
    # Validate slug to prevent injection
    if not re.match(r"^[a-z0-9\-]+$", slug):
        abort(404)

    project = Project.query.filter_by(slug=slug, published=True).first_or_404()
    settings = _get_settings()

    project.metrics_dict = _parse_json_field(project.metrics, {})
    project.tech_list = _parse_json_field(project.technologies, [])

    return render_template(
        "project_detail.html",
        project=project,
        settings=settings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Contact Form
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route("/contact", methods=["POST"])
@limiter.limit("5 per minute;20 per hour")
def contact():
    """
    Accept contact form submission.
    - CSRF validated
    - All fields validated server-side
    - Stored in DB (never in public JSON)
    - Email notification dispatched if SMTP configured
    """
    # ── CSRF check ────────────────────────────────────────────────────────────
    if current_app.config.get("WTF_CSRF_ENABLED", True):
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
        try:
            validate_csrf(token)
        except ValidationError:
            return jsonify({"success": False, "message": "Invalid request. Please refresh and try again."}), 400

    # ── Extract & strip inputs ─────────────────────────────────────────────────
    name = request.form.get("name", "").strip()[:100]
    email = request.form.get("email", "").strip()[:120]
    subject = request.form.get("subject", "").strip()[:200]
    body = request.form.get("message", "").strip()[:3000]

    # ── Validate ──────────────────────────────────────────────────────────────
    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        errors.append("A valid email address is required.")
    if not subject:
        errors.append("Subject is required.")
    if not body:
        errors.append("Message is required.")

    if errors:
        return jsonify({"success": False, "message": " ".join(errors)}), 400

    # ── Store in database ──────────────────────────────────────────────────────
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")[:45]
        msg = Message(
            name=name,
            email=email,
            subject=subject,
            message=body,
            ip_address=ip,
        )
        db.session.add(msg)
        db.session.commit()
    except Exception:
        logger.exception("Failed to save contact message to database")
        return jsonify({"success": False, "message": "An error occurred. Please try again later."}), 500

    # ── Email notification ─────────────────────────────────────────────────────
    from utils.email_service import send_contact_email
    email_res = send_contact_email(name=name, email=email, subject=subject, message=body, ip_address=ip)
    if email_res.get("success"):
        logger.info("Contact form email delivered successfully via %s", email_res.get("provider"))
    else:
        logger.warning("Contact form email could not be forwarded (%s). Stored in DB.", email_res.get("details"))

    return jsonify({"success": True, "message": "Thank you! Your message has been received."})


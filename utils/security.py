"""
Security utility functions:
- Secure image upload validation (PIL MIME + extension + size + filename)
- Security HTTP response headers middleware
"""
import os
import io
import uuid
import logging
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_PIL_FORMATS = {"PNG", "JPEG", "WEBP"}


def allowed_file(filename: str) -> bool:
    """Check that the filename has an allowed extension."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_and_save_image(file_storage, subfolder: str = "") -> str | None:
    """
    Securely validate and save an uploaded image file.

    Returns the relative URL path (e.g. 'uploads/abc123.png') on success,
    or None if validation fails.

    Validation steps:
    1. Filename extension check
    2. Content-based verification via Pillow Image.open / verify
    3. File size check (enforced by MAX_CONTENT_LENGTH but double-checked)
    4. Unique sanitized filename generation
    5. Save outside code root under static/uploads/
    """
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    if not allowed_file(original_name):
        logger.warning("Upload rejected: disallowed extension — %s", original_name)
        return None

    file_bytes = file_storage.read()

    # Guard: max 5 MB double-check
    if len(file_bytes) > 5 * 1024 * 1024:
        logger.warning("Upload rejected: file too large — %d bytes", len(file_bytes))
        return None

    # Pillow format verification & sanitize
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image_format = image.format.upper() if image.format else ""
        if image_format not in ALLOWED_PIL_FORMATS:
            logger.warning("Upload rejected: invalid image format '%s'", image_format)
            return None
        
        # Strip EXIF metadata to protect user privacy
        clean_io = io.BytesIO()
        image.save(clean_io, format=image_format)
        file_bytes = clean_io.getvalue()
    except Exception as e:
        logger.warning("Upload rejected: failed PIL validation — %s", e)
        return None

    # Build collision-proof random filename
    ext = original_name.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"

    upload_root = current_app.config["UPLOAD_FOLDER"]
    if subfolder:
        upload_dir = os.path.join(upload_root, subfolder)
    else:
        upload_dir = upload_root
    os.makedirs(upload_dir, exist_ok=True)

    save_path = os.path.join(upload_dir, safe_name)

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    relative = f"uploads/{subfolder + '/' if subfolder else ''}{safe_name}"
    logger.info("Upload saved: %s", relative)
    return relative


def validate_and_save_pdf(file_storage, subfolder: str = "cv") -> str | None:
    """
    Securely validate and save an uploaded PDF resume.
    Verifies %PDF magic header bytes, file extension, and size.
    """
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    if not original_name.lower().endswith(".pdf"):
        logger.warning("Upload rejected: not a PDF — %s", original_name)
        return None

    file_bytes = file_storage.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        logger.warning("Upload rejected: PDF file too large — %d bytes", len(file_bytes))
        return None

    # Magic bytes verification for PDF (%PDF)
    if not file_bytes.startswith(b"%PDF"):
        logger.warning("Upload rejected: invalid PDF header signature")
        return None

    safe_name = f"{uuid.uuid4().hex}.pdf"
    upload_root = current_app.config["UPLOAD_FOLDER"]
    upload_dir = os.path.join(upload_root, subfolder) if subfolder else upload_root
    os.makedirs(upload_dir, exist_ok=True)

    save_path = os.path.join(upload_dir, safe_name)
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    relative = f"uploads/{subfolder + '/' if subfolder else ''}{safe_name}"
    logger.info("PDF saved: %s", relative)
    return relative


def apply_security_headers(response):
    """
    Add security response headers to every response.
    CSP is intentionally structured to allow:
    - Google Fonts
    - Font Awesome CDN
    - Unsplash images
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
        "https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com "
        "https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https://images.unsplash.com blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    # Apply HSTS in production or HTTPS environments
    if current_app.config.get("SESSION_COOKIE_SECURE", False):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response


def send_otp_email(to_email: str, otp_code: str, purpose_text: str) -> bool:
    """
    Send OTP verification code to registered admin email via utils.email_service.
    """
    from utils.email_service import send_otp_email as _dispatch_otp
    return _dispatch_otp(to_email=to_email, otp_code=otp_code, purpose_text=purpose_text)



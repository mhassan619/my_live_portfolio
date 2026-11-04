"""
Email Service for Muhammad Hassan's Portfolio CMS.
Optimized for PythonAnywhere (both Free tier allowlisted HTTP APIs and Paid tier SMTP).

Supported providers (in cascade order):
1. Resend API (HTTP POST to https://api.resend.com/emails) — Allowlisted on PythonAnywhere Free Tier.
2. Brevo API (HTTP POST to https://api.brevo.com/v3/smtp/email) — Allowlisted on PythonAnywhere Free Tier.
3. Flask-Mail / SMTP (Port 587 TLS) — For Paid PythonAnywhere accounts, VPS, or local development.
"""
import os
import logging
from datetime import datetime, timezone
import requests
from flask import current_app

logger = logging.getLogger(__name__)


def _build_contact_html(name: str, email: str, subject: str, message: str, ip: str = "") -> str:
    """Generate modern, responsive HTML email for contact form notifications."""
    sent_time = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    clean_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>New Portfolio Message</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%); padding: 24px 28px; text-align: left;">
      <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.01em;">
        📬 New Portfolio Message
      </h1>
      <p style="margin: 6px 0 0 0; color: #ccfbf1; font-size: 13px;">
        Received from your portfolio website contact form
      </p>
    </div>

    <!-- Body -->
    <div style="padding: 28px;">
      <!-- Sender Meta Card -->
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
        <tr>
          <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #64748b; width: 90px; font-weight: 600;">From:</td>
          <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-size: 14px; color: #0f172a; font-weight: 600;">
            {name} &lt;<a href="mailto:{email}" style="color: #0d9488; text-decoration: none;">{email}</a>&gt;
          </td>
        </tr>
        <tr>
          <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #64748b; font-weight: 600;">Subject:</td>
          <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-size: 14px; color: #0f172a; font-weight: 600;">{subject}</td>
        </tr>
        <tr>
          <td style="padding: 12px 16px; font-size: 13px; color: #64748b; font-weight: 600;">Date:</td>
          <td style="padding: 12px 16px; font-size: 13px; color: #475569;">{sent_time} {f'· IP: {ip}' if ip else ''}</td>
        </tr>
      </table>

      <!-- Message Header -->
      <h2 style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin: 0 0 10px 0;">
        Message Content
      </h2>

      <!-- Message Text -->
      <div style="background: #ffffff; border-left: 4px solid #0d9488; padding: 16px 20px; border-radius: 0 8px 8px 0; background-color: #f0fdfa; font-size: 15px; line-height: 1.7; color: #1e293b; margin-bottom: 28px;">
        {clean_msg}
      </div>

      <!-- Action Button -->
      <div style="text-align: center; margin: 24px 0 12px 0;">
        <a href="mailto:{email}?subject=Re:%20{subject}" style="display: inline-block; background-color: #0d9488; color: #ffffff; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 600; text-decoration: none; box-shadow: 0 2px 6px rgba(13, 148, 136, 0.3);">
          ✉️ Reply Directly to {name}
        </a>
      </div>
      <p style="text-align: center; font-size: 12px; color: #94a3b8; margin: 8px 0 0 0;">
        Or simply click "Reply" in your email client (Reply-To is configured to {email})
      </p>
    </div>

    <!-- Footer -->
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 28px; text-align: center; font-size: 12px; color: #94a3b8;">
      Muhammad Hassan Portfolio CMS &nbsp;·&nbsp; AI Engineer &amp; LLM Builder
    </div>
  </div>
</body>
</html>"""


def send_contact_email(name: str, email: str, subject: str, message: str, ip_address: str = "") -> dict:
    """
    Deliver contact message to owner's inbox.
    Tries Resend API -> Brevo API -> Flask-Mail SMTP.
    Returns: {"success": bool, "provider": str, "details": str}
    """
    recipient = (
        current_app.config.get("CONTACT_RECIPIENT_EMAIL")
        or os.environ.get("CONTACT_RECIPIENT_EMAIL")
        or "mhassanawan66521@gmail.com"
    ).strip()

    email_subject = f"🚀 Portfolio Inquiry: {name} — {subject}"
    html_body = _build_contact_html(name, email, subject, message, ip_address)
    plain_body = (
        f"New message from your portfolio website!\n\n"
        f"Sender: {name} ({email})\n"
        f"Subject: {subject}\n"
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"IP: {ip_address}\n\n"
        f"Message:\n"
        f"{message}\n\n"
        f"---\n"
        f"Reply directly by emailing {email}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Try Resend API (HTTP — PythonAnywhere free tier compatible)
    # ──────────────────────────────────────────────────────────────────────────
    resend_api_key = (
        current_app.config.get("RESEND_API_KEY")
        or os.environ.get("RESEND_API_KEY", "")
    ).strip()

    if resend_api_key:
        try:
            from_sender = current_app.config.get(
                "RESEND_FROM_EMAIL",
                "Muhammad Hassan Portfolio <onboarding@resend.dev>",
            )
            headers = {
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "from": from_sender,
                "to": [recipient],
                "reply_to": email,
                "subject": email_subject,
                "html": html_body,
                "text": plain_body,
            }
            logger.info("Dispatching email via Resend API to %s...", recipient)
            r = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=12)
            if r.status_code in (200, 201):
                res_data = r.json() if r.text else {}
                email_id = res_data.get("id", "ok")
                logger.info("Resend email dispatched successfully! ID: %s", email_id)
                return {"success": True, "provider": "Resend API", "details": f"Delivered (ID: {email_id})"}
            else:
                logger.warning("Resend API rejected request. HTTP %s: %s", r.status_code, r.text)
        except Exception as e:
            logger.exception("Resend API dispatch error: %s", e)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Try Brevo API (HTTP — PythonAnywhere free tier compatible)
    # ──────────────────────────────────────────────────────────────────────────
    brevo_api_key = (
        current_app.config.get("BREVO_API_KEY")
        or os.environ.get("BREVO_API_KEY", "")
    ).strip()

    if brevo_api_key:
        try:
            sender_email = (
                current_app.config.get("BREVO_SENDER_EMAIL")
                or os.environ.get("BREVO_SENDER_EMAIL")
                or recipient
            ).strip()
            headers = {
                "api-key": brevo_api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "sender": {"name": "Portfolio Contact", "email": sender_email},
                "to": [{"email": recipient, "name": "Muhammad Hassan"}],
                "replyTo": {"email": email, "name": name},
                "subject": email_subject,
                "htmlContent": html_body,
                "textContent": plain_body,
            }
            logger.info("Dispatching email via Brevo API to %s...", recipient)
            r = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=12)
            if r.status_code in (200, 201):
                logger.info("Brevo email dispatched successfully!")
                return {"success": True, "provider": "Brevo API", "details": "Delivered"}
            else:
                logger.warning("Brevo API rejected request. HTTP %s: %s", r.status_code, r.text)
        except Exception as e:
            logger.exception("Brevo API dispatch error: %s", e)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Try SMTP via Flask-Mail (Works for Paid PythonAnywhere or Local Dev)
    # ──────────────────────────────────────────────────────────────────────────
    mail_user = current_app.config.get("MAIL_USERNAME")
    mail_pass = current_app.config.get("MAIL_PASSWORD")
    if mail_user and mail_pass:
        try:
            from extensions import mail
            from flask_mail import Message as MailMessage

            msg = MailMessage(
                subject=email_subject,
                recipients=[recipient],
                reply_to=email,
                body=plain_body,
                html=html_body,
            )
            mail.send(msg)
            logger.info("Email dispatched successfully via Flask-Mail SMTP to %s", recipient)
            return {"success": True, "provider": "Flask-Mail SMTP", "details": "Delivered"}
        except Exception as e:
            logger.exception("SMTP dispatch failed: %s (Note: PythonAnywhere free accounts block SMTP ports. Use Resend API instead).", e)

    # If no provider succeeded
    logger.warning(
        "Could not deliver email to %s. No valid email provider credentials configured or all providers failed. "
        "To receive emails on PythonAnywhere Free Tier, set RESEND_API_KEY in .env.",
        recipient,
    )
    return {
        "success": False,
        "provider": None,
        "details": "No email provider succeeded. The message has been securely saved to the database.",
    }


def send_otp_email(to_email: str, otp_code: str, purpose_text: str) -> bool:
    """
    Send OTP verification code to registered admin email.
    Cascades through Resend API -> Brevo API -> Flask-Mail.
    """
    subject = f"Portfolio CMS Security Verification Code: {otp_code}"
    body = (
        f"Hello,\n\n"
        f"Your verification code (OTP) for {purpose_text} is:\n\n"
        f"    {otp_code}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"If you did not initiate this request, please review your account security immediately.\n\n"
        f"— Muhammad Hassan Portfolio CMS"
    )
    html_body = f"""<div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #0f172a; margin-top: 0;">🔐 Security Verification Code</h2>
        <p style="color: #334155;">Hello,</p>
        <p style="color: #334155;">Your OTP verification code for <strong>{purpose_text}</strong> is:</p>
        <div style="background: #f1f5f9; padding: 14px 20px; font-size: 26px; font-weight: bold; letter-spacing: 6px; color: #0d9488; border-radius: 6px; text-align: center; margin: 20px 0;">
            {otp_code}
        </div>
        <p style="color: #64748b; font-size: 13px; line-height: 1.5;">This code will expire in 10 minutes. If you did not initiate this request, please review your account credentials immediately.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">Muhammad Hassan Portfolio Security System</p>
    </div>"""

    # 1. Resend API
    resend_api_key = (
        current_app.config.get("RESEND_API_KEY")
        or os.environ.get("RESEND_API_KEY", "")
    ).strip()
    if resend_api_key:
        try:
            from_sender = current_app.config.get(
                "RESEND_FROM_EMAIL",
                "Muhammad Hassan Portfolio <onboarding@resend.dev>",
            )
            headers = {"Authorization": f"Bearer {resend_api_key}", "Content-Type": "application/json"}
            payload = {
                "from": from_sender,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": body,
            }
            r = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
            if r.status_code in (200, 201):
                logger.info("OTP successfully sent via Resend API to %s", to_email)
                return True
        except Exception:
            logger.exception("Failed to dispatch OTP via Resend")

    # 2. SMTP
    mail_user = current_app.config.get("MAIL_USERNAME")
    mail_pass = current_app.config.get("MAIL_PASSWORD")
    if mail_user and mail_pass:
        try:
            from extensions import mail
            from flask_mail import Message as MailMessage
            msg = MailMessage(subject=subject, recipients=[to_email], body=body, html=html_body)
            mail.send(msg)
            logger.info("OTP successfully sent via SMTP to %s", to_email)
            return True
        except Exception:
            logger.exception("Failed to dispatch OTP via SMTP")

    return False


def send_test_email(to_email: str = None) -> dict:
    """
    Send an immediate test email to verify inbox delivery.
    """
    recipient = to_email or current_app.config.get("CONTACT_RECIPIENT_EMAIL", "mhassanawan66521@gmail.com")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return send_contact_email(
        name="Portfolio Test Agent",
        email="test@hassan-portfolio.dev",
        subject=f"System Email Delivery Test ({now_str})",
        message=(
            f"Congratulations!\n\n"
            f"If you are reading this email in your inbox, your portfolio email notifications are working perfectly.\n\n"
            f"Timestamp: {now_str}\n"
            f"Recipient: {recipient}\n"
            f"PythonAnywhere Compatible: YES\n"
        ),
        ip_address="127.0.0.1",
    )

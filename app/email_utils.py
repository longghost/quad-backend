"""
Transactional email helpers for Quad Marketplace.

Password-reset email is sent through the Resend HTTPS API instead of SMTP.
This works on Render Free because it uses outbound HTTPS rather than SMTP
ports 25/465/587.

Required environment variables:
  RESEND_API_KEY      - Resend API key (starts with ``re_``)
  RESEND_FROM_EMAIL   - verified sender, e.g. ``Quad <noreply@yourdomain.com>``
  FRONTEND_URL        - live frontend URL, e.g. ``https://quad-marketplace.netlify.app``
"""

from html import escape

import requests

from app.config import settings


RESEND_API_URL = "https://api.resend.com/emails"


def send_password_reset_email(to_email: str, full_name: str, reset_token: str) -> bool:
    """Send a password-reset email through Resend.

    Returns True only when Resend accepts the email request. Any network or
    API error is logged and returns False so the caller can handle the failure.
    """
    if not settings.resend_api_key or not settings.resend_from_email:
        print(
            "Resend not configured; skipping email send. "
            "Set RESEND_API_KEY and RESEND_FROM_EMAIL."
        )
        return False

    reset_link = (
        f"{settings.frontend_url.rstrip('/')}/reset-password.html?token={reset_token}"
    )

    safe_name = escape(full_name or "there")
    safe_reset_link = escape(reset_link, quote=True)

    text_body = (
        f"Hi {full_name or 'there'},\n\n"
        "Someone requested a password reset for your Quad account.\n"
        f"Reset it here (link expires in 1 hour): {reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )

    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
      <h2 style="color:#14213D;">Reset your Quad password</h2>
      <p>Hi {safe_name},</p>
      <p>Someone requested a password reset for your Quad account. This link expires in 1 hour.</p>
      <p style="text-align:center;margin:28px 0;">
        <a href="{safe_reset_link}" style="background:#FFB627;color:#14213D;padding:12px 28px;
           border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">
          Reset Password
        </a>
      </p>
      <p style="color:#8894AC;font-size:.85rem;">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
    """

    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": "Reset your Quad password",
        "text": text_body,
        "html": html_body,
        "tags": [{"name": "category", "value": "password_reset"}],
    }

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"Failed to send reset email through Resend: {exc}")
        return False

    if response.ok:
        try:
            data = response.json()
            print(f"Password reset email accepted by Resend (id={data.get('id', 'unknown')})")
        except ValueError:
            print("Password reset email accepted by Resend.")
        return True

    # Log the provider's response, but never log the API key.
    try:
        error_data = response.json()
        print(
            "Resend rejected password reset email "
            f"(HTTP {response.status_code}): {error_data}"
        )
    except ValueError:
        print(
            "Resend rejected password reset email "
            f"(HTTP {response.status_code}): {response.text[:500]}"
        )
    return False

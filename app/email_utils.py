"""
Sends transactional email (currently just password reset) via Gmail SMTP.

Setup required in .env / Render environment variables:
  SMTP_EMAIL          - the Gmail address sending the mail (e.g. longman661.ab@gmail.com)
  SMTP_APP_PASSWORD   - a Gmail "App Password" (NOT your normal Gmail password)
                         Generate one at: https://myaccount.google.com/apppasswords
                         (requires 2-Step Verification to be turned on for the Google account)
  FRONTEND_URL         - the live site URL, used to build the reset link
                          e.g. https://quad-marketplace.netlify.app
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def send_password_reset_email(to_email: str, full_name: str, reset_token: str) -> bool:
    if not settings.smtp_email or not settings.smtp_app_password:
        # Not configured — fail quietly rather than crashing the request.
        print("SMTP not configured; skipping email send. Set SMTP_EMAIL and SMTP_APP_PASSWORD.")
        return False

    reset_link = f"{settings.frontend_url}/reset-password.html?token={reset_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your Quad password"
    msg["From"] = settings.smtp_email
    msg["To"] = to_email

    text_body = (
        f"Hi {full_name},\n\n"
        f"Someone requested a password reset for your Quad account.\n"
        f"Reset it here (link expires in 1 hour): {reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
      <h2 style="color:#14213D;">Reset your Quad password</h2>
      <p>Hi {full_name},</p>
      <p>Someone requested a password reset for your Quad account. This link expires in 1 hour.</p>
      <p style="text-align:center;margin:28px 0;">
        <a href="{reset_link}" style="background:#FFB627;color:#14213D;padding:12px 28px;
           border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;">
          Reset Password
        </a>
      </p>
      <p style="color:#8894AC;font-size:.85rem;">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.smtp_email, settings.smtp_app_password)
            server.sendmail(settings.smtp_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send reset email: {e}")
        return False

"""SendGrid email delivery. Returns True on success, False on failure (non-blocking)."""
import logging
from datetime import datetime

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_kyc_link_email(
    to_email: str,
    customer_name: str,
    kyc_url: str,
    expires_at: datetime,
) -> bool:
    if not settings.sendgrid_api_key:
        logger.warning("SendGrid API key not set — skipping email, KYC URL: %s", kyc_url)
        return False

    expires_str = expires_at.strftime("%d %b %Y, %I:%M %p UTC")
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1a3c7a; padding: 24px; text-align: center;">
        <h1 style="color: white; margin: 0;">Poonawalla Fincorp</h1>
      </div>
      <div style="padding: 32px; background: #f9f9f9;">
        <h2>Hi {customer_name},</h2>
        <p>Your Video KYC session is ready. Please click the button below to begin your personal loan application.</p>
        <p>The session takes about <strong>10–12 minutes</strong>. You'll need:</p>
        <ul>
          <li>A working camera and microphone</li>
          <li>Good lighting</li>
          <li>A quiet place to answer 8 short questions</li>
        </ul>
        <div style="text-align: center; margin: 32px 0;">
          <a href="{kyc_url}"
             style="background: #1a3c7a; color: white; padding: 16px 32px;
                    text-decoration: none; border-radius: 8px; font-size: 18px;">
            Start My KYC Session
          </a>
        </div>
        <p style="color: #666; font-size: 13px;">
          This link expires on <strong>{expires_str}</strong>.<br>
          If the button doesn't work, copy and paste this link:<br>
          <a href="{kyc_url}" style="color: #1a3c7a;">{kyc_url}</a>
        </p>
      </div>
      <div style="padding: 16px; background: #eee; font-size: 11px; color: #999; text-align: center;">
        Poonawalla Fincorp Ltd. | NBFC registered with RBI<br>
        Do not share this link with anyone.
      </div>
    </div>
    """

    message = Mail(
        from_email=From(settings.sendgrid_from_email, settings.sendgrid_from_name),
        to_emails=To(to_email, customer_name),
        subject="Your Video KYC Link — Poonawalla Fincorp Personal Loan",
        html_content=html,
    )

    try:
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        if response.status_code in (200, 202):
            return True
        logger.error("SendGrid returned %s", response.status_code)
        return False
    except Exception as exc:
        logger.error("SendGrid error: %s", exc)
        return False


async def send_offer_email(
    to_email: str,
    customer_name: str,
    download_url: str,
    approved_amount: float,
    interest_rate: float,
) -> bool:
    if not settings.sendgrid_api_key:
        logger.warning("SendGrid not configured — skipping offer email")
        return False

    amount_fmt = f"₹{approved_amount:,.0f}"
    rate_fmt = f"{interest_rate:.1f}%"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1a3c7a; padding: 24px; text-align: center;">
        <h1 style="color: white; margin: 0;">Poonawalla Fincorp</h1>
      </div>
      <div style="padding: 32px; background: #f9f9f9;">
        <h2 style="color: #2e7d32;">Congratulations, {customer_name}! 🎉</h2>
        <p>Your personal loan has been approved.</p>
        <div style="background: #e8f5e9; border: 2px solid #2e7d32; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
          <div style="font-size: 36px; font-weight: bold; color: #1a3c7a;">{amount_fmt}</div>
          <div style="color: #555;">at {rate_fmt} per annum</div>
        </div>
        <div style="text-align: center; margin: 24px 0;">
          <a href="{download_url}"
             style="background: #2e7d32; color: white; padding: 14px 28px;
                    text-decoration: none; border-radius: 8px; font-size: 16px;">
            Download Your Offer Letter
          </a>
        </div>
        <p style="color: #666; font-size: 13px;">
          The PDF is password protected. Use the last 4 digits of your registered mobile number.<br>
          This offer is valid for 30 days.
        </p>
      </div>
    </div>
    """

    message = Mail(
        from_email=From(settings.sendgrid_from_email, settings.sendgrid_from_name),
        to_emails=To(to_email, customer_name),
        subject=f"Your Loan Offer — {amount_fmt} Approved | Poonawalla Fincorp",
        html_content=html,
    )

    try:
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        return response.status_code in (200, 202)
    except Exception as exc:
        logger.error("SendGrid offer email error: %s", exc)
        return False

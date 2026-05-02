"""Email delivery via Resend HTTP API."""
import logging
from datetime import datetime

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_html(customer_name: str, kyc_url: str, expires_at: datetime) -> str:
    expires_str = expires_at.strftime("%d %b %Y, %I:%M %p UTC")
    return f"""
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


async def send_kyc_link_email(
    to_email: str,
    customer_name: str,
    kyc_url: str,
    expires_at: datetime,
) -> bool:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping email, KYC URL: %s", kyc_url)
        return False

    html = _build_html(customer_name, kyc_url, expires_at)
    hours = max(1, min(72, int((expires_at.timestamp() - datetime.utcnow().timestamp()) / 3600)))

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.email_from,
                    "to": [to_email],
                    "subject": "Your Video KYC Link — Poonawalla Fincorp Personal Loan",
                    "html": html,
                    "text": f"Hi {customer_name}, your KYC session is ready. Visit: {kyc_url} — expires in {hours} hours.",
                },
            )
        if resp.status_code == 200:
            return True
        logger.error("Resend API returned %s: %s", resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.error("Resend email error: %s", exc)
        return False


async def send_offer_email(
    to_email: str,
    _customer_name: str,
    _download_url: str,
    _approved_amount: float,
    _interest_rate: float,
) -> bool:
    logger.info("Offer email not yet implemented — skipping for %s", to_email)
    return False

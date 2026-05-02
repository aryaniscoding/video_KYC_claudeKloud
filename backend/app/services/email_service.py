"""Email delivery via AWS SES (boto3)."""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import boto3

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_lock = threading.Lock()
_ses_client = None
_executor = ThreadPoolExecutor(max_workers=2)


def _get_ses():
    global _ses_client
    if _ses_client is None:
        with _lock:
            if _ses_client is None:
                _ses_client = boto3.client(
                    "ses",
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                )
    return _ses_client


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
    if not settings.aws_access_key_id:
        logger.warning("AWS credentials not set — skipping email")
        return False

    html = _build_html(customer_name, kyc_url, expires_at)
    hours = max(1, min(72, int((expires_at.timestamp() - datetime.utcnow().timestamp()) / 3600)))

    def _send():
        return _get_ses().send_email(
            Source=settings.ses_from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": "Your Video KYC Link — Poonawalla Fincorp Personal Loan"},
                "Body": {
                    "Html": {"Data": html},
                    "Text": {"Data": f"Hi {customer_name}, your KYC session is ready. Visit: {kyc_url} — expires in {hours} hours."},
                },
            },
        )

    import asyncio
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _send)
        return True
    except Exception as exc:
        logger.error("SES send error: %s", exc)
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

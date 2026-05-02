"""Email delivery — delegates to the nodemailer HTTP server."""
import logging
from datetime import datetime

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_kyc_link_email(
    to_email: str,
    customer_name: str,
    kyc_url: str,
    expires_at: datetime,
) -> bool:
    url = f"{settings.email_service_url}/api/send-email"
    # rough hours until expiry, capped at 72 for the template
    hours = max(1, min(72, int((expires_at.timestamp() - datetime.utcnow().timestamp()) / 3600)))
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json={
                "toEmail": to_email,
                "customerName": customer_name,
                "sessionUrl": kyc_url,
                "expiryHours": hours,
            })
        if resp.status_code == 200:
            return True
        logger.error("Email service returned %s: %s", resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.error("Email service error: %s", exc)
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

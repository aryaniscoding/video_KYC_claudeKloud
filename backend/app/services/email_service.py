"""AWS SES email delivery via boto3. Returns True on success, False on failure (non-blocking)."""
import logging
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _ses_client():
    return boto3.client(
        "ses",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def _send_email(to_email: str, to_name: str, subject: str, html: str) -> bool:
    try:
        _ses_client().send_email(
            Source=f"{settings.sendgrid_from_name} <{settings.sendgrid_from_email}>",
            Destination={"ToAddresses": [f"{to_name} <{to_email}>"]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html, "Charset": "UTF-8"}},
            },
        )
        return True
    except (BotoCoreError, ClientError) as exc:
        logger.error("SES send error: %s", exc)
        return False


_FOOTER = """
  <div style="padding:16px;background:#eee;font-size:11px;color:#999;text-align:center;">
    Poonawalla Fincorp Ltd. | NBFC registered with RBI
  </div>
"""

_HEADER = """
  <div style="background:#1a3c7a;padding:24px;text-align:center;">
    <h1 style="color:white;margin:0;">Poonawalla Fincorp</h1>
  </div>
"""


async def send_kyc_link_email(
    to_email: str,
    customer_name: str,
    kyc_url: str,
    expires_at: datetime,
) -> bool:
    if not settings.aws_access_key_id:
        logger.warning("AWS credentials not set — skipping KYC link email, URL: %s", kyc_url)
        return False

    expires_str = expires_at.strftime("%d %b %Y, %I:%M %p UTC")
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_HEADER}
      <div style="padding:32px;background:#f9f9f9;">
        <h2>Hi {customer_name},</h2>
        <p>Your Video KYC session is ready. Please click the button below to begin your personal loan application.</p>
        <p>The session takes about <strong>10–12 minutes</strong>. You'll need:</p>
        <ul>
          <li>A working camera and microphone</li>
          <li>Good lighting</li>
          <li>A quiet place to answer 8 short questions</li>
        </ul>
        <div style="text-align:center;margin:32px 0;">
          <a href="{kyc_url}" style="background:#1a3c7a;color:white;padding:16px 32px;
             text-decoration:none;border-radius:8px;font-size:18px;">
            Start My KYC Session
          </a>
        </div>
        <p style="color:#666;font-size:13px;">
          This link expires on <strong>{expires_str}</strong>.<br>
          If the button doesn't work, copy and paste:<br>
          <a href="{kyc_url}" style="color:#1a3c7a;">{kyc_url}</a>
        </p>
      </div>
      {_FOOTER}
    </div>
    """
    return _send_email(to_email, customer_name,
                       "Your Video KYC Link — Poonawalla Fincorp Personal Loan", html)


async def send_offer_email(
    to_email: str,
    customer_name: str,
    download_url: str,
    approved_amount: float,
    interest_rate: float,
) -> bool:
    if not settings.aws_access_key_id:
        logger.warning("AWS credentials not set — skipping offer email")
        return False

    amount_fmt = f"₹{approved_amount:,.0f}"
    rate_fmt = f"{interest_rate:.1f}%"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_HEADER}
      <div style="padding:32px;background:#f9f9f9;">
        <h2 style="color:#2e7d32;">Congratulations, {customer_name}!</h2>
        <p>Your personal loan application has been <strong>approved</strong>.</p>
        <div style="background:#e8f5e9;border:2px solid #2e7d32;border-radius:8px;
                    padding:24px;text-align:center;margin:24px 0;">
          <div style="font-size:36px;font-weight:bold;color:#1a3c7a;">{amount_fmt}</div>
          <div style="color:#555;">at {rate_fmt} per annum</div>
        </div>
        <div style="text-align:center;margin:24px 0;">
          <a href="{download_url}" style="background:#2e7d32;color:white;padding:14px 28px;
             text-decoration:none;border-radius:8px;font-size:16px;">
            Download Your Offer Letter
          </a>
        </div>
        <p style="color:#666;font-size:13px;">
          The PDF is password-protected. Use the last 4 digits of your registered mobile number.<br>
          This offer is valid for 30 days.
        </p>
      </div>
      {_FOOTER}
    </div>
    """
    return _send_email(to_email, customer_name,
                       f"Loan Approved — {amount_fmt} | Poonawalla Fincorp", html)


async def send_rejection_email(
    to_email: str,
    customer_name: str,
    decline_reason: str | None = None,
) -> bool:
    if not settings.aws_access_key_id:
        logger.warning("AWS credentials not set — skipping rejection email")
        return False

    reason_block = ""
    if decline_reason:
        reason_block = f"""
        <div style="background:#fff3cd;border-left:4px solid #e65100;padding:16px;margin:20px 0;border-radius:4px;">
          <p style="margin:0;font-size:14px;color:#333;"><strong>Reason:</strong> {decline_reason}</p>
        </div>"""

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_HEADER}
      <div style="padding:32px;background:#f9f9f9;">
        <h2 style="color:#c62828;">Dear {customer_name},</h2>
        <p>Thank you for applying for a personal loan with Poonawalla Fincorp.</p>
        <p>After careful review of your application, we regret to inform you that we are
           <strong>unable to approve your loan request</strong> at this time.</p>
        {reason_block}
        <p>Here are some steps you can take to improve your eligibility:</p>
        <ul>
          <li>Maintain a healthy CIBIL score above 700</li>
          <li>Reduce existing EMI obligations before reapplying</li>
          <li>Ensure stable employment for at least 1 year</li>
        </ul>
        <p>You may reapply after <strong>90 days</strong>. For any queries, call
           <strong>1800-555-0000</strong>.</p>
      </div>
      {_FOOTER}
    </div>
    """
    return _send_email(to_email, customer_name,
                       "Loan Application Update — Poonawalla Fincorp", html)

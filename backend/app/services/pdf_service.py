"""
PDF Generation & Delivery — Phase 9 of the blueprint.

Sections: letterhead, customer details, offer box, EMI table,
SHAP approval basis, fees, consent record, next steps, regulatory footer.

No password protection (will be added in a later stage).
Stored in Supabase Storage with SHA-256 hash. Pre-signed URL (30-day).
"""
import hashlib
import io
import logging
import os
from datetime import datetime, timezone, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.config import get_settings
from app.database import get_supabase

logger = logging.getLogger(__name__)
settings = get_settings()

# Brand colours
_NAVY = colors.HexColor("#1a3c7a")
_GREEN = colors.HexColor("#2e7d32")
_LIGHT_GREY = colors.HexColor("#f5f5f5")

# Register a Unicode-capable font so the ₹ symbol renders correctly.
# ReportLab's built-in Helvetica is Latin-1 only and silently drops ₹.
_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"

def _init_fonts() -> None:
    global _FONT, _FONT_BOLD
    candidates = [
        ("C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/calibri.ttf",  "C:/Windows/Fonts/calibrib.ttf"),
    ]
    for regular, bold in candidates:
        try:
            if os.path.exists(regular):
                pdfmetrics.registerFont(TTFont("KYCFont", regular))
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont("KYCFont-Bold", bold))
                    _FONT_BOLD = "KYCFont-Bold"
                else:
                    _FONT_BOLD = "KYCFont"
                _FONT = "KYCFont"
                logger.info("PDF font: registered %s for Unicode support", regular)
                return
        except Exception as e:
            logger.debug("Font registration failed for %s: %s", regular, e)
    logger.warning("No Unicode font found — ₹ symbol may not render in PDFs")

_init_fonts()


async def generate_offer_pdf(
    session,
    application,
    customer,
    decision,
    offer: dict,
    shap_reasons: list[str],
) -> dict:
    """
    Generate, password-protect, upload, and return metadata.
    Returns {storage_path, pdf_hash, download_url, download_expires_at}.
    """
    pdf_bytes = _build_pdf(session, application, customer, decision, offer, shap_reasons)

    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    storage_path = f"pdfs/{session.token_jti}/{decision.offer_ref_id}.pdf"

    # Upload to Supabase Storage
    sb = get_supabase()
    sb.storage.from_(settings.storage_bucket_pdfs).upload(
        path=storage_path,
        file=pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    # Pre-signed URL (30 days) — handle both supabase-py v1 and v2 response shapes
    expires_in_seconds = 30 * 24 * 3600
    url_response = sb.storage.from_(settings.storage_bucket_pdfs).create_signed_url(
        path=storage_path,
        expires_in=expires_in_seconds,
    )
    if isinstance(url_response, dict):
        download_url = (
            url_response.get("signedURL")
            or url_response.get("signedUrl")
            or url_response.get("signed_url")
            or ""
        )
    else:
        download_url = getattr(url_response, "signed_url", "") or getattr(url_response, "signedURL", "")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

    return {
        "storage_path": storage_path,
        "pdf_hash": pdf_hash,
        "download_url": download_url,
        "download_expires_at": expires_at,
    }


def _build_pdf(session, application, customer, decision, _offer: dict, shap_reasons: list[str]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    story = []

    # ── Letterhead ─────────────────────────────────────────────────────────────
    story.append(_heading("POONAWALLA FINCORP LIMITED", size=18))
    story.append(_subheading("Personal Loan Offer Letter"))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=_NAVY))
    story.append(Spacer(1, 3*mm))

    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    story.append(_body(f"Date: {date_str}   |   Offer Ref: {decision.offer_ref_id}"))
    story.append(Spacer(1, 5*mm))

    # ── Customer details ───────────────────────────────────────────────────────
    story.append(_section_title("Applicant Details"))
    cust_data = [
        ["Name", application.full_name or customer.name],
        ["Date of Birth", str(application.dob) if application.dob else "—"],
        ["Address", _fmt_address(application)],
        ["Mobile", f"XXXXXX{customer.phone_last4}"],
        ["Employment", (application.employment_type or "—").replace("_", " ").title()],
        ["Employer", application.employer_name or "—"],
        ["Monthly Income", f"₹{application.monthly_income:,.0f}" if application.monthly_income else "—"],
    ]
    story.append(_info_table(cust_data))
    story.append(Spacer(1, 5*mm))

    # ── Offer box ──────────────────────────────────────────────────────────────
    story.append(_section_title("Loan Offer Summary"))
    offer_data = [
        ["Approved Loan Amount", f"₹{decision.approved_amount:,.0f}"],
        ["Interest Rate (p.a.)", f"{decision.interest_rate:.1f}%"],
        ["Processing Fee", f"{decision.processing_fee_pct:.1f}% of loan amount"],
        ["Offer Valid Until", decision.offer_valid_until.strftime("%d %B %Y") if decision.offer_valid_until else "30 days"],
    ]
    offer_table = Table(offer_data, colWidths=[90*mm, 80*mm])
    offer_table.setStyle(TableStyle([
        # Labels column: navy background, white text — set explicitly with no overrides
        ("BACKGROUND", (0, 0), (0, -1), _NAVY),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
        # Values column: light grey background, dark text
        ("BACKGROUND", (1, 0), (1, -1), _LIGHT_GREY),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.black),
        ("FONTNAME", (1, 0), (1, -1), _FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(offer_table)
    story.append(Spacer(1, 5*mm))

    # ── EMI options table ──────────────────────────────────────────────────────
    if decision.emi_options:
        story.append(_section_title("EMI Options"))
        emi_header = [["Tenure", "Monthly EMI", "Total Payable", "Total Interest"]]
        emi_rows = [
            [
                f"{opt['tenure_months']} months",
                f"₹{opt['emi_amount']:,.0f}",
                f"₹{opt['total_payable']:,.0f}",
                f"₹{opt['total_interest_inr']:,.0f}",
            ]
            for opt in decision.emi_options
        ]
        rec_tenure = decision.recommended_tenure_months
        highlight_row = next(
            (i + 1 for i, opt in enumerate(decision.emi_options) if opt["tenure_months"] == rec_tenure),
            1,
        )
        emi_table = Table(emi_header + emi_rows, colWidths=[40*mm, 45*mm, 45*mm, 45*mm])
        emi_table.setStyle(TableStyle([
            # Header row: navy background, white bold text
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            # Data rows: alternating light grey / white, dark text
            ("FONTNAME", (0, 1), (-1, -1), _FONT),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_GREY, colors.white]),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6),
            # Highlight recommended tenure row (applied last so it overrides ROWBACKGROUNDS)
            ("BACKGROUND", (0, highlight_row), (-1, highlight_row), colors.HexColor("#e8f5e9")),
        ]))
        story.append(emi_table)
        story.append(_body("* Highlighted row is the recommended tenure.", size=8))
        story.append(Spacer(1, 5*mm))

    # ── Approval basis (SHAP) ──────────────────────────────────────────────────
    if shap_reasons:
        story.append(_section_title("Why You Were Approved"))
        for i, reason in enumerate(shap_reasons[:3], 1):
            story.append(_body(f"{i}. {reason}"))
        story.append(Spacer(1, 5*mm))

    # ── Fees & charges ─────────────────────────────────────────────────────────
    story.append(_section_title("Fees & Charges"))
    fees_data = [
        ["Processing Fee", f"{decision.processing_fee_pct:.1f}% (deducted from disbursement)"],
        ["Prepayment Charges", "2% on outstanding principal after 6 EMIs"],
        ["Late Payment Fee", "₹500 per missed EMI + penal interest @ 2% p.m."],
    ]
    story.append(_info_table(fees_data))
    story.append(Spacer(1, 5*mm))

    # ── Consent record ─────────────────────────────────────────────────────────
    story.append(_section_title("Consent Record"))
    consent_data = [
        ["Session ID", session.token_jti],
        ["Consent Captured", session.consent_timestamp.strftime("%d %b %Y %H:%M:%S UTC") if session.consent_timestamp else "—"],
        ["Digital Fingerprint", session.consent_hash[:32] + "..." if session.consent_hash else "—"],
    ]
    story.append(_info_table(consent_data))
    story.append(Spacer(1, 5*mm))

    # ── Next steps ─────────────────────────────────────────────────────────────
    story.append(_section_title("Next Steps"))
    story.append(_body("1. Click 'Accept This Offer' in your session or reply to this email."))
    story.append(_body("2. Upload KYC documents (Aadhaar + PAN) via the portal link sent separately."))
    story.append(_body("3. Loan will be disbursed within 2 business days of document verification."))
    story.append(Spacer(1, 8*mm))

    # ── Regulatory footer ──────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 2*mm))
    story.append(_body(
        "Poonawalla Fincorp Ltd. | CIN: U65910PN2005PLC020189 | NBFC registered with Reserve Bank of India | "
        "RBI Registration No.: N-13.01707 | Grievance Officer: grievance@poonawallafincorp.com | "
        "This offer is subject to KYC verification and final credit approval. "
        "Interest rates are subject to change per RBI guidelines.",
        size=7,
    ))

    doc.build(story)
    return buf.getvalue()


def _password_protect(pdf_bytes: bytes, password: str) -> bytes:
    """Encrypt PDF with password using pikepdf."""
    try:
        import pikepdf
        pdf_in = pikepdf.open(io.BytesIO(pdf_bytes))
        buf_out = io.BytesIO()
        pdf_in.save(
            buf_out,
            encryption=pikepdf.Encryption(user=password, owner=password + "_admin", R=4),
        )
        return buf_out.getvalue()
    except Exception as e:
        logger.warning("PDF password protection failed: %s — returning unprotected", e)
        return pdf_bytes


# ── Style helpers ──────────────────────────────────────────────────────────────

def _heading(text: str, size: int = 14) -> Paragraph:
    style = ParagraphStyle("h", fontName=_FONT_BOLD, fontSize=size, textColor=_NAVY, spaceAfter=2)
    return Paragraph(text, style)


def _subheading(text: str) -> Paragraph:
    style = ParagraphStyle("sh", fontName=_FONT, fontSize=11, textColor=colors.grey)
    return Paragraph(text, style)


def _section_title(text: str) -> Paragraph:
    style = ParagraphStyle("st", fontName=_FONT_BOLD, fontSize=11, textColor=_NAVY, spaceBefore=4, spaceAfter=3)
    return Paragraph(text, style)


def _body(text: str, size: int = 9) -> Paragraph:
    style = ParagraphStyle("b", fontName=_FONT, fontSize=size, leading=13, spaceAfter=2)
    return Paragraph(text, style)


def _info_table(data: list[list]) -> Table:
    t = Table(data, colWidths=[60*mm, 110*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), _FONT),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_LIGHT_GREY, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _fmt_address(application) -> str:
    parts = filter(None, [
        application.address_line,
        application.city,
        application.state,
        application.pincode,
    ])
    return ", ".join(parts) or "—"

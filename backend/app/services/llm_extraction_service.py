"""
LLM Field Extraction — Phase 6 of the blueprint.

Q1–Q8 JSON-mode Gemini prompts, confidence scoring, consistency check.

Confidence thresholds (blueprint):
  0.90–1.00 → green  (auto-fill, high trust)
  0.70–0.89 → amber  (auto-fill, flag for review)
  0.50–0.69 → orange (soft flag)
  0.00–0.49 → HITL queue
  null       → follow-up question needed
"""
import logging
import re
from datetime import date

from app.services.llm_service import call_json, call_text

logger = logging.getLogger(__name__)

# ── Questions config ────────────────────────────────────────────────────────────

QUESTIONS = [
    {
        "index": 0,
        "text": "Please tell me your full name and date of birth.",
        "fields": ["full_name", "dob"],
    },
    {
        "index": 1,
        "text": "What is your home address, including your PIN code?",
        "fields": ["address_line", "city", "state", "pincode"],
    },
    {
        "index": 2,
        "text": "Are you salaried, self-employed, or a business owner?",
        "fields": ["employment_type"],
    },
    {
        "index": 3,
        "text": "What is your monthly take-home income or revenue?",
        "fields": ["monthly_income"],
    },
    {
        "index": 4,
        "text": "What is the name of your employer or business?",
        "fields": ["employer_name", "job_tenure_years"],
    },
    {
        "index": 5,
        "text": "What is the purpose of this loan?",
        "fields": ["loan_purpose"],
    },
    {
        "index": 6,
        "text": "Over how many months would you prefer to repay the loan?",
        "fields": ["preferred_tenure_months"],
    },
    {
        "index": 7,
        "text": "Do you have any existing loans? If yes, what is your total EMI per month?",
        "fields": ["has_existing_loans", "existing_emi_monthly"],
    },
]


# ── Per-question extraction prompts ────────────────────────────────────────────

_Q_PROMPTS = {
    0: """
Extract the applicant's full name and date of birth from the following spoken response.

Transcript: "{transcript}"

Rules:
- full_name: complete name as spoken; normalize capitalisation
- dob: convert any format to YYYY-MM-DD; null if not mentioned
- Each field must have a confidence score 0.0–1.0 reflecting extraction certainty

Return JSON:
{{
  "full_name": string | null,
  "full_name_confidence": number,
  "dob": "YYYY-MM-DD" | null,
  "dob_confidence": number
}}
""",

    1: """
Extract the applicant's home address from the following spoken response.

Transcript: "{transcript}"

Rules:
- address_line: house/flat/street/area
- city: city name; normalize spelling
- state: Indian state name; normalize spelling
- pincode: exactly 6 digits; null if not mentioned
- Confidence per field reflects extraction certainty

Return JSON:
{{
  "address_line": string | null,
  "address_confidence": number,
  "city": string | null,
  "city_confidence": number,
  "state": string | null,
  "state_confidence": number,
  "pincode": string | null,
  "pincode_confidence": number
}}
""",

    2: """
Classify the applicant's employment type from the following spoken response.

Transcript: "{transcript}"

Rules:
- employment_type must be exactly one of: "salaried", "self_employed", "business_owner"
- Map common variations: "job" → salaried, "freelance" → self_employed, "shop" → business_owner

Return JSON:
{{
  "employment_type": "salaried" | "self_employed" | "business_owner" | null,
  "employment_type_confidence": number
}}
""",

    3: """
Extract the applicant's monthly income from the following spoken response.

Transcript: "{transcript}"

Rules:
- monthly_income: numerical value in Indian Rupees
- Normalize spoken amounts: "55 to 60 thousand" → 57500, "around 1 lakh" → 100000
- Income must be a number, not null if clearly stated

Return JSON:
{{
  "monthly_income": number | null,
  "monthly_income_confidence": number,
  "income_normalized_from": string
}}
""",

    4: """
Extract the employer or business name and job tenure from the following spoken response.

Transcript: "{transcript}"

Rules:
- employer_name: company or business name; clean up informal references
- job_tenure_years: number of years in current job/business; null if not mentioned
- If applicant says "6 years", job_tenure_years = 6.0

Return JSON:
{{
  "employer_name": string | null,
  "employer_name_confidence": number,
  "job_tenure_years": number | null,
  "job_tenure_confidence": number
}}
""",

    5: """
Extract the loan purpose from the following spoken response.

Transcript: "{transcript}"

Rules:
- loan_purpose: normalize to one of: "home_renovation", "medical", "education", "wedding",
  "vehicle", "travel", "debt_consolidation", "business", "personal", "other"
- Use context to best match; "marriage" → "wedding", "hospital" → "medical"

Return JSON:
{{
  "loan_purpose": string | null,
  "loan_purpose_confidence": number,
  "loan_purpose_raw": string
}}
""",

    6: """
Extract the preferred repayment tenure from the following spoken response.

Transcript: "{transcript}"

Rules:
- preferred_tenure_months: integer number of months; "2 years" → 24, "18 months" → 18, "as short as possible" → 12
- null if not clearly stated

Return JSON:
{{
  "preferred_tenure_months": number | null,
  "preferred_tenure_confidence": number
}}
""",

    7: """
Extract existing loan information from the following spoken response.

Transcript: "{transcript}"

Rules:
- has_existing_loans: true/false; null if ambiguous
- existing_emi_monthly: total monthly EMI in INR across all loans; 0 if no loans
- Normalize: "around 8000" → 8000, "8 to 9 thousand" → 8500

Return JSON:
{{
  "has_existing_loans": boolean | null,
  "has_existing_loans_confidence": number,
  "existing_emi_monthly": number | null,
  "existing_emi_confidence": number
}}
""",
}


# ── Extraction logic ────────────────────────────────────────────────────────────

async def extract_question_fields(question_index: int, transcript: str) -> dict:
    """
    Run Gemini extraction for a single Q&A transcript.
    Returns extracted fields + confidence scores.
    """
    if not transcript.strip():
        return {"error": "empty_transcript", "confidence": 0.0}

    prompt = _Q_PROMPTS[question_index].format(transcript=transcript)
    try:
        result = await call_json(prompt)
        result["question_index"] = question_index
        result["transcript"] = transcript
        return result
    except ValueError as e:
        logger.error("Q%d extraction failed: %s", question_index, e)
        return {"question_index": question_index, "error": str(e), "confidence": 0.0}


def _get_confidence_values(extracted_all: list[dict]) -> list[float]:
    """Pull all confidence values from all extracted question results."""
    confidences = []
    for q in extracted_all:
        for k, v in q.items():
            if k.endswith("_confidence") and isinstance(v, (int, float)):
                confidences.append(float(v))
    return confidences


def merge_extracted_fields(extracted_all: list[dict]) -> dict:
    """
    Merge all Q1–Q8 extraction results into a single flat application dict.
    Returns merged fields + extraction_confidence_avg + hitl_fields list.
    """
    merged = {}
    hitl_fields = []

    # Q0
    q0 = extracted_all[0] if len(extracted_all) > 0 else {}
    merged["full_name"] = q0.get("full_name")
    merged["dob"] = q0.get("dob")

    # Q1
    q1 = extracted_all[1] if len(extracted_all) > 1 else {}
    merged["address_line"] = q1.get("address_line")
    merged["city"] = q1.get("city")
    merged["state"] = q1.get("state")
    merged["pincode"] = q1.get("pincode")

    # Q2
    q2 = extracted_all[2] if len(extracted_all) > 2 else {}
    merged["employment_type"] = q2.get("employment_type")

    # Q3
    q3 = extracted_all[3] if len(extracted_all) > 3 else {}
    merged["monthly_income"] = q3.get("monthly_income")

    # Q4
    q4 = extracted_all[4] if len(extracted_all) > 4 else {}
    merged["employer_name"] = q4.get("employer_name")
    merged["job_tenure_years"] = q4.get("job_tenure_years")

    # Q5
    q5 = extracted_all[5] if len(extracted_all) > 5 else {}
    merged["loan_purpose"] = q5.get("loan_purpose")

    # Q6
    q6 = extracted_all[6] if len(extracted_all) > 6 else {}
    merged["preferred_tenure_months"] = q6.get("preferred_tenure_months")

    # Q7
    q7 = extracted_all[7] if len(extracted_all) > 7 else {}
    merged["has_existing_loans"] = q7.get("has_existing_loans")
    merged["existing_emi_monthly"] = q7.get("existing_emi_monthly") or 0.0

    confidences = _get_confidence_values(extracted_all)
    extraction_confidence_avg = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    # Flag fields below HITL threshold (< 0.50)
    for q in extracted_all:
        for k, v in q.items():
            if k.endswith("_confidence") and isinstance(v, (int, float)) and v < 0.50:
                field_name = k.replace("_confidence", "")
                hitl_fields.append(field_name)

    merged["extraction_confidence_avg"] = extraction_confidence_avg
    merged["hitl_required_fields"] = list(set(hitl_fields))
    return merged


# ── Consistency check ───────────────────────────────────────────────────────────

async def run_consistency_check(merged_fields: dict, estimated_age: float | None) -> dict:
    """
    Cross-field consistency check.
    Returns inconsistency_score (0.0–1.0) + flagged_conflicts list.
    """
    prompt = f"""
You are a loan application validator. Check the following extracted fields for consistency.

Application data:
{_format_for_prompt(merged_fields)}
{"Estimated age from video: " + str(round(estimated_age, 1)) if estimated_age else ""}

Check for:
1. DOB vs estimated age — are they consistent? (tolerance: ±5 years)
2. Monthly income vs existing EMI — FOIR (EMI/income) should be < 80% to be plausible
3. Requested amount vs income — loan_to_income ratio > 20× is suspicious
4. Employment type vs employer_name — do they make sense together?
5. City/state consistency — does the state match the city?

For each issue found, assign severity: "low" | "medium" | "high"
inconsistency_score: 0.0 (fully consistent) to 1.0 (very inconsistent)

Return JSON:
{{
  "inconsistency_score": number,
  "flagged_conflicts": [
    {{"field": string, "issue": string, "severity": "low"|"medium"|"high"}}
  ]
}}
"""
    try:
        result = await call_json(prompt)
        result["inconsistency_score"] = float(result.get("inconsistency_score", 0.0))
        return result
    except ValueError:
        return {"inconsistency_score": 0.0, "flagged_conflicts": []}


def _format_for_prompt(fields: dict) -> str:
    lines = []
    for k, v in fields.items():
        if not k.startswith("hitl") and not k.startswith("extraction"):
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ── Consent validation ──────────────────────────────────────────────────────────

async def validate_consent(transcript: str) -> dict:
    """
    Validate verbal consent from transcript.
    Returns {is_valid, consent_confidence, normalized_response}.
    """
    prompt = f"""
The following is a transcription of a customer's verbal response to a consent request for a video KYC loan application.

Consent text shown to customer:
"I give my consent to Poonawalla Fincorp to record this video session, use my personal information
for loan assessment, and verify my identity. I confirm I am providing this consent voluntarily."

Customer's response: "{transcript}"

Determine if the customer has given valid consent. Accept: "I agree", "yes", "haan", "theek hai",
affirmative nods captured as speech, or any clear affirmative response in Hindi or English.
Reject: silence, unclear response, "no", "nahi", explicit refusal.

Return JSON:
{{
  "is_valid": boolean,
  "consent_confidence": number,
  "normalized_response": string,
  "language_detected": "en" | "hi" | "other"
}}
"""
    try:
        result = await call_json(prompt)
        return {
            "is_valid": bool(result.get("is_valid", False)),
            "consent_confidence": float(result.get("consent_confidence", 0.0)),
            "normalized_response": result.get("normalized_response", transcript),
            "language_detected": result.get("language_detected", "en"),
        }
    except ValueError:
        return {"is_valid": False, "consent_confidence": 0.0, "normalized_response": transcript}


# ── SHAP plain-English reasons ──────────────────────────────────────────────────

async def shap_to_plain_english(
    top_positive: list[str],
    top_negative: list[str],
    application_context: dict,
) -> list[str]:
    """
    Convert SHAP feature names to customer-facing plain English sentences.
    Used in the offer PDF and approved screen.
    """
    # top_negative = features that lowered PD = actual approval factors
    # top_positive = features that raised PD = risk drivers (not approval reasons)
    approval_factors = top_negative or top_positive
    if not approval_factors:
        return []

    prompt = f"""
A loan application was approved by a risk model. The top factors that helped approval are:
{approval_factors}

Application context:
- Monthly income: ₹{application_context.get('monthly_income', 'unknown')}
- Credit score: {application_context.get('credit_score', 'unknown')}
- Employment: {application_context.get('employment_type', 'unknown')} at {application_context.get('employer_name', 'unknown')}

Write exactly 3 short, friendly sentences explaining WHY the application was approved.
Use simple language a non-finance person understands. Do not mention technical feature names.
Keep each sentence under 15 words.

Return JSON:
{{
  "reasons": ["sentence 1", "sentence 2", "sentence 3"]
}}
"""
    try:
        result = await call_json(prompt)
        return result.get("reasons", [])[:3]
    except ValueError:
        return ["Your application met our eligibility criteria."]

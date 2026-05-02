"""
Decision Engine — Phase 8 (3 layers).

Layer 1: Hard rules from policy_rules.yaml
Layer 2: LightGBM 35-feature ML scoring
Layer 3: Deterministic offer matrix lookup + EMI calculation
"""
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import yaml

logger = logging.getLogger(__name__)

_POLICY_PATH = Path("config/policy_rules.yaml")
_MODEL_PATH = Path("models/risk_model_v1.lgb")
_FEATURES_PATH = Path("models/features.json")
_THRESHOLDS_PATH = Path("models/thresholds.json")
_CALIBRATOR_PATH = Path("models/calibrator.pkl")

_POLICY_VER = "v1.0"
_MODEL_VER = "v1.0"
_OFFER_MATRIX_VER = "v1.0"

_EXCLUDED_PINCODES: set[str] = set()


# ── Model singletons ────────────────────────────────────────────────────────────

_lgb_model = None
_calibrator = None
_feature_names: list[str] = []
_thresholds: dict = {}


def _load_models():
    global _lgb_model, _calibrator, _feature_names, _thresholds

    import json
    if _FEATURES_PATH.exists():
        with open(_FEATURES_PATH) as f:
            _feature_names = json.load(f)
    else:
        _feature_names = _default_feature_order()

    if _THRESHOLDS_PATH.exists():
        with open(_THRESHOLDS_PATH) as f:
            _thresholds = json.load(f)
    else:
        _thresholds = {"LOW": 0.15, "MEDIUM_LOW": 0.25, "MEDIUM_HIGH": 0.40, "HIGH": 0.50}

    if _MODEL_PATH.exists():
        import lightgbm as lgb
        import pickle
        _lgb_model = lgb.Booster(model_file=str(_MODEL_PATH))
        logger.info("LightGBM model loaded from %s", _MODEL_PATH)
        if _CALIBRATOR_PATH.exists():
            try:
                with open(_CALIBRATOR_PATH, "rb") as f:
                    _calibrator = pickle.load(f)
            except Exception as e:
                logger.warning("Calibrator load failed (%s) — using raw LightGBM score", e)
    else:
        logger.warning("LightGBM model not found — using dummy PD=0.05")


_load_models()


# ── Layer 1: Hard rules ─────────────────────────────────────────────────────────

def run_hard_rules(features: dict) -> dict:
    """
    Evaluate all 8 hard rules from policy_rules.yaml.
    Returns {passed: bool, failing_rule: str|None, failing_rule_reason: str|None}.
    """
    with open(_POLICY_PATH) as f:
        policy = yaml.safe_load(f)

    for rule in policy["rules"]:
        rule_id = rule["id"]
        field = rule["field"]
        operator = rule["operator"]
        threshold = rule.get("value")
        reason = rule["reason"]

        value = features.get(field)

        if value is None:
            # Missing field — skip (don't hard-fail on missing data; let ML handle it)
            continue

        failed = False
        if operator == "gte":
            failed = float(value) < float(threshold)
        elif operator == "lte":
            failed = float(value) > float(threshold)
        elif operator == "not_in_exclusion_list":
            failed = str(value) in _EXCLUDED_PINCODES

        if failed:
            logger.info("Hard rule failed: %s (value=%s threshold=%s)", rule_id, value, threshold)
            return {"passed": False, "failing_rule": rule_id, "failing_rule_reason": reason}

    return {"passed": True, "failing_rule": None, "failing_rule_reason": None}


# ── Layer 2: LightGBM ──────────────────────────────────────────────────────────

def assemble_feature_vector(features: dict) -> np.ndarray:
    """Build numpy array in exact order from features.json."""
    vec = []
    for name in _feature_names:
        val = features.get(name, 0.0)
        if val is None:
            val = 0.0
        vec.append(float(val))
    return np.array(vec, dtype=np.float32)


def run_ml_scoring(features: dict) -> dict:
    """
    Run LightGBM inference.
    Returns pd_score, risk_band, eligible, shap_values, top features.
    """
    feature_vec = assemble_feature_vector(features)

    if _lgb_model is None:
        # Dummy model until Moksh delivers
        pd_score = 0.05
    else:
        raw_score = float(_lgb_model.predict(feature_vec.reshape(1, -1))[0])
        if _calibrator is not None:
            try:
                # IsotonicRegression uses predict(), not predict_proba()
                pd_score = float(_calibrator.predict([raw_score])[0])
                pd_score = max(0.0, min(1.0, pd_score))
            except Exception as e:
                logger.warning("Calibrator prediction failed (%s) — using raw score", e)
                pd_score = raw_score
        else:
            pd_score = raw_score

    risk_band = _pd_to_risk_band(pd_score)
    eligible = risk_band in ("LOW", "MEDIUM_LOW", "MEDIUM_HIGH")

    # SHAP values
    shap_values = {}
    top_positive = []
    top_negative = []
    if _lgb_model is not None:
        try:
            import shap
            explainer = shap.TreeExplainer(_lgb_model)
            sv = explainer.shap_values(feature_vec.reshape(1, -1))[0]
            shap_values = {name: round(float(sv[i]), 6) for i, name in enumerate(_feature_names)}
            sorted_sv = sorted(shap_values.items(), key=lambda x: x[1], reverse=True)
            top_positive = [k for k, v in sorted_sv if v > 0][:3]
            top_negative = [k for k, v in sorted_sv if v < 0][:3]
        except Exception as e:
            logger.warning("SHAP computation failed: %s", e)

    return {
        "pd_score": round(pd_score, 6),
        "risk_band": risk_band,
        "eligible": eligible,
        "shap_values": shap_values,
        "top_positive_features": top_positive,
        "top_negative_features": top_negative,
        "model_version": _MODEL_VER,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def _pd_to_risk_band(pd: float) -> str:
    t = _thresholds
    if pd < t.get("LOW", 0.03):
        return "LOW"
    elif pd < t.get("MEDIUM_LOW", 0.06):
        return "MEDIUM_LOW"
    elif pd < t.get("MEDIUM_HIGH", 0.10):
        return "MEDIUM_HIGH"
    elif pd < t.get("HIGH", 0.15):
        return "HIGH"
    return "VERY_HIGH"


# ── Layer 3: Offer matrix ───────────────────────────────────────────────────────

# Deterministic offer table: risk_band → income_bucket → rate%
# LLM never touches these numbers.
# Rates sourced from real CIBIL-band lending benchmarks (India, 2024).
# Risk bands map approximately: LOW=800+, MEDIUM_LOW=750-799, MEDIUM_HIGH=700-749,
# HIGH=650-699 (HITL), VERY_HIGH=<650 (Decline).
_OFFER_TABLE = {
    "personal_loan": {
        "LOW":         {"rate": 10.50, "processing_fee": 1.0, "max_multiplier": 22},
        "MEDIUM_LOW":  {"rate": 11.75, "processing_fee": 1.5, "max_multiplier": 18},
        "MEDIUM_HIGH": {"rate": 14.50, "processing_fee": 2.0, "max_multiplier": 14},
        "HIGH":        None,
        "VERY_HIGH":   None,
    },
    "vehicle_loan": {
        "LOW":         {"rate":  8.65, "processing_fee": 0.5, "max_multiplier": 25},
        "MEDIUM_LOW":  {"rate":  9.25, "processing_fee": 1.0, "max_multiplier": 20},
        "MEDIUM_HIGH": {"rate": 10.15, "processing_fee": 1.5, "max_multiplier": 15},
        "HIGH":        None,
        "VERY_HIGH":   None,
    },
    "education_loan": {
        "LOW":         {"rate":  9.00, "processing_fee": 0.5, "max_multiplier": 30},
        "MEDIUM_LOW":  {"rate": 10.35, "processing_fee": 1.0, "max_multiplier": 25},
        "MEDIUM_HIGH": {"rate": 11.50, "processing_fee": 1.5, "max_multiplier": 20},
        "HIGH":        None,
        "VERY_HIGH":   None,
    },
    "home_loan": {
        "LOW":         {"rate":  8.25, "processing_fee": 0.5, "max_multiplier": 60},
        "MEDIUM_LOW":  {"rate":  8.60, "processing_fee": 0.5, "max_multiplier": 50},
        "MEDIUM_HIGH": {"rate":  9.00, "processing_fee": 1.0, "max_multiplier": 40},
        "HIGH":        None,
        "VERY_HIGH":   None,
    },
    "business_loan": {
        "LOW":         {"rate": 14.25, "processing_fee": 1.5, "max_multiplier": 25},
        "MEDIUM_LOW":  {"rate": 17.00, "processing_fee": 2.0, "max_multiplier": 20},
        "MEDIUM_HIGH": {"rate": 20.50, "processing_fee": 2.5, "max_multiplier": 15},
        "HIGH":        None,
        "VERY_HIGH":   None,
    },
}

# Maps loan_purpose string → offer table key
_PURPOSE_TO_CATEGORY = {
    "home_loan":          "home_loan",
    "home_renovation":    "personal_loan",
    "education":          "education_loan",
    "vehicle":            "vehicle_loan",
    "medical":            "personal_loan",
    "wedding":            "personal_loan",
    "travel":             "personal_loan",
    "debt_consolidation": "personal_loan",
    "business":           "business_loan",
    "personal":           "personal_loan",
    "other":              "personal_loan",
}

_TENURE_OPTIONS = [12, 24, 36]  # months shown in offer


def compute_offer(
    risk_band: str,
    monthly_income: float,
    existing_emi: float = 0,
    preferred_tenure_months: int | None = None,
    loan_purpose: str | None = None,
) -> dict | None:
    category = _PURPOSE_TO_CATEGORY.get(loan_purpose or "", "personal_loan")
    offer_params = _OFFER_TABLE[category].get(risk_band)
    if not offer_params:
        return None

    rate_annual = offer_params["rate"]
    rate_monthly = rate_annual / 12 / 100

    # Honour the user's preferred tenure if given, else default to 24 months
    preferred = int(preferred_tenure_months) if preferred_tenure_months else 24
    recommended_tenure = min(_TENURE_OPTIONS, key=lambda t: abs(t - preferred))

    # Approved amount from income × risk-band multiplier
    income_based_amount = monthly_income * offer_params["max_multiplier"]

    # Min-salary check: monthly_income ≥ (existing_emi + new_emi) × 2
    # → max affordable EMI = monthly_income / 2 − existing_emi
    max_affordable_emi = monthly_income / 2 - existing_emi
    if max_affordable_emi <= 0:
        return None  # existing obligations already exceed 50% of income

    # Cap by affordability for recommended tenure
    if rate_monthly > 0:
        max_by_affordability = (
            max_affordable_emi
            * ((1 + rate_monthly) ** recommended_tenure - 1)
            / (rate_monthly * (1 + rate_monthly) ** recommended_tenure)
        )
    else:
        max_by_affordability = max_affordable_emi * recommended_tenure

    approved_amount = min(income_based_amount, max_by_affordability)
    approved_amount = max(10000, round(approved_amount / 1000) * 1000)

    emi_options = []
    for tenure in _TENURE_OPTIONS:
        if rate_monthly > 0:
            emi = approved_amount * rate_monthly * (1 + rate_monthly) ** tenure / ((1 + rate_monthly) ** tenure - 1)
        else:
            emi = approved_amount / tenure
        total_payable = emi * tenure
        emi_options.append({
            "tenure_months": tenure,
            "emi_amount": round(emi, 2),
            "total_payable": round(total_payable, 2),
            "total_interest_inr": round(total_payable - approved_amount, 2),
        })

    return {
        "approved_amount": approved_amount,
        "interest_rate": rate_annual,
        "loan_category": category,
        "recommended_tenure_months": recommended_tenure,
        "emi_options": emi_options,
        "processing_fee_pct": offer_params["processing_fee"],
        "offer_matrix_version": _OFFER_MATRIX_VER,
        "offer_valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


# ── 35-feature assembly helper ─────────────────────────────────────────────────

def build_35_features(
    application: dict,
    session: dict,
    customer: dict,
    history_features: dict,
) -> dict:
    """
    Assemble all 35 features into a flat dict keyed by exact feature names.
    References: blueprint §8, fixed model I/O spec §12.
    """
    monthly_income = float(application.get("monthly_income") or 0)
    existing_emi = float(application.get("existing_emi_monthly") or 0)
    credit_score = float(customer.get("credit_score") or 0)
    total_outstanding = float(customer.get("total_outstanding_inr") or 0)

    foir_ratio = existing_emi / monthly_income if monthly_income > 0 else 0
    dti = (existing_emi * 12) / (monthly_income * 12) if monthly_income > 0 else 0

    # post_loan_foir uses existing obligations only (loan amount unknown pre-decision)
    post_loan_foir = foir_ratio
    min_required_salary = existing_emi * 2

    emp_type_map = {"salaried": 1, "self_employed": 2, "business_owner": 3}
    emp_type_enc = emp_type_map.get(application.get("employment_type"), 0)

    loan_purpose_map = {
        "home_renovation": 1, "medical": 2, "education": 3, "wedding": 4,
        "vehicle": 5, "travel": 6, "debt_consolidation": 7, "business": 8,
        "personal": 9, "other": 10,
    }
    loan_purpose_enc = loan_purpose_map.get(application.get("loan_purpose"), 0)

    tenure_yrs = float(application.get("job_tenure_years") or 0)
    employer_tier = _classify_employer_tier(application.get("employer_name") or "")

    return {
        # Bureau (5)
        "credit_score": credit_score,
        "dpd_12m": float(customer.get("dpd_12m") or 0),
        "dpd_24m": float(customer.get("dpd_24m") or 0),
        "active_loans_count": float(customer.get("active_loans_count") or 0),
        "total_outstanding_inr": total_outstanding,
        # Income & Employment (4)
        "monthly_income": monthly_income,
        "employment_type": emp_type_enc,
        "employer_tier": employer_tier,
        "job_tenure_years": tenure_yrs,
        # Loan Request (4)
        "requested_amount": 0,
        "loan_to_income_ratio": 0,
        "preferred_tenure_months": float(application.get("preferred_tenure_months") or 24),
        "loan_purpose_encoded": loan_purpose_enc,
        "loan_purpose": application.get("loan_purpose"),
        # Liabilities (4)
        "existing_emi_monthly": existing_emi,
        "total_obligations": round(existing_emi, 2),
        "foir_ratio": round(foir_ratio, 4),
        "debt_to_income": round(dti, 4),
        # Post-loan affordability (not model features — used by hard rules only)
        "post_loan_foir": round(post_loan_foir, 4),
        "min_required_salary": round(min_required_salary, 2),
        # Pre-session Scores (3)
        "geo_risk_score": float(session.get("geo_risk_score") or 0),
        "ip_risk_score": float(session.get("ip_risk_score") or 0),
        "device_risk_score": float(session.get("device_risk_score") or 0),
        # CV Signals (3)
        "liveness_score": float(session.get("liveness_score") or 0),
        "age_consistency_score": float(session.get("age_consistency_score") or 0.5),
        "face_confidence_score": float(session.get("face_confidence") or 0),
        # Session Behavior (3)
        "avg_response_latency_ms": float(session.get("avg_response_latency_ms") or 0),
        "hesitation_count": float(session.get("hesitation_count") or 0),
        "question_retry_count": float(session.get("question_retry_count") or 0),
        # LLM Quality (3)
        "extraction_confidence_avg": float(application.get("extraction_confidence_avg") or 0),
        "inconsistency_score": float(application.get("inconsistency_score") or 0),
        "consent_confidence": float(session.get("consent_confidence") or 0),
        # Prior App History (7)
        "prior_applications_count": float(history_features.get("prior_applications_count") or 0),
        "prior_rejections_count": float(history_features.get("prior_rejections_count") or 0),
        "days_since_last_app": float(history_features.get("days_since_last_app") or 999),
        "last_outcome_encoded": float(history_features.get("last_outcome_encoded") or 0),
        "prior_risk_band_encoded": float(history_features.get("prior_risk_band_encoded") or 0),
        "prior_loan_performance_encoded": float(history_features.get("prior_loan_performance_encoded") or 0),
        "application_velocity_30d": float(history_features.get("application_velocity_30d") or 0),
    }


def _classify_employer_tier(employer_name: str) -> float:
    """
    Tier 1 (score 3): Fortune 500, PSU, MNC
    Tier 2 (score 2): Mid-size known company
    Tier 3 (score 1): SME, unknown
    """
    if not employer_name:
        return 1.0
    name_lower = employer_name.lower()
    tier1_keywords = ["tcs", "infosys", "wipro", "hcl", "accenture", "ibm", "google",
                      "microsoft", "amazon", "reliance", "hdfc", "icici", "sbi", "lic"]
    if any(k in name_lower for k in tier1_keywords):
        return 3.0
    return 2.0


def _default_feature_order() -> list[str]:
    return [
        "credit_score", "dpd_12m", "dpd_24m", "active_loans_count", "total_outstanding_inr",
        "monthly_income", "employment_type", "employer_tier", "job_tenure_years",
        "requested_amount", "loan_to_income_ratio", "preferred_tenure_months", "loan_purpose_encoded",
        "existing_emi_monthly", "total_obligations", "foir_ratio", "debt_to_income",
        "geo_risk_score", "ip_risk_score", "device_risk_score",
        "liveness_score", "age_consistency_score", "face_confidence_score",
        "avg_response_latency_ms", "hesitation_count", "question_retry_count",
        "extraction_confidence_avg", "inconsistency_score", "consent_confidence",
        "prior_applications_count", "prior_rejections_count", "days_since_last_app",
        "last_outcome_encoded", "prior_risk_band_encoded", "prior_loan_performance_encoded",
        "application_velocity_30d",
    ]

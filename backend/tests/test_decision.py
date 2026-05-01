"""
Tests for the 3-layer decision engine.
  Layer 1: Hard rules
  Layer 2: LightGBM (dummy model)
  Layer 3: Offer matrix + EMI calculation
"""
import pytest
from app.services.decision_service import (
    run_hard_rules, run_ml_scoring, compute_offer,
    build_35_features, assemble_feature_vector,
)
from tests.conftest import RAMESH, RAMESH_35_FEATURES


# ── Layer 1: Hard rules ────────────────────────────────────────────────────────

def _base_features(**overrides):
    f = {
        "estimated_age": 34.0,
        "monthly_income": 58000.0,
        "credit_score": 742.0,
        "dpd_24m": 0.0,
        "foir_ratio": 0.14,
        "pincode": "411027",
        "liveness_score": 0.92,
    }
    f.update(overrides)
    return f


def test_hard_rules_all_pass():
    result = run_hard_rules(_base_features())
    assert result["passed"] is True
    assert result["failing_rule"] is None


def test_hard_rules_min_age_fail():
    result = run_hard_rules(_base_features(estimated_age=19.0))
    assert result["passed"] is False
    assert result["failing_rule"] == "min_age"


def test_hard_rules_max_age_fail():
    result = run_hard_rules(_base_features(estimated_age=67.0))
    assert result["passed"] is False
    assert result["failing_rule"] == "max_age"


def test_hard_rules_min_income_fail():
    result = run_hard_rules(_base_features(monthly_income=12000.0))
    assert result["passed"] is False
    assert result["failing_rule"] == "min_income"


def test_hard_rules_bureau_fail():
    result = run_hard_rules(_base_features(credit_score=600.0))
    assert result["passed"] is False
    assert result["failing_rule"] == "bureau_score"


def test_hard_rules_dpd_fail():
    result = run_hard_rules(_base_features(dpd_24m=95.0))
    assert result["passed"] is False
    assert result["failing_rule"] == "dpd_24m"


def test_hard_rules_foir_fail():
    result = run_hard_rules(_base_features(foir_ratio=0.56))
    assert result["passed"] is False
    assert result["failing_rule"] == "foir"


def test_hard_rules_liveness_fail():
    result = run_hard_rules(_base_features(liveness_score=0.30))
    assert result["passed"] is False
    assert result["failing_rule"] == "liveness"


def test_hard_rules_missing_field_does_not_block():
    """Missing non-critical fields should not hard-fail."""
    result = run_hard_rules({"estimated_age": 30.0, "monthly_income": 20000.0,
                              "credit_score": 700.0, "dpd_24m": 0.0,
                              "foir_ratio": 0.20, "liveness_score": 0.85})
    assert result["passed"] is True


# ── Layer 2: ML scoring (dummy model) ─────────────────────────────────────────

def test_ml_scoring_returns_required_keys():
    result = run_ml_scoring(RAMESH_35_FEATURES)
    assert "pd_score" in result
    assert "risk_band" in result
    assert "eligible" in result
    assert "model_version" in result
    assert "shap_values" in result


def test_dummy_model_ramesh_is_low_risk():
    result = run_ml_scoring(RAMESH_35_FEATURES)
    # Dummy model always returns PD=0.05 → MEDIUM_LOW
    assert result["pd_score"] == pytest.approx(0.05, abs=0.001)
    assert result["risk_band"] in ("LOW", "MEDIUM_LOW", "MEDIUM_HIGH")
    assert result["eligible"] is True


def test_risk_band_thresholds():
    from app.services.decision_service import _pd_to_risk_band
    assert _pd_to_risk_band(0.01) == "LOW"
    assert _pd_to_risk_band(0.04) == "MEDIUM_LOW"
    assert _pd_to_risk_band(0.08) == "MEDIUM_HIGH"
    assert _pd_to_risk_band(0.12) == "HIGH"
    assert _pd_to_risk_band(0.20) == "VERY_HIGH"


# ── Layer 3: Offer matrix ──────────────────────────────────────────────────────

def test_offer_low_risk():
    offer = compute_offer(
        risk_band="LOW",
        monthly_income=58000,
        requested_amount=400000,
        max_amount=500000,
    )
    assert offer is not None
    assert offer["approved_amount"] > 0
    assert offer["approved_amount"] <= 400000
    assert offer["interest_rate"] == pytest.approx(10.5)
    assert len(offer["emi_options"]) == 3


def test_offer_medium_low_risk():
    offer = compute_offer("MEDIUM_LOW", 58000, 400000, 500000)
    assert offer["interest_rate"] == pytest.approx(12.5)


def test_offer_high_risk_returns_none():
    offer = compute_offer("HIGH", 58000, 400000, 500000)
    assert offer is None


def test_offer_very_high_risk_returns_none():
    offer = compute_offer("VERY_HIGH", 58000, 400000, 500000)
    assert offer is None


def test_offer_respects_income_multiplier():
    """LOW risk: max 20× income. 20 × 15000 = 300000 < requested 400000."""
    offer = compute_offer("LOW", 15000, 400000, 500000)
    assert offer["approved_amount"] <= 300000


def test_offer_respects_max_amount():
    offer = compute_offer("LOW", 200000, 1000000, 300000)
    assert offer["approved_amount"] <= 300000


def test_emi_options_structure():
    offer = compute_offer("LOW", 58000, 400000, 500000)
    for opt in offer["emi_options"]:
        assert "tenure_months" in opt
        assert "emi_inr" in opt
        assert "total_payable_inr" in opt
        assert "total_interest_inr" in opt
        # Interest must be positive for any non-zero rate
        assert opt["total_interest_inr"] > 0


def test_emi_formula_correctness():
    """Verify EMI formula: EMI × tenure ≈ total_payable."""
    offer = compute_offer("LOW", 58000, 400000, 500000)
    for opt in offer["emi_options"]:
        expected = round(opt["emi_inr"] * opt["tenure_months"], 0)
        actual = round(opt["total_payable_inr"], 0)
        assert abs(expected - actual) <= 2   # rounding tolerance


# ── 35-feature assembly ────────────────────────────────────────────────────────

def test_feature_vector_length():
    from app.services.decision_service import _default_feature_order
    vec = assemble_feature_vector(RAMESH_35_FEATURES)
    assert len(vec) == 35
    assert len(_default_feature_order()) == 35


def test_feature_vector_no_nans():
    import numpy as np
    vec = assemble_feature_vector(RAMESH_35_FEATURES)
    assert not np.any(np.isnan(vec))


def test_build_35_features_ramesh():
    app_dict = {
        "monthly_income": RAMESH["monthly_income"],
        "employment_type": RAMESH["employment_type"],
        "employer_name": RAMESH["employer_name"],
        "job_tenure_years": RAMESH["job_tenure_years"],
        "requested_amount": RAMESH["requested_amount"],
        "preferred_tenure_months": RAMESH["preferred_tenure_months"],
        "existing_emi_monthly": RAMESH["existing_emi_monthly"],
        "loan_purpose": RAMESH["loan_purpose"],
        "extraction_confidence_avg": 0.944,
        "inconsistency_score": 0.04,
    }
    session_dict = {
        "geo_risk_score": 0.08, "ip_risk_score": 0.05, "device_risk_score": 0.03,
        "liveness_score": 0.92, "age_consistency_score": 0.89, "face_confidence": 0.95,
        "avg_response_latency_ms": 3200, "hesitation_count": 1, "question_retry_count": 0,
        "consent_confidence": 0.97,
    }
    customer_dict = {
        "credit_score": RAMESH["credit_score"], "dpd_12m": 0, "dpd_24m": 0,
        "active_loans_count": 1, "total_outstanding_inr": 120000,
    }
    history = {
        "prior_applications_count": 1, "prior_rejections_count": 0,
        "days_since_last_app": 180, "last_outcome_encoded": 3,
        "prior_risk_band_encoded": 0, "prior_loan_performance_encoded": 0,
        "application_velocity_30d": 0,
    }
    features = build_35_features(app_dict, session_dict, customer_dict, history)
    assert features["credit_score"] == 742.0
    assert features["monthly_income"] == 58000.0
    assert features["foir_ratio"] == pytest.approx(8000 / 58000, abs=0.001)
    assert features["employer_tier"] == 3.0   # TCS = Tier 1


# ── Ramesh Kumar end-to-end decision ──────────────────────────────────────────

def test_ramesh_full_pipeline():
    """Blueprint §13: Ramesh should get LOW risk, eligible, offer ≈ ₹4,00,000."""
    rules = run_hard_rules({
        "estimated_age": 34.0,
        "monthly_income": 58000.0,
        "credit_score": 742.0,
        "dpd_24m": 0.0,
        "foir_ratio": round(8000 / 58000, 4),
        "pincode": "411027",
        "liveness_score": 0.92,
    })
    assert rules["passed"] is True

    ml = run_ml_scoring(RAMESH_35_FEATURES)
    assert ml["eligible"] is True

    offer = compute_offer("LOW", 58000, 400000, 500000)
    assert offer is not None
    # Approved amount should be exactly what was requested (within income limits)
    assert offer["approved_amount"] == pytest.approx(400000, abs=1000)
    # Rate should be 10.5% for LOW risk
    assert offer["interest_rate"] == pytest.approx(10.5)

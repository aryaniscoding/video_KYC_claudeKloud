import lightgbm as lgb
import numpy as np
import json
import joblib
import pandas as pd

# -----------------------------
# 1. Load Model & Artifacts
# -----------------------------
model = lgb.Booster(model_file="risk_model_v1.lgb")
calibrator = joblib.load("calibrator.pkl")

with open("features.json", "r") as f:
    feature_order = json.load(f)

with open("thresholds.json", "r") as f:
    thresholds = json.load(f)

# -----------------------------
# 2. Risk Band Function
# -----------------------------
def get_risk_band(pd):
    if pd < thresholds["LOW"]:
        return "LOW"
    elif pd < thresholds["MEDIUM_LOW"]:
        return "MEDIUM_LOW"
    elif pd < thresholds["MEDIUM_HIGH"]:
        return "MEDIUM_HIGH"
    elif pd < thresholds["HIGH"]:
        return "HIGH"
    else:
        return "VERY_HIGH"

# -----------------------------
# 3. Prediction Function
# -----------------------------
def predict_risk(input_dict):
    """
    input_dict: dictionary with all 35 features
    """

    # Ensure correct feature order
    X = pd.DataFrame([input_dict])[feature_order]
    print(X.head())

    # Raw prediction
    raw_pred = model.predict(X)

    # Calibrated probability
    pd_score = calibrator.predict_proba(X)[:, 1][0]

    # Risk band
    risk_band = get_risk_band(pd_score)

    return {
        "pd_score": float(pd_score),
        "risk_band": risk_band
    }

# -----------------------------
# 4. Test with Sample Inputs
# -----------------------------
if __name__ == "__main__":

    # Sample input 1 (Low risk)
    sample_1 = {
        "credit_score": 780,
        "dpd_12m": 0,
        "dpd_24m": 1,
        "active_loans_count": 1,
        "total_outstanding_inr": 100000,
        "monthly_income": 80000,
        "employment_type": 1,
        "employer_tier": 1,
        "job_tenure_years": 5,
        "requested_amount": 300000,
        "loan_to_income_ratio": 4,
        "preferred_tenure_months": 36,
        "loan_purpose_encoded": 2,
        "existing_emi_monthly": 10000,
        "total_obligations": 10000,
        "foir_ratio": 0.125,
        "debt_to_income": 0.1,
        "geo_risk_score": 0.2,
        "ip_risk_score": 0.2,
        "device_risk_score": 0.2,
        "liveness_score": 0.95,
        "age_consistency_score": 0.9,
        "face_confidence_score": 0.95,
        "avg_response_latency_ms": 1000,
        "hesitation_count": 0,
        "question_retry_count": 0,
        "extraction_confidence_avg": 0.95,
        "inconsistency_score": 0.1,
        "consent_confidence": 0.95,
        "prior_applications_count": 1,
        "prior_rejections_count": 0,
        "days_since_last_app": 200,
        "last_outcome_encoded": 1,
        "prior_risk_band_encoded": 1,
        "prior_loan_performance_encoded": 1,
        "application_velocity_30d": 0
    }

    # Sample input 2 (High risk)
    sample_2 = {
        "credit_score": 580,
        "dpd_12m": 3,
        "dpd_24m": 5,
        "active_loans_count": 4,
        "total_outstanding_inr": 800000,
        "monthly_income": 30000,
        "employment_type": 2,
        "employer_tier": 3,
        "job_tenure_years": 1,
        "requested_amount": 400000,
        "loan_to_income_ratio": 10,
        "preferred_tenure_months": 60,
        "loan_purpose_encoded": 5,
        "existing_emi_monthly": 15000,
        "total_obligations": 15000,
        "foir_ratio": 0.5,
        "debt_to_income": 0.7,
        "geo_risk_score": 0.7,
        "ip_risk_score": 0.6,
        "device_risk_score": 0.6,
        "liveness_score": 0.8,
        "age_consistency_score": 0.6,
        "face_confidence_score": 0.85,
        "avg_response_latency_ms": 4000,
        "hesitation_count": 4,
        "question_retry_count": 2,
        "extraction_confidence_avg": 0.7,
        "inconsistency_score": 0.7,
        "consent_confidence": 0.8,
        "prior_applications_count": 4,
        "prior_rejections_count": 2,
        "days_since_last_app": 10,
        "last_outcome_encoded": 3,
        "prior_risk_band_encoded": 4,
        "prior_loan_performance_encoded": 2,
        "application_velocity_30d": 4
    }

    print("\n--- Sample 1 ---")
    print(predict_risk(sample_1))

    print("\n--- Sample 2 ---")
    print(predict_risk(sample_2))
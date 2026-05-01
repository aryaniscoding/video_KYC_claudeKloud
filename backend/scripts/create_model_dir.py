"""
Scaffold the models/ directory with placeholder files.
Run this once so Aryan can drop Moksh's deliverables in the right place.

Expected files (drop in backend/models/):
  risk_model_v1.lgb    — LightGBM Booster format
  features.json        — ordered list of 35 feature names
  thresholds.json      — PD cutoffs per risk band
  calibrator.pkl       — sklearn calibration object
  test_inference.py    — Moksh's test script
"""
import json
from pathlib import Path

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

# features.json placeholder — exact order must match Moksh's features.json
FEATURES = [
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

THRESHOLDS = {
    "LOW": 0.15,
    "MEDIUM_LOW": 0.25,
    "MEDIUM_HIGH": 0.40,
    "HIGH": 0.50,
}

features_path = MODELS_DIR / "features.json"
thresholds_path = MODELS_DIR / "thresholds.json"
readme_path = MODELS_DIR / "README.md"

if not features_path.exists():
    features_path.write_text(json.dumps(FEATURES, indent=2))
    print(f"  Created {features_path} (placeholder — replace with Moksh's file)")

if not thresholds_path.exists():
    thresholds_path.write_text(json.dumps(THRESHOLDS, indent=2))
    print(f"  Created {thresholds_path}")

readme_path.write_text("""# models/

Drop Moksh's deliverables here:

| File | Description |
|---|---|
| `risk_model_v1.lgb` | LightGBM Booster — trained risk model |
| `features.json` | Ordered list of 35 feature names (MUST match this repo's order) |
| `thresholds.json` | PD cutoffs: LOW/MEDIUM_LOW/MEDIUM_HIGH/HIGH/VERY_HIGH |
| `calibrator.pkl` | sklearn Platt/isotonic calibration object |
| `test_inference.py` | Moksh's test script with 3 sample inputs |

Until `risk_model_v1.lgb` is present, the system uses a **dummy model** (PD=0.05, risk_band=MEDIUM_LOW).
The dummy is a one-line swap in `app/services/decision_service.py::run_ml_scoring`.
""")
print(f"  Created {readme_path}")
print("\nmodels/ directory ready. Waiting for Moksh's deliverables.")

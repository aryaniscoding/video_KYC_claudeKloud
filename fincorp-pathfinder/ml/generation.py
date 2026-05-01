import numpy as np
import pandas as pd

np.random.seed(42)
n = 10000

# -----------------------------
# 1. Bureau Features
# -----------------------------
credit_score = np.random.normal(680, 80, n).clip(300, 900).astype(int)

dpd_12m = np.random.poisson(1.2, n)
dpd_24m = dpd_12m + np.random.poisson(1.5, n)

active_loans_count = np.random.poisson(2, n)
active_loans_count = np.clip(active_loans_count, 0, 8)

total_outstanding_inr = np.random.randint(50000, 1200000, n)

# -----------------------------
# 2. Income & Employment
# -----------------------------
monthly_income = np.random.randint(15000, 120000, n)

employment_type = np.random.choice(
    [1, 2, 3], n, p=[0.65, 0.25, 0.10]
)

employer_tier = np.random.choice(
    [1, 2, 3, 4], n, p=[0.3, 0.3, 0.25, 0.15]
)

job_tenure_years = np.random.exponential(scale=4, size=n)
job_tenure_years = np.clip(job_tenure_years, 0.5, 15)

# -----------------------------
# 3. Loan Request (DEPENDENT)
# -----------------------------
requested_amount = (monthly_income * np.random.uniform(3, 10, n)).astype(int)

loan_to_income_ratio = requested_amount / monthly_income

preferred_tenure_months = np.random.choice(
    [12, 24, 36, 48, 60], n, p=[0.2, 0.35, 0.25, 0.15, 0.05]
)

loan_purpose_encoded = np.random.randint(0, 9, n)

# -----------------------------
# 4. Liabilities (DEPENDENT)
# -----------------------------
existing_emi_monthly = (monthly_income * np.random.uniform(0.1, 0.5, n)).astype(int)

total_obligations = existing_emi_monthly.copy()

foir_ratio = np.clip(
    (existing_emi_monthly / monthly_income) + np.random.normal(0, 0.05, n),
    0, 1
)

debt_to_income = total_outstanding_inr / (12 * monthly_income)

# -----------------------------
# 5. Pre-session Risk Scores
# -----------------------------
geo_risk_score = np.random.beta(2, 5, n)
ip_risk_score = np.random.beta(2, 5, n)
device_risk_score = np.random.beta(2, 5, n)

# -----------------------------
# 6. CV Signals
# -----------------------------
liveness_score = np.random.uniform(0.75, 1.0, n)
age_consistency_score = np.random.beta(5, 2, n)
face_confidence_score = np.random.uniform(0.75, 1.0, n)

# -----------------------------
# 7. Session Behavior
# -----------------------------
avg_response_latency_ms = np.random.randint(500, 5000, n)
hesitation_count = np.random.poisson(1.5, n)
question_retry_count = np.random.randint(0, 3, n)

# -----------------------------
# 8. LLM Quality
# -----------------------------
extraction_confidence_avg = np.random.beta(5, 2, n)
inconsistency_score = np.random.beta(2, 3, n)
consent_confidence = np.random.beta(6, 2, n)

# -----------------------------
# 9. Prior Application History
# -----------------------------
prior_applications_count = np.random.poisson(2, n)
prior_rejections_count = np.random.poisson(1, n)

days_since_last_app = np.random.exponential(scale=90, size=n).astype(int)
days_since_last_app = np.clip(days_since_last_app, -1, 365)

last_outcome_encoded = np.random.randint(0, 5, n)
prior_risk_band_encoded = np.random.randint(0, 6, n)
prior_loan_performance_encoded = np.random.randint(0, 4, n)

application_velocity_30d = np.random.poisson(1.2, n)

# -----------------------------
# Combine into DataFrame
# -----------------------------
df = pd.DataFrame({
    "credit_score": credit_score,
    "dpd_12m": dpd_12m,
    "dpd_24m": dpd_24m,
    "active_loans_count": active_loans_count,
    "total_outstanding_inr": total_outstanding_inr,

    "monthly_income": monthly_income,
    "employment_type": employment_type,
    "employer_tier": employer_tier,
    "job_tenure_years": job_tenure_years,

    "requested_amount": requested_amount,
    "loan_to_income_ratio": loan_to_income_ratio,
    "preferred_tenure_months": preferred_tenure_months,
    "loan_purpose_encoded": loan_purpose_encoded,

    "existing_emi_monthly": existing_emi_monthly,
    "total_obligations": total_obligations,
    "foir_ratio": foir_ratio,
    "debt_to_income": debt_to_income,

    "geo_risk_score": geo_risk_score,
    "ip_risk_score": ip_risk_score,
    "device_risk_score": device_risk_score,

    "liveness_score": liveness_score,
    "age_consistency_score": age_consistency_score,
    "face_confidence_score": face_confidence_score,

    "avg_response_latency_ms": avg_response_latency_ms,
    "hesitation_count": hesitation_count,
    "question_retry_count": question_retry_count,

    "extraction_confidence_avg": extraction_confidence_avg,
    "inconsistency_score": inconsistency_score,
    "consent_confidence": consent_confidence,

    "prior_applications_count": prior_applications_count,
    "prior_rejections_count": prior_rejections_count,
    "days_since_last_app": days_since_last_app,
    "last_outcome_encoded": last_outcome_encoded,
    "prior_risk_band_encoded": prior_risk_band_encoded,
    "prior_loan_performance_encoded": prior_loan_performance_encoded,
    "application_velocity_30d": application_velocity_30d
})

# -----------------------------
# 10. Target Variable (REALISTIC)
# -----------------------------
risk_score = (
    (credit_score < 650).astype(int) +
    (foir_ratio > 0.45).astype(int) +
    (dpd_24m > 2).astype(int) +
    (inconsistency_score > 0.6).astype(int) +
    (application_velocity_30d > 3).astype(int)
)

# Convert risk_score to probability
prob_default = 1 / (1 + np.exp(-(risk_score - 2)))

# Add noise (critical)
prob_default = np.clip(prob_default + np.random.normal(0, 0.1, n), 0, 1)

# Sample target
df["default"] = np.random.binomial(1, prob_default)

# -----------------------------
# 11. Control Imbalance (~70:30)
# -----------------------------
df_major = df[df["default"] == 0]
df_minor = df[df["default"] == 1]

df_minor = df_minor.sample(int(len(df_major) * 0.4), random_state=42)

df = pd.concat([df_major, df_minor]).sample(frac=1).reset_index(drop=True)

# -----------------------------
# 12. Save Dataset
# -----------------------------
df.to_csv("risk_model_dataset_v1.csv", index=False)

# -----------------------------
# 13. Verification
# -----------------------------
print("Dataset Shape:", df.shape)
print("\nDefault Distribution:\n", df["default"].value_counts(normalize=True))
print("\nSample Data:\n", df.head())
print("\nSummary:\n", df.describe())
<div align="center">

# 🔵 Loan Wizard — Backend
### FastAPI · LangGraph · LightGBM · AWS · Supabase

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.56-FF6B35?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.5-02569B?style=for-the-badge)](https://lightgbm.readthedocs.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)

> The brain of Loan Wizard. Handles all API endpoints, real-time WebSocket sessions,  
> agentic LangGraph decision pipeline, ML inference, and cloud integrations.

</div>

---

## 📁 Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── admin.py            → All admin REST endpoints (9 routes)
│   │   ├── session.py          → Customer session endpoints
│   │   ├── deps.py             → FastAPI dependencies (JWT auth)
│   │   └── ws/
│   │       ├── liveness.py     → WebSocket: AWS Rekognition liveness
│   │       ├── consent.py      → WebSocket: consent recording + STT
│   │       └── qa.py           → WebSocket: 8-question Q&A engine
│   ├── models/
│   │   ├── session.py          → Session + SessionStatus enum (11 states)
│   │   ├── customer.py         → Customer model
│   │   ├── application.py      → Application (LLM-extracted fields)
│   │   ├── decision.py         → Decision + OfferPDF models
│   │   ├── admin.py            → AdminUser model
│   │   └── audit.py            → AuditLog (append-only)
│   ├── schemas/
│   │   ├── admin.py            → Request/response Pydantic schemas
│   │   └── session.py          → Session flow schemas
│   ├── services/
│   │   ├── decision_service.py → Hard rules + 35-feature assembly + offer matrix
│   │   ├── email_service.py    → AWS SES email templates
│   │   ├── liveness_service.py → AWS Rekognition face analysis
│   │   ├── llm_extraction_service.py → Gemini field extraction + consistency
│   │   ├── pdf_service.py      → ReportLab PDF + pikepdf encryption
│   │   ├── s3_service.py       → AWS S3 upload + presigned URLs (SigV4)
│   │   ├── scoring_service.py  → Pre-session geo/IP/device risk scoring
│   │   ├── stt_service.py      → Groq Whisper streaming STT
│   │   ├── history_service.py  → Prior application 7-feature lookup
│   │   └── jwt_service.py      → JWT create + validate
│   ├── orchestration/
│   │   └── graph.py            → LangGraph 8-node agentic pipeline
│   ├── config.py               → Pydantic settings (all env vars)
│   ├── database.py             → SQLAlchemy async engine + session
│   └── main.py                 → FastAPI app + router registration
├── migrations/
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_ip_location_to_sessions.py
│       ├── 003_add_pan_number_to_customers.py
│       ├── 004_add_gender_and_antispoof_to_sessions.py
│       └── 005_add_s3_keys.py
├── models/
│   ├── risk_model_v1.lgb       → LightGBM trained model
│   ├── calibrator.pkl          → IsotonicRegression calibrator
│   ├── features.json           → Feature names (35)
│   └── thresholds.json         → Risk band PD thresholds
├── config/
│   └── policy_rules.yaml       → Hard rules config (hot-reloadable)
├── requirements.txt
└── Dockerfile
```

---

## ⚡ Quick Start

### Option A — Local (direct)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials (see Environment Variables section)

# 4. Run database migrations
alembic upgrade head

# 5. Start development server
uvicorn app.main:app --reload --port 8000

# API available at: http://localhost:8000
# Swagger UI:        http://localhost:8000/docs
# Health check:      http://localhost:8000/health
```

### Option B — Docker

```bash
# Build image
docker build -t loan-wizard-backend .

# Run container
docker run -p 8000:8000 --env-file .env loan-wizard-backend

# Or with docker-compose (includes LiveKit)
docker-compose up
```

---

## 🌐 API Reference

### Authentication

All `/admin/*` endpoints require:
```
Authorization: Bearer <admin_jwt_token>
```

Session endpoints require a session JWT embedded in the URL path token.

---

### REST Endpoints

#### Admin Routes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/login` | Authenticate admin → returns JWT |
| `GET` | `/admin/customers` | List all customers (paginated) |
| `POST` | `/admin/customers` | Create customer (409 if phone exists) |
| `POST` | `/admin/send-link` | Create session + send KYC email |
| `POST` | `/admin/resend-link` | Expire old session, create fresh one |
| `GET` | `/admin/session-status/{jti}` | Full session detail with all signals |
| `GET` | `/admin/hitl-queue` | List sessions in HITL status |
| `POST` | `/admin/hitl/{jti}/decision` | Approve/decline HITL session + email |

#### Customer Session Routes

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/session/{token}` | Validate JWT, compute pre-session risk, return session config |
| `POST` | `/session/{id}/pan` | Store PAN number |
| `GET` | `/session/{id}/offer` | Poll for pipeline result (202 while processing) |
| `GET` | `/offers/{ref_id}/download` | Get fresh presigned PDF URL |
| `GET` | `/health` | Health check |

#### WebSocket Endpoints

| Endpoint | Protocol | Description |
|---|---|---|
| `/ws/liveness/{session_id}` | WSS | Face liveness + anti-spoof via AWS Rekognition |
| `/ws/consent/{session_id}` | WSS | Consent audio recording + Groq STT |
| `/ws/qa/{session_id}` | WSS | 8-question Q&A with streaming STT + Gemini extraction |

---

### Key Request/Response Examples

<details>
<summary><b>POST /admin/customers — Create Customer</b></summary>

**Request:**
```json
{
  "name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "phone": "9876543210",
  "credit_score": 742,
  "product_code": "PL_STANDARD",
  "dpd_12m": 0,
  "dpd_24m": 0,
  "active_loans_count": 1,
  "total_outstanding_inr": 120000
}
```

**Response 201:**
```json
{
  "id": "uuid-here",
  "name": "Ramesh Kumar",
  "email": "ramesh@example.com",
  "phone_last4": "3210",
  "credit_score": 742,
  "created_at": "2026-05-03T10:00:00Z"
}
```

**Response 409 (duplicate phone):**
```json
{
  "detail": {
    "code": "customer_exists",
    "name": "Ramesh Kumar",
    "email": "ramesh@example.com",
    "phone_last4": "3210",
    "pan_number": "ABCDE1234F",
    "credit_score": 742,
    "product_code": "PL_STANDARD",
    "created_at": "2026-04-01T10:00:00Z",
    "id": "uuid-here"
  }
}
```

</details>

<details>
<summary><b>POST /admin/hitl/{id}/decision — HITL Decision</b></summary>

**Request:**
```json
{
  "decision": "decline",
  "notes": "High debt-to-income ratio. Customer has 3 active loans totalling ₹4.5L outstanding."
}
```

**Response 200:**
```json
{
  "status": "ok",
  "new_status": "declined"
}
```

*Side effect: Rejection email sent via AWS SES (FastAPI BackgroundTasks)*

</details>

<details>
<summary><b>GET /session/{id}/offer — Poll for Decision</b></summary>

**Response 202 (still processing):**
```json
{ "processing": true }
```

**Response 200 (approved):**
```json
{
  "status": "approved",
  "approved_amount": 400000,
  "interest_rate": 12.5,
  "risk_band": "LOW",
  "pd_score": 0.024,
  "recommended_tenure_months": 24,
  "emi_options": [
    {"tenure_months": 12, "emi_amount": 35612, "total_interest_inr": 27344, "total_payable": 427344},
    {"tenure_months": 24, "emi_amount": 18841, "total_interest_inr": 52184, "total_payable": 452184},
    {"tenure_months": 36, "emi_amount": 13320, "total_interest_inr": 79520, "total_payable": 479520}
  ],
  "download_url": "https://s3.ap-south-1.amazonaws.com/...(presigned)...",
  "top_positive_features": ["Strong CIBIL score", "Low FOIR ratio", "Stable employment"],
  "top_negative_features": ["Moderate outstanding balance"]
}
```

</details>

---

## 🧠 LangGraph Pipeline

### Node Descriptions

| Node | Purpose | Inputs | Outputs |
|---|---|---|---|
| `form_assembly` | Load all data, build feature vector | session_id, application_id | 35-feature dict, history features |
| `hard_rules` | Evaluate 9 policy rules | feature_vector | pass/fail, failing_rule, reason |
| `ml_scoring` | LightGBM PD score + SHAP | feature_vector | pd_score, risk_band, shap_values |
| `offer_matrix` | Compute personalised offer | risk_band, monthly_income, requested_amount | approved_amount, interest_rate, emi_options |
| `pdf_generation` | Generate + upload PDF offer | offer, customer, application | storage_path, download_url |
| `node_decline` | Record decline decision | failing_rule / risk_band | Decision record, rejection email |
| `node_hitl_review` | Route to human review | session | session.status = HITL |
| `audit_commit` | Final audit log entry | all state | AuditLog record |

### Hard Policy Rules (`config/policy_rules.yaml`)

```yaml
rules:
  - id: min_age
    field: estimated_age
    operator: gte
    value: 21
    decline_reason: "Minimum age requirement is 21 years"

  - id: bureau_score
    field: credit_score
    operator: gte
    value: 650
    decline_reason: "CIBIL score must be 650 or above"

  - id: foir
    field: foir_ratio
    operator: lte
    value: 0.50
    decline_reason: "Existing loan EMIs exceed 50% of monthly income"

  # ... 6 more rules
```

---

## 🔧 Services Reference

### `scoring_service.py` — Pre-Session Risk

Called on `GET /session/{token}`. Runs before the customer starts their session.

```python
# Returns:
{
  "geo_risk_score": 0.08,      # GPS vs IP mismatch
  "ip_risk_score": 0.05,       # VPN/Tor/datacenter
  "device_risk_score": 0.00,   # Known device
  "hard_stop": False,          # Government-prohibited IP
  "ip_city": "Pune",
  "ip_state": "Maharashtra"
}
```

### `email_service.py` — AWS SES Templates

Three email types, all HTML-templated with Poonawalla Fincorp branding:

```python
await send_kyc_link_email(to_email, customer_name, kyc_url, expires_at)
await send_offer_email(to_email, customer_name, download_url, approved_amount, interest_rate)
await send_rejection_email(to_email, customer_name, decline_reason)
```

### `s3_service.py` — AWS S3 with SigV4

```python
# Upload file
s3_key = upload_to_s3(file_bytes, key, bucket, content_type)

# Get presigned URL (1 hour TTL, SigV4 signed)
url = generate_presigned_url(key, bucket, expires_seconds=3600)
```

---

## 🗄️ Database Migrations

```bash
# Check current migration state
alembic current

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Create a new migration
alembic revision --autogenerate -m "description"
```

### Migration History

| # | File | What it adds |
|---|---|---|
| 001 | `initial_schema` | All core tables: customers, sessions, applications, decisions, offer_pdfs, audit_logs, admin_users |
| 002 | `add_ip_location_to_sessions` | ip_city, ip_state, ip_zip columns |
| 003 | `add_pan_number_to_customers` | pan_number column |
| 004 | `add_gender_and_antispoof` | estimated_gender, gender_confidence, anti_spoof_score, anti_spoof_passed, spoof_type |
| 005 | `add_s3_keys` | liveness_frame_key, consent_recording_key |

---

## 🔑 Environment Variables

```env
# ── Application ──────────────────────────────────────────────────
APP_ENV=production
APP_BASE_URL=https://your-backend.railway.app
FRONTEND_URL=https://your-frontend.railway.app

# ── Database ─────────────────────────────────────────────────────
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJh...
SUPABASE_DB_URL=postgresql+asyncpg://postgres:password@db.xxxx.supabase.co:5432/postgres

# ── JWT ──────────────────────────────────────────────────────────
JWT_SECRET=minimum-32-character-random-secret-key
JWT_ALGORITHM=HS256
SESSION_TOKEN_TTL_SECONDS=86400

# ── Admin ────────────────────────────────────────────────────────
ADMIN_DEFAULT_EMAIL=admin@poonawalla.com
ADMIN_DEFAULT_PASSWORD=change-immediately

# ── AWS (S3 + Rekognition + SES) ─────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1
S3_BUCKET_FRAMES=kyc-video-frames
S3_BUCKET_PDFS=kyc-offer-pdfs

# ── Email (AWS SES) ───────────────────────────────────────────────
SENDGRID_FROM_EMAIL=kyc@yourdomain.com    # SES-verified sender
SENDGRID_FROM_NAME=Poonawalla Fincorp

# ── LiveKit ───────────────────────────────────────────────────────
LIVEKIT_HOST=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIsomething
LIVEKIT_API_SECRET=your-livekit-secret

# ── LLM ──────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
GROQ_LLM_MODEL=openai/gpt-oss-20b
GEMINI_API_KEY=AIzaSy...

# ── Optional ─────────────────────────────────────────────────────
GEOIP_DB_PATH=/app/data/geoip/GeoLite2-City.mmdb
```

---

## 🐳 Docker

```dockerfile
# Dockerfile summary
FROM python:3.11-slim
# System deps: libgl1, libglib2.0-0, libsndfile1, ffmpeg (for CV + audio)
# Copies app code, installs requirements
# CMD: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
# Build
docker build -t loan-wizard-backend .

# Run with env file
docker run -p 8000:8000 --env-file .env loan-wizard-backend

# Check logs
docker logs <container_id> -f
```

---

## 📦 Key Dependencies

```
fastapi==0.115.5          # API framework
uvicorn[standard]==0.32.1 # ASGI server
sqlalchemy[asyncio]==2.0.36 # Async ORM
asyncpg==0.30.0           # PostgreSQL async driver
alembic==1.14.0           # DB migrations
langgraph==0.2.56         # Agentic pipeline orchestration
lightgbm==4.5.0           # ML model
shap==0.46.0              # ML explainability
scikit-learn==1.5.2       # Calibration + preprocessing
boto3==1.35.0             # AWS SDK (S3 + Rekognition + SES)
groq                      # Whisper STT
httpx==0.27.2             # Async HTTP (Gemini + ip-api + Nominatim)
reportlab==4.2.5          # PDF generation
pikepdf==9.4.2            # PDF encryption
opencv-python-headless==4.10.0.84  # Computer vision
PyJWT==2.10.1             # JWT tokens
passlib[bcrypt]==1.7.4    # Password hashing
```

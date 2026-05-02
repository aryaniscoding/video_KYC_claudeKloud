# Agentic AI Video KYC — Complete Project Documentation

> **Product**: Poonawalla Fincorp Personal Loan Origination via Conversational Video KYC  
> **Version**: 1.0  
> **Date**: May 2026  

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Overview](#2-solution-overview)
3. [Tech Stack](#3-tech-stack)
4. [System Architecture](#4-system-architecture)
5. [Feature Breakdown](#5-feature-breakdown)
6. [Pipeline Deep Dive](#6-pipeline-deep-dive)
7. [Data Models](#7-data-models)
8. [API Reference](#8-api-reference)
9. [UI/UX Design](#9-uiux-design)
10. [Security & Compliance](#10-security--compliance)
11. [ML Model & Decision Engine](#11-ml-model--decision-engine)
12. [Deployment Guide](#12-deployment-guide)
13. [Infrastructure — AWS, Supabase, Railway](#13-infrastructure--aws-supabase-railway)
14. [Scalability & Feasibility](#14-scalability--feasibility)
15. [Environment Variables Reference](#15-environment-variables-reference)

---

## 1. Problem Statement

Traditional loan origination at NBFCs requires:
- Physical branch visits for document verification
- Manual credit officer interviews (typically 45–60 minutes)
- 3–5 day turnaround for loan decisions
- High operational cost per application (₹800–₹2,000 per case)
- Susceptibility to fraud via impersonation or coached responses

**Poonawalla Fincorp** needed a fully digital, AI-driven KYC process that could:
- Verify applicant identity in real-time via video
- Collect loan application data through a conversational interface
- Make instant credit decisions using bureau data + ML scoring
- Detect fraud signals (spoof attacks, VPN usage, location mismatch, coached responses)
- Flag borderline cases for human review rather than automated rejection
- Deliver the entire experience in under 12 minutes from link click to decision

---

## 2. Solution Overview

An end-to-end **Agentic AI Video KYC platform** with three major phases:

### Phase 1 — Pre-Session Risk Scoring
Before the applicant even starts, the system silently evaluates:
- IP address (VPN, Tor, datacenter detection via ip-api.com)
- GPS coordinates vs IP-derived location (mismatch detection)
- Device fingerprint (fraud blacklist check)

### Phase 2 — Guided Video Session (10–12 minutes)
A structured 5-step session:
1. **Welcome & Consent** — Policy disclosure + recorded verbal consent
2. **Liveness Check** — Real-time face anti-spoofing via AWS Rekognition
3. **PAN Capture** — Customer enters PAN for identity anchoring
4. **Conversational Q&A** — 8 questions asked by AI, answers extracted via Groq STT + Gemini LLM
5. **Decision & Offer** — Instant loan offer or decline with reasons

### Phase 3 — Agentic Decision Pipeline (LangGraph)
After Q&A, a LangGraph orchestration pipeline:
- Assembles 35 ML features from session, bureau, and behavioral data
- Evaluates 9 hard policy rules
- Runs LightGBM risk model with SHAP explainability
- Computes personalized loan offer (amount, rate, EMI options)
- Generates password-protected PDF offer letter (uploaded to S3)
- Routes borderline cases to Human-In-The-Loop (HITL) review queue
- Sends transactional emails at every decision point via AWS SES

### Admin Dashboard
A React-based admin panel for loan officers to:
- Create customers and send KYC links
- Monitor session status with live polling
- View full session details (biometrics, risk scores, application data, ML decision)
- Approve or decline HITL queue items directly

---

## 3. Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 (Python 3.11) |
| Async ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Database | PostgreSQL 15 (Supabase) |
| Migrations | Alembic |
| AI Orchestration | LangGraph 0.2.56 |
| ML Model | LightGBM 4.5 + Scikit-learn (calibration) |
| Explainability | SHAP 0.46 |
| STT | Groq Whisper (streaming PCM) |
| LLM Extraction | Gemini (field extraction + SHAP narration) |
| Face Analysis | AWS Rekognition (liveness + anti-spoof) |
| Real-time Video | LiveKit WebRTC |
| PDF Generation | ReportLab 4.2 + pikepdf (encryption) |
| Email | AWS SES via boto3 |
| File Storage | AWS S3 (video frames + PDFs) |
| Auth | PyJWT (HS256) + passlib/bcrypt |
| Geo/IP Risk | ip-api.com + OpenStreetMap Nominatim |
| Containerisation | Docker + Docker Compose |
| Hosting | Railway |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 19 + TanStack Start 1.167 |
| Routing | TanStack Router 1.168 |
| State / Data | TanStack Query 5.83 |
| Build | Vite 7.3 |
| Styling | Tailwind CSS 4.2 |
| UI Primitives | Radix UI (17 packages) |
| Forms | React Hook Form 7.71 + Zod 3.24 |
| Charts | Recharts 2.15 |
| Icons | Lucide React |
| Hosting | Railway (nginx static) |

### Infrastructure
| Service | Provider | Purpose |
|---|---|---|
| Database | Supabase (PostgreSQL) | All persistent data |
| Object Storage | AWS S3 (ap-south-1) | Video frames, offer PDFs |
| Face Analysis | AWS Rekognition | Liveness, anti-spoof, age/gender |
| Email Delivery | AWS SES | Transactional emails |
| Real-time Video | LiveKit | WebRTC room management |
| App Hosting | Railway | Backend + frontend containers |
| STT | Groq API | Speech-to-text (Whisper) |
| LLM | Google Gemini | Field extraction, SHAP narration |
| Geo Risk | ip-api.com (free tier) | IP reputation, location |
| Reverse Geocoding | OpenStreetMap Nominatim | GPS → city/state |

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CUSTOMER FLOW                               │
│                                                                     │
│   Email Link → React SPA → WebSocket Sessions → Decision → Email   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS / WSS
┌──────────────────────────▼──────────────────────────────────────────┐
│                      FASTAPI BACKEND (Railway)                      │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  REST APIs  │  │  WS: Liveness│  │ WS: Consent│  │  WS: Q&A │  │
│  │  /admin/*   │  │  /ws/liveness│  │ /ws/consent│  │  /ws/qa  │  │
│  │  /session/* │  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  │
│  └──────┬──────┘         │                │               │        │
│         │           AWS Rekognition    Recording       Groq STT    │
│         │           (anti-spoof)       → S3            + Gemini    │
│         │                                                           │
│  ┌──────▼──────────────────────────────────────────────────────┐   │
│  │              LANGGRAPH PIPELINE (post-QA)                   │   │
│  │                                                             │   │
│  │  form_assembly → hard_rules → ml_scoring → offer_matrix    │   │
│  │       ↓                           ↓              ↓         │   │
│  │   (load 35             (LightGBM +       pdf_generation     │   │
│  │    features)            SHAP)             → S3 + SES        │   │
│  │                                                             │   │
│  │  Decline branch → node_decline → SES rejection email       │   │
│  │  HITL branch   → node_hitl_review → admin queue            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
   Supabase DB         AWS S3             AWS SES
 (PostgreSQL 15)   (frames + PDFs)   (transactional email)
```

### Session State Machine (11 states)

```
PENDING → STARTED → FACE_CHECK → CONSENT → QA → PROCESSING
                                                      │
                           ┌──────────────────────────┤
                           ▼          ▼               ▼
                        APPROVED   DECLINED          HITL
                           │          │               │ (admin action)
                        (email     (email          APPROVED / DECLINED
                        + PDF)     + reason)         (email sent)
                           └──────────┴───────────────┘
                           
Also possible: EXPIRED (token TTL), DROPPED (user abandon)
```

---

## 5. Feature Breakdown

### 5.1 Customer-Facing Session

#### Welcome & Policy Disclosure
- Branded landing page with Poonawalla Fincorp identity
- Displays session validity (24-hour token by default)
- One-click start with camera/mic permission request

#### Liveness & Anti-Spoof Check
- Real-time video feed via LiveKit WebRTC
- AWS Rekognition passive liveness analysis
- Active challenge (blink/nod) for high-risk users
- Signals captured:
  - `liveness_score` (0.0–1.0)
  - `anti_spoof_score` + `anti_spoof_passed`
  - `spoof_type` (print attack, replay, deepfake)
  - `estimated_age`, `estimated_gender`, `gender_confidence`
  - `face_confidence`, `age_consistency_score`
- Best-quality frame saved to S3 (`liveness_frame_key`)
- HITL trigger if liveness < 0.40 or spoof detected

#### Consent Recording
- Displays consent text with 10-second mandatory read window
- Audio recording of verbal consent ("I agree…")
- Groq Whisper STT transcription
- `consent_confidence` score + full transcript stored
- Recording saved to S3 (`consent_recording_key`)
- HITL trigger if consent confidence < 0.70

#### PAN Card Entry
- Validated against regex pattern (AAAAA0000A)
- Stored as uppercase, linked to customer profile

#### Conversational Q&A (8 Questions)
Each question has a 30-second display phase (mic off) then 120-second answer window:

| # | Question Topic | Extracted Fields |
|---|---|---|
| 1 | Full name + date of birth | `full_name`, `dob` |
| 2 | Home address + PIN code | `address_line`, `city`, `state`, `pincode` |
| 3 | Employment type | `employment_type` (salaried/self_employed/business) |
| 4 | Monthly take-home salary | `monthly_income` |
| 5 | Employer name + job tenure | `employer_name`, `job_tenure_years` |
| 6 | Loan purpose | `loan_purpose` |
| 7 | Loan amount + preferred tenure | `requested_amount`, `preferred_tenure_months` |
| 8 | Existing loans + total EMI | `has_existing_loans`, `existing_emi_monthly` |

- Streaming STT via Groq (binary PCM chunks over WebSocket)
- Gemini LLM extracts structured fields per answer
- Per-field confidence scores (0.0–1.0)
- Inconsistency detection across answers
- Manual advance if silence detected, auto-advance at timer

#### Processing Screen
- Animated loading indicator
- Polls `GET /session/{id}/offer` every 3 seconds
- Shows while LangGraph pipeline runs (typically 8–15 seconds)

#### Offer Screen (Approved)
- Approved amount (₹) prominently displayed
- Interest rate, processing fee
- EMI table for 3 tenure options (admin-configured)
- Recommended tenure highlighted
- "Download Offer Letter" button → S3 presigned URL
- Offer validity countdown (30 days)

#### Declined Screen
- Decline reason (policy rule or ML risk band)
- PD score (probability of default %)
- Contributing risk factors
- 4 improvement tips (CIBIL, EMI ratio, employment, reapply date)

#### Manual Review Screen
- Friendly message: "Your application is under review"
- Estimated review time: 1 business day
- Helpline number

#### Expired Screen
- Clear expiry message
- "Contact your loan officer" call to action

---

### 5.2 Admin Dashboard

#### Login
- JWT-based authentication (bcrypt password hash)
- Token stored in `localStorage` as `lw_admin_token`
- Default credentials configurable via env

#### All Customers Tab
- Full customer table: Name, Email, Phone (masked), CIBIL Score, Status badge, Created date
- Auto-refreshes every 30 seconds
- Manual "Refresh" button
- "Add Customer" button → modal
- "Send Link" / "Resend Link" per row
- Click any row → Session Status Drawer

**Add Customer Modal**:
- Fields: Full Name, Phone (10 digits), Email, CIBIL Score (required, 300–900)
- On duplicate phone → amber banner showing existing customer's full details (Name, Email, Phone, PAN, CIBIL, Product, Created date) + "Send KYC Link" button inline

**Session Status Drawer** (full-screen modal):
- Two-column layout
- **Left column**: Personal details, Address, Employment & Income, Loan Request, LLM Extraction Quality (confidence/inconsistency bars)
- **Right column**: Decision Breakdown (hard rules + ML scoring + offer), Biometrics (face frame image + scores), Network & Fraud Signals, Behaviour & Consent
- **Bottom strip**: Session Timeline, Session metadata
- HITL sessions show approve/decline panel with notes textarea

#### Manual Review Tab (HITL Queue)
- Table of sessions flagged for human review
- Columns: Customer Name, Session ID, Flagged At, Flag Reason
- **Inline action buttons per row**: ✓ Approve (green), ✕ Decline (red → requires reason modal), Review (opens full drawer)
- Approve → offer email sent immediately to customer
- Decline → rejection email with admin's typed reason sent immediately
- Row shows "✓ Approved" / "✕ Declined" after action, queue auto-refreshes

---

### 5.3 Email Notifications (AWS SES)

| Trigger | Email |
|---|---|
| Admin sends KYC link | KYC session link with expiry, instructions |
| Pipeline: APPROVED | Offer letter email with PDF download link, amount, rate |
| Pipeline: DECLINED | Rejection email with reason + improvement tips |
| Admin HITL: Approve | Same offer email as pipeline approval |
| Admin HITL: Decline | Rejection email with admin's stated reason |

All emails use branded Poonawalla Fincorp HTML templates with header/footer.

---

### 5.4 Fraud & Risk Signals

#### Pre-Session (computed before session starts)
| Signal | Method | Score |
|---|---|---|
| IP risk | ip-api.com VPN/Tor/datacenter flags | 0.0–1.0 |
| Geo risk | GPS ↔ IP city/state mismatch via Nominatim | 0.0–1.0 |
| Device risk | Fingerprint vs. fraud blacklist | 0.0–1.0 |
| Hard stop | Government-prohibited IPs | Block |

#### During Session
| Signal | Source |
|---|---|
| Velocity fraud | ≥7 sessions from same phone in 7 days |
| Liveness score | AWS Rekognition |
| Anti-spoof | AWS Rekognition (print/replay/deepfake) |
| Consent confidence | Groq Whisper transcript similarity |
| Hesitation count | STT silence detection |
| Response latency | Per-question timer tracking |
| Inconsistency score | Gemini cross-answer consistency check |
| Location mismatch | Q&A stated city/state vs IP-derived |

---

## 6. Pipeline Deep Dive

### LangGraph Node Flow

```
[START]
   │
   ▼
form_assembly        ← Loads session + application + customer
   │                   Calls build_35_features()
   │                   Checks prior application history
   ▼
hard_rules           ← Evaluates 9 policy rules from policy_rules.yaml
   │                   Loads rules dynamically (hot-reload support)
   ├─ (fail) ──────► node_decline → audit_commit → [END]
   │
   ▼
ml_scoring           ← Loads LightGBM model + calibrator
   │                   Runs 35-feature vector
   │                   Computes PD score, risk band, SHAP values
   ├─ (HIGH/VERY_HIGH) → node_hitl_review → [END]  (awaits admin)
   ├─ (MEDIUM_HIGH)   → node_hitl_review → [END]  (awaits admin)
   │
   ▼
offer_matrix         ← Deterministic lookup by risk band + income
   │                   Caps amount at customer's requested_amount
   │                   Computes EMI options for 3 tenures
   ├─ (no offer) ───► node_decline → audit_commit → [END]
   │
   ▼
pdf_generation       ← ReportLab PDF with offer details + SHAP reasons
   │                   Password: last 4 digits of mobile
   │                   Upload to S3 (kyc-pdfs bucket)
   │                   await send_offer_email() via AWS SES
   │
   ▼
audit_commit         ← Writes final AuditLog entry
   │                   Updates session status
   ▼
[END]
```

### Hard Rules (9 policies, any failure → decline)

| Rule ID | Condition | Decline Reason |
|---|---|---|
| `min_age` | estimated_age ≥ 21 | "Minimum age requirement is 21 years" |
| `max_age` | estimated_age ≤ 65 | "Maximum age limit is 65 years" |
| `min_income` | monthly_income ≥ ₹15,000 | "Minimum monthly income required is ₹15,000" |
| `bureau_score` | CIBIL ≥ 650 | "Credit score must be 650 or above" |
| `dpd_24m` | dpd_24m ≤ 89 | "Active delinquency detected in past 24 months" |
| `foir` | existing EMI / income ≤ 50% | "Existing EMIs exceed 50% of income" |
| `post_loan_foir` | (existing + new EMI) / income ≤ 50% | "Adding this loan would push total EMIs above 50%" |
| `pincode_exclusion` | pincode not in exclusion list | "Unable to service applications from your area" |
| `liveness` | liveness_score ≥ 0.40 | "Identity verification could not be completed" |

### 35-Feature ML Vector

```
Bureau (5):         credit_score, dpd_12m, dpd_24m, active_loans_count, total_outstanding_inr
Income (4):         monthly_income, employment_type_encoded, employer_tier, job_tenure_years
Loan Request (4):   requested_amount, loan_to_income_ratio, preferred_tenure_months, loan_purpose_encoded
Liabilities (4):    existing_emi_monthly, total_obligations, foir_ratio, debt_to_income
Affordability (2):  post_loan_foir, min_required_salary
Pre-session (3):    geo_risk_score, ip_risk_score, device_risk_score
Biometrics (3):     liveness_score, age_consistency_score, face_confidence_score
Behaviour (3):      avg_response_latency_ms, hesitation_count, question_retry_count
LLM Quality (3):    extraction_confidence_avg, inconsistency_score, consent_confidence
History (7):        prior_apps_count, approved_count, declined_count, hitl_count,
                    avg_days_since_last_app, worst_risk_band, best_loan_performance
```

### Risk Band → Decision Routing

| Risk Band | PD Range | Action |
|---|---|---|
| LOW | < 0.10 | Auto-approve |
| MEDIUM_LOW | 0.10–0.25 | Auto-approve |
| MEDIUM_HIGH | 0.25–0.50 | HITL queue |
| HIGH | 0.50–0.70 | HITL queue |
| VERY_HIGH | > 0.70 | Auto-decline |

---

## 7. Data Models

### Customer
```
id              UUID (PK)
name            TEXT
email           TEXT (unique)
phone_hash      TEXT (unique) — SHA-256 of full phone
phone_last4     CHAR(4)        — PDF password seed
aadhaar_hash    TEXT (optional)
pan_number      VARCHAR(10) (optional)
product_code    TEXT (default: PL_STANDARD)
max_loan_amount NUMERIC (default: 500,000)
credit_score    INTEGER (300–900)
dpd_12m         INTEGER
dpd_24m         INTEGER
active_loans_count INTEGER
total_outstanding_inr NUMERIC
created_at      TIMESTAMPTZ
```

### Session
```
id              UUID (PK)
customer_id     UUID (FK → customers)
status          ENUM (11 states)
token_jti       TEXT (unique) — JWT ID, used as session_id in all APIs
policy_ver      TEXT
product_code    TEXT
max_amount      NUMERIC

-- JWT timing
token_issued_at  TIMESTAMPTZ
token_expires_at TIMESTAMPTZ

-- Pre-session risk
geo_risk_score   FLOAT
ip_risk_score    FLOAT
device_risk_score FLOAT
latitude         FLOAT
longitude        FLOAT
ip_address       TEXT
device_fingerprint TEXT
ip_city, ip_state, ip_zip TEXT

-- Biometrics
liveness_score        FLOAT
estimated_age         FLOAT
estimated_gender      TEXT
gender_confidence     FLOAT
age_consistency_score FLOAT
face_confidence       FLOAT
anti_spoof_score      FLOAT
anti_spoof_passed     BOOLEAN
spoof_type            TEXT

-- Consent
consent_confidence  FLOAT
consent_hash        TEXT
consent_timestamp   TIMESTAMPTZ
consent_transcript  TEXT

-- Q&A Behaviour
avg_response_latency_ms FLOAT
hesitation_count        INTEGER
question_retry_count    INTEGER

-- Fraud flags
velocity_fraud_flag BOOLEAN
is_fast_track       BOOLEAN

-- S3 Storage
recording_path         TEXT
liveness_frame_key     TEXT  — S3 key for best face frame
consent_recording_key  TEXT  — S3 key for consent audio

-- Pipeline
langgraph_thread_id TEXT
created_at, updated_at TIMESTAMPTZ
```

### Application
```
id              UUID (PK)
session_id      UUID (FK, unique)
customer_id     UUID (FK)

-- Extracted by LLM from Q1–Q8
full_name, dob, address_line, city, state, pincode
employment_type, monthly_income, employer_name, job_tenure_years
loan_purpose, requested_amount, preferred_tenure_months
existing_emi_monthly, has_existing_loans

-- LLM quality signals
extraction_confidence_avg FLOAT
inconsistency_score       FLOAT
flagged_inconsistencies   JSONB

-- ML input
feature_vector JSONB  -- assembled 35-feature dict
```

### Decision
```
id              UUID (PK)
session_id      UUID (FK, unique)
application_id  UUID (FK)

-- Layer 1: Hard Rules
hard_rules_passed    BOOLEAN
failing_rule         TEXT
failing_rule_reason  TEXT

-- Layer 2: ML Scoring
pd_score             FLOAT    -- probability of default
risk_band            TEXT
eligible             BOOLEAN
shap_values          JSONB
top_positive_features TEXT[]
top_negative_features TEXT[]
model_version        TEXT

-- Layer 3: Offer
approved_amount          NUMERIC
interest_rate            FLOAT    -- annual %
recommended_tenure_months INTEGER
emi_options              JSONB    -- [{tenure_months, emi_amount, total_interest_inr, total_payable}]
processing_fee_pct       FLOAT
offer_matrix_version     TEXT
offer_ref_id             UUID (unique)
offer_valid_until        TIMESTAMPTZ
decided_at               TIMESTAMPTZ
```

### OfferPDF
```
id              UUID (PK)
session_id      UUID (FK)
decision_id     UUID (FK)
offer_ref_id    UUID (unique)
storage_path    TEXT      -- S3 key
pdf_hash        TEXT      -- SHA-256 of PDF bytes
download_url    TEXT      -- S3 presigned URL (1hr)
download_expires_at TIMESTAMPTZ
created_at      TIMESTAMPTZ
```

### AuditLog (append-only, no updates/deletes)
```
id          UUID (PK)
session_id  UUID (FK)
node_name   TEXT      -- LangGraph node name
event_type  TEXT      -- e.g. hitl_triggered, hitl_decision, hard_rule_fail
event_data  JSONB     -- arbitrary structured data
policy_ver  TEXT
model_version TEXT
created_at  TIMESTAMPTZ
```

---

## 8. API Reference

### Authentication
All `/admin/*` endpoints require `Authorization: Bearer <admin_jwt>` header.

### REST Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/admin/login` | None | Admin login → JWT token |
| GET | `/admin/customers` | Admin | List customers (paginated) |
| POST | `/admin/customers` | Admin | Create customer (409 if phone exists) |
| POST | `/admin/send-link` | Admin | Create session + send KYC email |
| POST | `/admin/resend-link` | Admin | Expire old session, create new, send email |
| GET | `/admin/session-status/{jti}` | Admin | Full session detail (all signals, decision) |
| GET | `/admin/hitl-queue` | Admin | List sessions in HITL status |
| POST | `/admin/hitl/{jti}/decision` | Admin | Approve/decline/resume HITL session + email |
| GET | `/session/{token}` | Session JWT | Validate token, start session, score risk |
| POST | `/session/{id}/pan` | Session JWT | Store PAN number |
| GET | `/session/{id}/offer` | Session JWT | Poll for decision result (202 while processing) |
| GET | `/offers/{ref_id}/download` | None | Get fresh presigned PDF URL |
| GET | `/health` | None | Health check |

### WebSocket Endpoints

| Path | Protocol | Description |
|---|---|---|
| `/ws/liveness/{session_id}` | WSS | LiveKit face liveness + anti-spoof |
| `/ws/consent/{session_id}` | WSS | Consent recording + STT transcription |
| `/ws/qa/{session_id}` | WSS | 8-question Q&A (binary PCM audio) |

### Q&A WebSocket Message Flow
```
Server → Client:  { type: "question", index: N, text: "...", phase: "display" }
                  (30 second display window, mic disabled)
Server → Client:  { type: "question", index: N, text: "...", phase: "answer", timer_seconds: 120 }
Client → Server:  <binary PCM audio chunks>
Server → Client:  { type: "transcript_chunk", text: "...", is_final: false }
Server → Client:  { type: "transcript_chunk", text: "...", is_final: true }
Client → Server:  { type: "manual_advance" }  OR  Server → Client: { type: "auto_advance" }
Server → Client:  { type: "extraction_result", index: N, fields: {...}, confidence: 0.89 }
[repeat for all 8 questions]
Server → Client:  { type: "pipeline_started" }
                  (LangGraph pipeline fires, session status → PROCESSING)
```

---

## 9. UI/UX Design

### Design System
- **Color palette**: Dark navy primary (`#1a3c7a`), amber accent, semantic status colors (green/amber/red)
- **Typography**: System font stack, monospace for IDs/codes
- **Custom CSS classes**: `lw-card`, `lw-btn`, `lw-btn-primary`, `lw-btn-outline`, `lw-input`, `lw-label`, `lw-badge`
- **Dark-friendly**: oklch color system, surface/on-surface token pattern

### Customer Session UX Principles
- **Minimal cognitive load**: One action per screen
- **Live progress bar**: Shows current step out of 5
- **30-second question preview**: Customer reads the question before mic activates — reduces anxiety
- **Auto-advance**: Silence detection prevents sessions from stalling
- **Graceful errors**: Each WebSocket closes with an error state that routes to appropriate screen
- **Mobile-first**: Designed to work on smartphone cameras

### Admin Dashboard UX Principles
- **Data density**: Wide two-column drawer shows all signals without scrolling
- **Color-coded risk**: Green > 0.7, amber 0.4–0.7, red < 0.4 for all score displays
- **Inline actions**: Approve/Decline directly in HITL queue row — no drawer needed
- **Auto-refresh**: 30-second polling on customer table; no stale status
- **Duplicate prevention**: 409 response shows full existing customer card with "Send KYC Link" shortcut

### Session Status Drawer (admin)
The most information-dense view in the product:
- **Left column**: Identity, address, employment, income, loan request, LLM quality scores with progress bars
- **Right column**: Decision explanation, hard rules pass/fail, ML scores + SHAP features, offer details, biometrics (live face frame + score cards), network/location/fraud signals, consent transcript
- **Bottom strip**: Session timeline + session metadata
- **HITL panel**: Appears only when status = `hitl`; textarea for notes; Approve (green) / Decline (red, requires notes)

---

## 10. Security & Compliance

### Authentication & Authorisation
- **Session tokens**: HS256 JWT with `jti` (UUID), customer_id, phone_hash, product_code, max_amount — expires in 24 hours
- **Admin tokens**: Separate HS256 JWT signed with same secret; decoded via `get_current_admin` dependency
- **Password hashing**: bcrypt via passlib

### Data Privacy
- **Phone number**: Never stored in plaintext — SHA-256 hash + last 4 digits only
- **Aadhaar**: SHA-256 hash only if provided (optional)
- **Face frames**: Stored in private S3 bucket; accessed only via presigned URLs (1-hour TTL)
- **PDF offer letters**: S3 presigned URL (1-hour TTL); file itself is password-protected (last 4 digits of mobile)
- **Consent recording**: Stored in private S3 bucket; not directly exposed to frontend

### Fraud Prevention Layers
1. **Token-bound sessions**: Each session is tied to a specific JWT — cannot be replayed
2. **Velocity check**: ≥7 sessions/phone/7 days → HITL pause before session starts
3. **IP blacklist**: Government-prohibited IPs → hard block
4. **VPN/Tor detection**: High IP risk score → HITL trigger
5. **Anti-spoof check**: AWS Rekognition detects print/replay/deepfake attacks
6. **Location mismatch**: GPS coordinates reverse-geocoded and compared to IP-derived city/state
7. **Behavioral signals**: Hesitation count, response latency, retry count feed into ML features
8. **LLM inconsistency**: Cross-answer consistency check by Gemini catches coached responses

### Audit Trail
- Every LangGraph node writes an `AuditLog` entry with event type, data, policy version, and model version
- AuditLog is append-only — no row updates or deletes
- HITL decisions log admin_id, decision, and notes
- `policy_ver` is embedded in every session token and audit entry (regulatory traceability)

---

## 11. ML Model & Decision Engine

### Model
- **Algorithm**: LightGBM (gradient boosted trees)
- **Task**: Binary classification — probability of default (PD score 0.0–1.0)
- **Calibration**: Isotonic Regression post-hoc calibration for reliable probability estimates
- **Files**: `models/risk_model_v1.lgb`, `models/calibrator.pkl`, `models/features.json`, `models/thresholds.json`
- **SHAP**: TreeExplainer for per-prediction feature attribution

### Offer Matrix
- **Input**: Risk band + monthly income + requested amount
- **Output**: Approved amount (capped at requested amount), interest rate, processing fee, recommended tenure
- **EMI calculation**: Standard reducing balance formula for 3 tenure options
- **Versioned**: `offer_matrix_version` stored in Decision record

### SHAP Narration
- After scoring, top 3 positive and negative SHAP features are passed to Gemini
- Gemini converts feature names + values → plain English sentences
- Displayed in admin drawer's "Top Risk Drivers" and "Approval Signals" sections

---

## 12. Deployment Guide

### Prerequisites
- Railway account (backend + frontend services)
- Supabase project (PostgreSQL database)
- AWS account with: S3 buckets (frames + PDFs), Rekognition, SES (verified domain/email)
- LiveKit Cloud account (or self-hosted LiveKit server)
- Groq API key
- Google Gemini API key

### Step 1 — Supabase Database Setup
1. Create a new Supabase project (region: ap-south-1 or closest)
2. Note the **Connection String** (postgres://...) → `SUPABASE_DB_URL`
3. Note the **Supabase URL** and **Service Role Key** → `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
4. Migrations run automatically on backend startup via `alembic upgrade head`

### Step 2 — AWS Setup
#### S3 Buckets
```
Create two buckets in ap-south-1:
  1. kyc-video-frames   — for liveness face frames (JPEG)
  2. kyc-offer-pdfs     — for generated offer letter PDFs

Bucket settings (both):
  - Block all public access: ON
  - Versioning: optional
  - Server-side encryption: AES-256

CORS configuration (kyc-video-frames):
[{
  "AllowedHeaders": ["*"],
  "AllowedMethods": ["GET", "PUT", "POST"],
  "AllowedOrigins": ["https://your-frontend-domain.railway.app"],
  "ExposeHeaders": []
}]
```

#### IAM User for Backend
```
Create IAM user: kyc-backend-service
Attach inline policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject","s3:GetObject","s3:DeleteObject","s3:GetObjectAttributes"],
      "Resource": ["arn:aws:s3:::kyc-video-frames/*","arn:aws:s3:::kyc-offer-pdfs/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["rekognition:DetectFaces","rekognition:DetectCustomLabels","rekognition:StartFaceLivenessSession","rekognition:GetFaceLivenessSessionResults"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail","ses:SendRawEmail"],
      "Resource": "*"
    }
  ]
}
Generate access key → AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

#### SES Setup
```
1. Go to SES → Verified Identities
2. Verify your sending domain (add DNS records) OR verify a single email address
3. If account is in SES Sandbox, request production access
4. Note the verified FROM email → SENDGRID_FROM_EMAIL (variable name kept for compatibility)
5. Set SENDGRID_FROM_NAME = "Poonawalla Fincorp"
```

### Step 3 — LiveKit Setup
```
Option A — LiveKit Cloud (recommended):
  1. Create project at cloud.livekit.io
  2. Note: LIVEKIT_HOST (wss://...), LIVEKIT_API_KEY, LIVEKIT_API_SECRET

Option B — Self-hosted on Railway:
  Deploy livekit/livekit-server Docker image
  Configure STUN/TURN servers for NAT traversal
```

### Step 4 — Railway Deployment

#### Backend Service
```
1. In Railway: New Project → Deploy from GitHub → select repo
2. Set root directory: /backend
3. Railway detects Dockerfile automatically
4. Set environment variables (see Section 15)
5. Add health check: /health
6. The startup command in Dockerfile runs:
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

#### Frontend Service
```
1. New Service → Deploy from GitHub → same repo
2. Set root directory: /fincorp-pathfinder/frontend
3. Build environment variables:
   VITE_API_BASE_URL=https://your-backend.railway.app
   VITE_WS_BASE_URL=wss://your-backend.railway.app
   VITE_USE_MOCK=false
   VITE_EMAIL_SERVER_URL=https://your-email.railway.app
4. Dockerfile builds React app and serves via nginx
```

#### Railway Service Discovery
```
Within Railway private network:
  - Backend → Supabase: external (Supabase cloud)
  - Backend → AWS: external (S3/Rekognition/SES)
  - Frontend → Backend: via VITE_API_BASE_URL (public URL)
  - WS connections: via VITE_WS_BASE_URL (public URL, Railway supports WSS)
```

### Step 5 — Post-Deployment Verification
```bash
# 1. Check health
curl https://your-backend.railway.app/health

# 2. Check migrations ran
# Look for 200 response with {"status":"ok","env":"production"}

# 3. Create admin user (runs via seed script or direct DB insert)
# Default: admin@poonawalla.com / admin123 (change immediately!)

# 4. Test email flow
# Log into admin → Add Customer → Send Link → check inbox

# 5. Test full KYC flow
# Open KYC link in browser → complete session → verify offer email
```

---

## 13. Infrastructure — AWS, Supabase, Railway

### AWS Services

| Service | Usage | Cost Profile |
|---|---|---|
| **S3** (ap-south-1) | Face frames (~50KB each), offer PDFs (~200KB each) | ~₹2/GB/month storage + minimal transfer |
| **Rekognition** | Liveness detection per session | $0.001 per API call (~3 calls/session) |
| **SES** | Transactional emails (KYC link, offer, rejection) | $0.10 per 1,000 emails |

#### S3 Bucket Structure
```
kyc-video-frames/
  └── sessions/{session_id}/liveness_frame.jpg

kyc-offer-pdfs/
  └── sessions/{session_id}/offers/{offer_ref_id}.pdf
```

#### Presigned URL Configuration
- Face frames: 1-hour TTL (admin viewing)
- Offer PDFs: 1-hour TTL (customer download)
- Signed with SigV4, regional endpoint `https://s3.ap-south-1.amazonaws.com`

### Supabase

| Feature | Usage |
|---|---|
| **PostgreSQL 15** | All application data (11 tables) |
| **Connection Pooling** | PgBouncer via Transaction mode (asyncpg compatible) |
| **Backups** | Automatic daily backups (Supabase managed) |
| **Row-Level Security** | Not used — backend enforces all access control |

#### Database Size Estimates
```
Per session:    ~5KB base + 2KB application + 1KB decision + 1KB audit = ~10KB
Per PDF:        stored in S3 (not DB) — only URL stored = negligible
1,000 sessions: ~10MB
100,000 sessions: ~1GB
```

### Railway

| Service | Config | Notes |
|---|---|---|
| **Backend** | Docker, 512MB RAM starter | Upgrade to 1GB for LightGBM inference |
| **Frontend** | Docker/nginx, 512MB | Static files only — minimal resources |
| **Networking** | Public HTTPS + WSS | Railway provides TLS termination |
| **Env vars** | Railway dashboard → Service → Variables | Injected at runtime |
| **Logs** | Railway dashboard → Logs tab | Structured JSON logs from uvicorn |

#### Railway Startup Sequence
```
1. Docker build (cached unless Dockerfile/requirements.txt changed)
2. Container starts → runs: alembic upgrade head
3. Alembic checks migration state in DB
4. Applies any new migrations
5. uvicorn starts on PORT (Railway injects $PORT)
6. Health check passes → service marked healthy
7. Traffic routed to service
```

---

## 14. Scalability & Feasibility

### Current Capacity (Railway Starter)
| Metric | Value |
|---|---|
| Concurrent WebSocket sessions | ~50 (limited by 512MB RAM) |
| API requests/second | ~100 (single uvicorn worker) |
| LangGraph pipeline throughput | ~10 concurrent (LightGBM is CPU-bound) |
| Database connections | 20 (asyncpg pool) |

### Scaling Strategies

#### Horizontal Scaling (Phase 2)
```
Backend:
  - Railway: Enable horizontal scaling (multiple instances)
  - Add Redis for LangGraph checkpoint storage (replace MemorySaver)
  - Move to AsyncPostgresSaver (already supported in graph.py)

WebSocket sessions:
  - Sticky sessions via Railway load balancer (session affinity by cookie)
  - OR move WebSocket state to Redis pub/sub

LightGBM inference:
  - Extract as separate microservice (inference API)
  - Deploy on CPU-optimised Railway plan
  - Cache model in memory — already done via module-level load
```

#### Database Scaling
```
Supabase Pro plan:
  - Up to 8GB RAM, dedicated compute
  - Connection pooling with PgBouncer (already configured)
  - Read replicas for reporting queries

At 1M+ sessions:
  - Partition AuditLog by month (append-only, high volume)
  - Archive old sessions to cold storage
  - Move feature_vector JSONB to separate ML features table
```

#### Cost Projections
```
1,000 sessions/month:
  Railway:     ~$20/month (starter plans)
  Supabase:    $0 (free tier: 500MB)
  AWS S3:      ~$0.05/month
  AWS Rekognition: ~$3/month
  AWS SES:     ~$0.10/month (1K emails)
  Groq:        ~$2/month (Whisper API)
  Total:       ~$25/month

100,000 sessions/month:
  Railway:     ~$200/month (scaled plans)
  Supabase:    ~$25/month (Pro)
  AWS S3:      ~$5/month
  AWS Rekognition: ~$300/month (dominant cost)
  AWS SES:     ~$10/month
  Groq:        ~$150/month
  Total:       ~$700/month (~₹0.60/session)
```

### Feasibility Assessment

| Dimension | Assessment |
|---|---|
| **Technical** | ✅ All components are production-grade, well-supported libraries |
| **Regulatory** | ✅ HITL fallback satisfies RBI requirement for human oversight in digital KYC |
| **Privacy** | ✅ Phone/Aadhaar hashed; face frames and PDFs in private S3; presigned URLs |
| **Fraud Resistance** | ✅ 7-layer fraud detection (IP, geo, device, liveness, consent, behaviour, ML) |
| **Latency** | ✅ Full session 10–12 min; pipeline decision <15 seconds post-QA |
| **Cost** | ✅ ₹0.60/session at scale — dramatically below manual KYC cost (₹800–₹2,000) |
| **Offline Risk** | ⚠️ Groq STT and Gemini are external APIs — add fallback STT (Whisper local) for resilience |
| **Browser Support** | ✅ WebRTC supported in all modern browsers; tested Chrome/Safari/Firefox |

---

## 15. Environment Variables Reference

### Backend (.env)

```env
# ── Application ──────────────────────────────────────────────────────────────
APP_ENV=production
APP_BASE_URL=https://your-backend.railway.app
FRONTEND_URL=https://your-frontend.railway.app

# ── Database (Supabase) ───────────────────────────────────────────────────────
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJh...
SUPABASE_DB_URL=postgresql+asyncpg://postgres:password@db.xxxx.supabase.co:5432/postgres

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET=your-very-long-random-secret-key-min-32-chars
JWT_ALGORITHM=HS256
SESSION_TOKEN_TTL_SECONDS=86400       # 24 hours

# ── Admin ─────────────────────────────────────────────────────────────────────
ADMIN_DEFAULT_EMAIL=admin@poonawalla.com
ADMIN_DEFAULT_PASSWORD=change-me-immediately

# ── AWS (S3 + Rekognition + SES) ─────────────────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-south-1
S3_BUCKET_FRAMES=kyc-video-frames
S3_BUCKET_PDFS=kyc-offer-pdfs

# ── Email (AWS SES) ───────────────────────────────────────────────────────────
SENDGRID_FROM_EMAIL=kyc@yourdomain.com    # must be SES-verified
SENDGRID_FROM_NAME=Poonawalla Fincorp

# ── LiveKit ───────────────────────────────────────────────────────────────────
LIVEKIT_HOST=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIsomething
LIVEKIT_API_SECRET=your-livekit-secret

# ── LLM ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
GROQ_LLM_MODEL=openai/gpt-oss-20b
GEMINI_API_KEY=AIzaSy...

# ── GeoIP ─────────────────────────────────────────────────────────────────────
GEOIP_DB_PATH=/app/data/geoip/GeoLite2-City.mmdb    # optional, falls back to ip-api.com
```

### Frontend (.env)

```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=https://your-backend.railway.app
VITE_WS_BASE_URL=wss://your-backend.railway.app
VITE_EMAIL_SERVER_URL=https://your-email.railway.app
VITE_ADMIN_DEFAULT_PASSWORD=admin123
```

---

## Appendix — Project Structure

```
agentic_ai_video_KYC/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── admin.py          — All admin REST endpoints
│   │   │   ├── session.py        — Customer session endpoints
│   │   │   ├── deps.py           — FastAPI dependencies (auth)
│   │   │   └── ws/
│   │   │       ├── liveness.py   — WebSocket: face liveness
│   │   │       ├── consent.py    — WebSocket: consent recording
│   │   │       └── qa.py         — WebSocket: Q&A engine
│   │   ├── models/               — SQLAlchemy ORM models
│   │   ├── schemas/              — Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── decision_service.py   — Hard rules + ML features + offer matrix
│   │   │   ├── email_service.py      — AWS SES email templates
│   │   │   ├── liveness_service.py   — AWS Rekognition face analysis
│   │   │   ├── llm_extraction_service.py — Gemini field extraction
│   │   │   ├── pdf_service.py        — ReportLab PDF generation
│   │   │   ├── s3_service.py         — AWS S3 upload + presigned URLs
│   │   │   ├── scoring_service.py    — Pre-session risk scoring
│   │   │   ├── stt_service.py        — Groq Whisper STT
│   │   │   └── history_service.py    — Prior application lookup
│   │   ├── orchestration/
│   │   │   └── graph.py          — LangGraph pipeline (8 nodes)
│   │   ├── config.py             — Pydantic settings
│   │   ├── database.py           — SQLAlchemy async engine
│   │   └── main.py               — FastAPI app + router registration
│   ├── migrations/               — Alembic migration files (5)
│   ├── models/                   — ML artifacts (LightGBM, calibrator, features)
│   ├── config/
│   │   └── policy_rules.yaml     — Hard rules configuration
│   └── Dockerfile
│
├── fincorp-pathfinder/frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SessionFlow.jsx       — Customer KYC session
│   │   │   ├── AdminCustomers.jsx    — Admin customer management
│   │   │   ├── AdminHitl.jsx         — HITL queue + decisions
│   │   │   └── AdminLogin.jsx        — Admin login
│   │   ├── components/
│   │   │   ├── admin/
│   │   │   │   ├── SessionStatusDrawer.jsx  — Full session detail modal
│   │   │   │   ├── CustomerTable.jsx        — Customer list table
│   │   │   │   ├── AddCustomerModal.jsx     — Create customer + duplicate handling
│   │   │   │   ├── SendLinkModal.jsx        — Send/resend KYC link
│   │   │   │   ├── StatusBadge.jsx          — Status pill component
│   │   │   │   └── NavBar.jsx               — Admin navigation
│   │   │   └── session/
│   │   │       ├── steps/
│   │   │       │   ├── WelcomeStep.jsx
│   │   │       │   ├── LivenessStep.jsx
│   │   │       │   ├── ConsentStep.jsx
│   │   │       │   ├── PanStep.jsx
│   │   │       │   ├── QAStep.jsx
│   │   │       │   ├── ProcessingStep.jsx
│   │   │       │   ├── OfferStep.jsx
│   │   │       │   ├── DeclinedStep.jsx
│   │   │       │   ├── ManualReviewStep.jsx
│   │   │       │   └── ExpiredStep.jsx
│   │   │       └── ProgressBar.jsx
│   │   └── lib/
│   │       └── apiClient.js       — Unified API client (mock + real)
│   ├── server/
│   │   └── index.js               — Express email relay server (legacy)
│   └── Dockerfile
│
└── docker-compose.yml             — Local dev (backend + LiveKit)
```

---

*Documentation generated May 2026. For questions contact the KYC platform engineering team.*

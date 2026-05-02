<div align="center">

#  LOAN WIZARD - team claudeKloud
### Agentic AI Video KYC · Loan Origination System
#### Built for Poonawalla Fincorp · Problem Statement #3

<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.56-FF6B35?style=for-the-badge&logo=python&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.5-02569B?style=for-the-badge&logo=python&logoColor=white)](https://lightgbm.readthedocs.io)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![AWS](https://img.shields.io/badge/AWS-S3·Rekognition·SES-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL_15-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Railway](https://img.shields.io/badge/Deployed_on-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

<br/>

> **"No forms. No branch visits. One video call to loan approval."**
>
> A fully agentic, AI-driven Video KYC platform that takes a personal loan applicant from  
> identity verification to a signed PDF offer letter — in under 12 minutes.

<br/>

| 🎥 Live Video KYC | 🧠 35-Feature AI Model | ⚡ ~12 Min Journey | 🔒 RBI-Ready Audit Trail | 👁️ 7-Layer Fraud Detection |
|:---:|:---:|:---:|:---:|:---:|
| LiveKit WebRTC | LightGBM + SHAP | End-to-End | Immutable Logs | Continuous Scores |

</div>

---

## 📁 Repository Structure

```
agentic_ai_video_KYC/
├── 📂 backend/                    → FastAPI + LangGraph + ML pipeline
│   ├── app/
│   │   ├── api/                   → REST + WebSocket endpoints
│   │   ├── models/                → SQLAlchemy ORM (11 tables)
│   │   ├── schemas/               → Pydantic request/response
│   │   ├── services/              → AI/ML/email/storage services
│   │   └── orchestration/         → LangGraph 8-node pipeline
│   ├── migrations/                → Alembic (5 migrations)
│   ├── models/                    → LightGBM artifacts
│   ├── config/policy_rules.yaml   → Hard rules config
│   └── README.md                  → [Backend docs →](./backend/README.md)
│
├── 📂 fincorp-pathfinder/frontend/
│   ├── src/
│   │   ├── pages/                 → 4 page components
│   │   ├── components/            → Admin + session UI
│   │   └── lib/apiClient.js       → Unified API client
│   ├── server/index.js            → Legacy email relay (Node/Express)
│   └── README.md                  → [Frontend docs →](./fincorp-pathfinder/frontend/README.md)
│
├── docker-compose.yml             → Local dev (backend + LiveKit)
├── PROJECT_DOCUMENTATION.md       → Full technical specification
└── README.md                      → ← You are here
```

---

## 🎯 Problem Statement

Traditional NBFC loan onboarding is broken across every dimension:

| Pain Point | Reality |
|---|---|
| ⏱️ Time to Decision | 3–7 days (branch visits, manual review) |
| 💸 Cost per Application | ₹180–₹400 (manual KYC officer time) |
| 📋 Form Drop-off Rate | 60%+ abandon long digital forms |
| 🚨 Annual NBFC Fraud | ₹2,400 Cr (no real-time liveness/intent checks) |
| 🔲 Intelligence Used | Zero behavioural, CV, or conversational signals |

**Loan Wizard eliminates all five problems simultaneously.**

---

## 🚀 Quick Links
The entire project is deployed on the internet, live running and tested.
| Service | URL | README |
|---|---|---|
| 🔵 **Backend API** | `https://backend-production-8a7a.up.railway.app` | [backend/README.md](./backend/README.md) |
| 🟠 **Frontend App** | `https://frontend-production-d74a.up.railway.app/` | [frontend/README.md](./fincorp-pathfinder/frontend/README.md) |
| 📧 **Email Server** | `https://nodemailer-server-production-36f5.up.railway.app/` | [server/README.md](./fincorp-pathfinder/frontend/server/README.md) |
| 📖 **API Docs** | `https://backend-production-8a7a.up.railway.app/docs` | Swagger UI (auto-generated) |
| ❤️ **Health Check** | `https://backend-production-8a7a.up.railway.app/docs#/default/health_health_get` | Returns `{"status":"ok"}` |

---

## 🏛️ System Architecture

### High-Level Flow

```mermaid
flowchart TD
    A([👤 Customer\nReceives Email Link]) -->|clicks link| B[React Session SPA\nRailway / nginx]
    ADMIN([🏦 Loan Officer\nAdmin Dashboard]) -->|creates customer\nsends link| ADMINSPA[React Admin SPA\nRailway / nginx]
    
    B -->|HTTPS REST| API[FastAPI Backend\nRailway Docker]
    B -->|WSS WebSocket| WS1[WS: Liveness\n/ws/liveness]
    B -->|WSS WebSocket| WS2[WS: Consent\n/ws/consent]
    B -->|WSS WebSocket| WS3[WS: Q&A\n/ws/qa]
    ADMINSPA -->|HTTPS REST| API

    WS1 -->|frames| REKOG[AWS Rekognition\nLiveness + Anti-spoof]
    WS1 -->|best frame| S3F[S3: kyc-video-frames]
    WS2 -->|audio PCM| GROQ1[Groq Whisper STT]
    WS2 -->|recording| S3F
    WS3 -->|audio PCM| GROQ2[Groq Whisper STT]
    WS3 -->|transcript| GEM[Gemini LLM\nField Extraction]

    API -->|pre-session| IPAPI[ip-api.com\nVPN/Tor/Geo]
    API -->|GPS coords| NOM[Nominatim\nReverse Geocode]

    WS3 -->|Q8 complete\nfire-and-forget| LG[LangGraph Pipeline\n8 Nodes]

    LG -->|read/write| DB[(Supabase\nPostgreSQL 15)]
    LG -->|approved| PDF[ReportLab PDF\n+ S3 Upload]
    PDF -->|offer email| SES[AWS SES\nTransactional Email]
    LG -->|declined| SES
    LG -->|HITL| ADMIN

    PDF -->|PDF stored| S3P[S3: kyc-offer-pdfs]

    style LG fill:#7c3aed,color:#fff
    style API fill:#1d4ed8,color:#fff
    style DB fill:#059669,color:#fff
    style SES fill:#d97706,color:#fff
    style REKOG fill:#d97706,color:#fff
    style S3F fill:#d97706,color:#fff
    style S3P fill:#d97706,color:#fff
```

---

### Session State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING : Admin sends KYC link
    PENDING --> STARTED : Customer opens link
    STARTED --> FACE_CHECK : Liveness WS connected
    FACE_CHECK --> CONSENT : Liveness passed
    FACE_CHECK --> HITL : Liveness score < 0.40
    CONSENT --> QA : Consent recorded
    CONSENT --> HITL : Consent confidence < 0.70
    QA --> PROCESSING : Q8 answered → pipeline fires
    PROCESSING --> APPROVED : All checks pass
    PROCESSING --> DECLINED : Hard rule fail or VERY_HIGH risk
    PROCESSING --> HITL : MEDIUM_HIGH / HIGH risk band
    HITL --> APPROVED : Admin approves → offer email sent
    HITL --> DECLINED : Admin declines → reason email sent
    PENDING --> EXPIRED : JWT TTL exceeded
    STARTED --> DROPPED : User abandons
    QA --> DROPPED : User abandons

    note right of HITL : Human-In-The-Loop\nRBI oversight requirement
    note right of PROCESSING : LangGraph pipeline\n< 15 seconds
```

---

### LangGraph Agentic Pipeline

```mermaid
flowchart LR
    START([▶ START\nPost-QA trigger]) --> FA

    FA["⚙️ form_assembly\nLoad session + app + customer\nBuild 35-feature vector\nCheck prior history"]
    HR["🏛️ hard_rules\nEvaluate 9 policy rules\nYAML hot-reload support"]
    ML["🧠 ml_scoring\nLightGBM PD score\nSHAP explainability\nRisk band assignment"]
    OM["💰 offer_matrix\nDeterministic offer lookup\nEMI calculation × 3 tenures\nAmount capped at request"]
    PDF["📄 pdf_generation\nReportLab + pikepdf\nS3 upload\nOffer email → AWS SES"]
    AC["📋 audit_commit\nAppend-only AuditLog\nFinal status update"]
    DEC["❌ node_decline\nDecision record\nRejection email → AWS SES"]
    HITL["👁️ node_hitl_review\nStatus = HITL\nAdmin queue entry"]
    END2([⏹ END])

    FA --> HR
    HR -->|all 9 rules pass| ML
    HR -->|any rule fails| DEC
    ML -->|LOW / MEDIUM_LOW| OM
    ML -->|MEDIUM_HIGH / HIGH| HITL
    ML -->|VERY_HIGH| DEC
    OM -->|offer computed| PDF
    OM -->|no viable offer| DEC
    PDF --> AC
    AC --> END2
    DEC --> AC
    HITL --> END2

    style FA fill:#1e40af,color:#fff
    style HR fill:#b91c1c,color:#fff
    style ML fill:#7c3aed,color:#fff
    style OM fill:#065f46,color:#fff
    style PDF fill:#b45309,color:#fff
    style AC fill:#374151,color:#fff
    style DEC fill:#991b1b,color:#fff
    style HITL fill:#92400e,color:#fff
```

---

### Three-Layer Decision Architecture

```mermaid
flowchart TD
    subgraph L1["Layer 1 — Hard Rules (9 policies)"]
        R1["✕ Age 21–65\n✕ Income ≥ ₹15,000\n✕ CIBIL ≥ 650\n✕ DPD ≤ 89 days\n✕ FOIR ≤ 50%\n✕ Post-loan FOIR ≤ 50%\n✕ Pincode not excluded\n✕ Liveness ≥ 0.40\n✕ No prohibited IP"]
    end

    subgraph L2["Layer 2 — ML Scoring (LightGBM)"]
        R2["35 features → PD Score\n\nLOW < 10% → Auto Approve\nMED_LOW 10–25% → Auto Approve\nMED_HIGH 25–50% → HITL Queue\nHIGH 50–70% → HITL Queue\nVERY_HIGH > 70% → Decline"]
    end

    subgraph L3["Layer 3 — Offer Matrix"]
        R3["Risk band + income → Amount\nCapped at requested amount\nRate: 11–18% p.a.\n3 EMI tenure options\nReducing balance formula"]
    end

    L1 -->|all pass| L2
    L1 -->|any fail| DECLINE1["❌ Decline\n+ Reason Email"]
    L2 -->|LOW/MED_LOW| L3
    L2 -->|MED_HIGH/HIGH| HITL1["👁️ HITL Queue\n+ Admin Review"]
    L2 -->|VERY_HIGH| DECLINE1
    L3 --> APPROVE["✅ Approved\n+ PDF Offer\n+ Email"]

    style L1 fill:#7f1d1d,color:#fff
    style L2 fill:#1e1b4b,color:#fff
    style L3 fill:#064e3b,color:#fff
    style APPROVE fill:#065f46,color:#fff
    style DECLINE1 fill:#7f1d1d,color:#fff
    style HITL1 fill:#78350f,color:#fff
```

---

## 🧠 AI Intelligence Stack

### The 35-Feature ML Vector

```mermaid
mindmap
  root((35 Features\nLightGBM))
    Bureau 5
      credit_score CIBIL
      dpd_12m
      dpd_24m
      active_loans_count
      total_outstanding_inr
    Income & Employment 4
      monthly_income
      employment_type_encoded
      employer_tier
      job_tenure_years
    Loan Request 4
      requested_amount
      loan_to_income_ratio
      preferred_tenure_months
      loan_purpose_encoded
    Liabilities 4
      existing_emi_monthly
      total_obligations
      foir_ratio
      debt_to_income
    Pre-Session Risk 3
      geo_risk_score
      ip_risk_score
      device_risk_score
    Biometrics 3
      liveness_score
      age_consistency_score
      face_confidence
    Behavioural 3
      avg_response_latency_ms
      hesitation_count
      question_retry_count
    LLM Quality 3
      extraction_confidence_avg
      inconsistency_score
      consent_confidence
    Prior History 7
      prior_apps_count
      approved_count
      declined_count
      hitl_count
      avg_days_since_last_app
      worst_risk_band
      best_loan_performance
```

---

### 8-Question Conversational Q&A Protocol

```mermaid
sequenceDiagram
    participant C as Customer Browser
    participant WS as FastAPI WS /ws/qa
    participant STT as Groq Whisper
    participant LLM as Gemini LLM
    participant DB as Supabase DB

    loop For each of 8 questions
        WS->>C: {type:"question", phase:"display", timer:30s}
        Note over C: Mic OFF — reads question
        WS->>C: {type:"question", phase:"answer", timer:120s}
        Note over C: Mic ON — speaks answer
        C->>WS: [binary PCM audio chunks]
        WS->>STT: stream PCM audio
        STT-->>WS: transcript chunks (partial + final)
        WS->>C: {type:"transcript_chunk", is_final:false}
        WS->>C: {type:"transcript_chunk", is_final:true}
        WS->>LLM: extract fields from transcript
        LLM-->>WS: {fields:{...}, confidence:0.92}
        WS->>C: {type:"extraction_result", fields:{...}}
        WS->>DB: save extracted fields
    end

    WS->>DB: commit Application record
    WS->>C: {type:"pipeline_started"}
    Note over WS: LangGraph pipeline fires async
    WS->>DB: session.status = PROCESSING
```

---

### Fraud Detection — 7 Continuous Layers

```mermaid
flowchart LR
    subgraph PRE["Pre-Session (silent, before user starts)"]
        IP["🌐 IP Risk Score\nVPN · Tor · Datacenter\nGovt blacklist\n→ 0.0–1.0 feature"]
        GEO["📍 Geo Risk Score\nGPS ↔ IP city/state\nNominatim reverse geocode\n→ 0.0–1.0 feature"]
        DEV["📱 Device Risk Score\nFingerprint blacklist\nNew device detection\n→ 0.0–1.0 feature"]
        VEL["⚡ Velocity Flag\n≥7 sessions / 7 days\nPrior decline history\n→ Boolean + history features"]
    end

    subgraph SESSION["During Session"]
        LIVE["👁️ Liveness + Anti-Spoof\nAWS Rekognition\nPrint/Replay/Deepfake\n→ Score + hard gate"]
        CONS["🎙️ Consent Confidence\nGroq Whisper similarity\n→ 0.0–1.0 feature + gate"]
        INCO["🧠 LLM Inconsistency\nGemini cross-answer check\nLatency outlier detection\n→ 0.0–1.0 feature"]
    end

    PRE --> ML["🧠 LightGBM\nAll 7 signals as\ncontinuous features\n(not binary blocks)"]
    SESSION --> ML
    ML --> DECISION["📊 PD Score + Risk Band\n→ Approve / HITL / Decline"]

    style PRE fill:#1e3a5f,color:#fff
    style SESSION fill:#3d1a00,color:#fff
    style ML fill:#2d0060,color:#fff
    style DECISION fill:#064e3b,color:#fff
```

> **Key Design Decision**: Fraud signals are **ML features** (0.0–1.0 continuous), not binary blocks.  
> This means a user with moderate VPN risk isn't auto-rejected — the model weighs all 35 features together.

---

## 🏗️ Infrastructure & Deployment

### Cloud Architecture

```mermaid
graph TB
    subgraph RAILWAY["🚂 Railway Platform"]
        BE["Backend Service\nFastAPI Docker\npython:3.11-slim\nPort 8000"]
        FE["Frontend Service\nnginx Static\nnode:20 → nginx:1.27\nPort 80"]
    end

    subgraph AWS["☁️ AWS ap-south-1"]
        S3F["S3: kyc-video-frames\nLiveness frames\nConsent recordings\nPrivate + Presigned URLs"]
        S3P["S3: kyc-offer-pdfs\nPassword-protected PDFs\nPrivate + Presigned URLs"]
        REKOG["Rekognition\nPassive liveness\nActive challenge\nAnti-spoof"]
        SES["SES\nKYC link emails\nOffer emails\nRejection emails"]
    end

    subgraph SUPA["💚 Supabase"]
        PG["PostgreSQL 15\n11 tables\nasyncpg pool\nAlembic migrations"]
    end

    subgraph EXTERNAL["🌐 External APIs"]
        LIVEKIT["LiveKit Cloud\nWebRTC rooms\nSTUN/TURN relay"]
        GROQ["Groq API\nWhisper STT\nStreaming PCM"]
        GEM["Google Gemini\nField extraction\nSHAP narration"]
        IPAPI["ip-api.com\nVPN/Tor/Geo\nFree tier 45 req/min"]
        NOM["OpenStreetMap\nNominatim\nReverse geocoding"]
    end

    FE -->|HTTPS REST\nWSS WebSocket| BE
    BE -->|SQL asyncpg| PG
    BE -->|S3 API SigV4| S3F
    BE -->|S3 API SigV4| S3P
    BE -->|Rekognition API| REKOG
    BE -->|SMTP/API| SES
    BE -->|WebRTC SDK| LIVEKIT
    BE -->|HTTP REST| GROQ
    BE -->|HTTP REST| GEM
    BE -->|HTTP GET| IPAPI
    BE -->|HTTP GET| NOM

    style RAILWAY fill:#0f0f23,color:#fff
    style AWS fill:#1a0a00,color:#fff
    style SUPA fill:#0a2318,color:#fff
    style EXTERNAL fill:#0a0a1a,color:#fff
```

### Deployment Topology

| Service | Platform | Runtime | RAM | Auto-scale |
|---|---|---|---|---|
| **Backend API** | Railway | Docker (python:3.11-slim) | 512MB–1GB | ✅ Yes |
| **Frontend** | Railway | Docker (nginx:1.27) | 256MB | ✅ Yes |
| **Database** | Supabase | PostgreSQL 15 | Managed | ✅ Managed |
| **Media Storage** | AWS S3 | Object storage | Unlimited | ✅ Infinite |
| **Email** | AWS SES | Managed | Managed | ✅ Infinite |

### Backend Startup Sequence

```
Docker container starts
    └─► alembic upgrade head        (run pending migrations)
            └─► uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
                    └─► FastAPI startup events
                            ├─► SQLAlchemy async engine init
                            ├─► LightGBM model load (models/risk_model_v1.lgb)
                            ├─► Calibrator load (models/calibrator.pkl)
                            └─► Health check: GET /health → {"status":"ok"}
```

---

## 📊 Performance & Scalability

### Latency Benchmarks

```
JWT Validation          < 50ms
Pre-session Risk Score  < 400ms   (ip-api + Nominatim)
Groq STT per answer     < 800ms   (streaming)
Gemini LLM extraction   < 1,200ms (per question)
LightGBM inference      < 50ms    (35 features)
Full PDF generation     < 3,000ms (ReportLab + S3 upload)
Full pipeline (post-QA) < 15s     (all 8 nodes)
End-to-end session      ~12 min   (customer-paced)
```

### Scalability Profile

| Metric | Current (Railway Starter) | Scaled (Railway Pro) |
|---|---|---|
| Concurrent WS sessions | ~50 | ~500+ |
| API requests/sec | ~100 | ~1,000+ |
| DB connections | 20 (asyncpg pool) | 100+ (PgBouncer) |
| Pipeline throughput | ~10 concurrent | ~100 (inference service) |
| Storage | Unlimited (S3) | Unlimited (S3) |

### Cost at Scale

| Volume | Estimated Cost |
|---|---|
| 1,000 sessions/month | ~$25/month (~₹0.20/session) |
| 100,000 sessions/month | ~$700/month (~₹0.60/session) |
| Manual KYC (baseline) | ₹180–₹400/session |

> **98% cost reduction** vs manual KYC at scale.

---

## 🔒 Security & Compliance

### Authentication Architecture

```mermaid
flowchart LR
    subgraph TOKENS["JWT Token Design"]
        ST["Session Token\nHS256 · 24hr TTL\nclaims: customer_id,\nphone_hash, product_code,\nmax_amount, jti, policy_ver"]
        AT["Admin Token\nHS256 · 8hr TTL\nclaims: admin_id,\nemail, sub, role"]
    end

    subgraph PRIVACY["Data Privacy"]
        P1["Phone: SHA-256 hash\n+ last 4 digits only"]
        P2["Aadhaar: SHA-256 hash\n(optional, never plaintext)"]
        P3["Face frames: S3 private\nPresigned URL 1hr TTL"]
        P4["PDF: S3 private\nPassword = last 4 of phone"]
    end

    subgraph AUDIT["Audit Trail"]
        A1["AuditLog: append-only\nNo UPDATE, no DELETE"]
        A2["Every node writes:\nevent_type, event_data,\npolicy_ver, model_version"]
        A3["HITL decisions log:\nadmin_id, decision, notes"]
    end
```

### Compliance Checklist

| Requirement | Implementation | Status |
|---|---|---|
| Human oversight (RBI) | HITL queue for MEDIUM_HIGH/HIGH risk | ✅ |
| Consent recording | Audio stored in S3 with hash + timestamp | ✅ |
| Immutable audit trail | Append-only AuditLog per pipeline node | ✅ |
| Model versioning | `model_version` in every Decision record | ✅ |
| Policy versioning | `policy_ver` in every JWT + audit entry | ✅ |
| Data minimisation | Phone/Aadhaar hashed; no unnecessary PII | ✅ |
| Document security | PDF password-protected + SHA-256 hash | ✅ |
| Access control | JWT-gated all endpoints; bcrypt admin auth | ✅ |

---

## 🧩 Database Schema

```mermaid
erDiagram
    CUSTOMER {
        uuid id PK
        text name
        text email
        text phone_hash
        char phone_last4
        text pan_number
        integer credit_score
        integer dpd_12m
        integer dpd_24m
        text product_code
        numeric max_loan_amount
    }

    SESSION {
        uuid id PK
        uuid customer_id FK
        text token_jti
        enum status
        float liveness_score
        float anti_spoof_score
        float geo_risk_score
        float ip_risk_score
        text liveness_frame_key
        text consent_recording_key
        boolean velocity_fraud_flag
    }

    APPLICATION {
        uuid id PK
        uuid session_id FK
        text full_name
        date dob
        text city
        text state
        text pincode
        text employment_type
        numeric monthly_income
        numeric requested_amount
        float extraction_confidence_avg
        float inconsistency_score
        jsonb feature_vector
    }

    DECISION {
        uuid id PK
        uuid session_id FK
        boolean hard_rules_passed
        text failing_rule
        float pd_score
        text risk_band
        numeric approved_amount
        float interest_rate
        jsonb emi_options
        jsonb shap_values
        text model_version
    }

    OFFER_PDF {
        uuid id PK
        uuid session_id FK
        text storage_path
        text download_url
        text pdf_hash
    }

    AUDIT_LOG {
        uuid id PK
        uuid session_id FK
        text node_name
        text event_type
        jsonb event_data
        text policy_ver
        text model_version
    }

    CUSTOMER ||--o{ SESSION : "has"
    SESSION ||--o| APPLICATION : "produces"
    SESSION ||--o| DECISION : "results in"
    SESSION ||--o| OFFER_PDF : "generates"
    SESSION ||--o{ AUDIT_LOG : "logged in"
```

---

## 🎯 Judging Criteria Alignment

<details>
<summary><b>✅ 3.1 End-to-End Digitisation</b></summary>

| What we built | Evidence |
|---|---|
| Zero paper, zero branch | JWT link → video → decision in one flow |
| 10-step fully digital journey | Welcome → Liveness → Consent → PAN → Q&A → Processing → Decision |
| Paperless offer delivery | Password-protected PDF emailed via AWS SES |
| Admin dashboard with live polling | 30s auto-refresh, manual refresh, send/resend links |
| Automated email on every event | KYC link, offer, rejection — all via AWS SES |

</details>

<details>
<summary><b>✅ 3.2 Accuracy & Compliance</b></summary>

| What we built | Evidence |
|---|---|
| Immutable audit log | Append-only AuditLog, every LangGraph node |
| Policy version traceability | `policy_ver` in every JWT token and audit entry |
| Model version traceability | `model_version` in every Decision record |
| Human oversight (HITL) | MEDIUM_HIGH/HIGH risk → admin queue, RBI-compliant |
| Consent hash + recording | SHA-256 hash + S3 audio + Whisper transcript |
| PDF tamper detection | SHA-256 of PDF bytes stored in DB |

</details>

<details>
<summary><b>✅ 3.3 Risk Mitigation</b></summary>

| What we built | Evidence |
|---|---|
| 7 fraud detection layers | IP risk, geo risk, device risk, liveness, consent, velocity, LLM inconsistency |
| Continuous scores (not binary gates) | All signals are 0.0–1.0 features fed into LightGBM |
| Anti-spoof detection | AWS Rekognition: print attack, replay, deepfake |
| Location mismatch detection | GPS → Nominatim reverse geocode vs ip-api.com city/state |
| 9 hard policy rules | Any failure → immediate decline with specific reason |
| Velocity fraud flag | ≥7 sessions/phone/7 days → HITL pause |

</details>

<details>
<summary><b>✅ 3.4 Intelligence & Personalisation</b></summary>

| What we built | Evidence |
|---|---|
| 35-feature ML model | 9 feature groups: bureau, income, loan, liabilities, risk, biometrics, behaviour, LLM, history |
| Gemini LLM extraction | Per-question structured field extraction with confidence scores |
| SHAP explainability | Top 3 positive + negative features per decision, narrated in plain English |
| Offer capped at request | `approved_amount = min(computed_amount, requested_amount)` |
| Personalised EMI options | 3 tenures computed via reducing balance formula |
| HITL for nuanced cases | Borderline risk (MEDIUM_HIGH/HIGH) gets human review, not auto-decline |

</details>

<details>
<summary><b>✅ 3.5 Scalability & Reliability</b></summary>

| What we built | Evidence |
|---|---|
| Async FastAPI + asyncpg | Non-blocking I/O throughout |
| LangGraph with DB checkpointing | AsyncPostgresSaver — pipeline resumable on crash |
| S3 for all media | No database bloat; unlimited scale |
| Stateless API layer | Horizontal scaling ready |
| Railway auto-scaling | Both services configured for auto-scale |
| FastAPI BackgroundTasks | Email sending non-blocking (uses FastAPI BackgroundTasks) |
| < 15s decision pipeline | LightGBM inference < 50ms; full pipeline < 15s |

</details>

---

## 🔑 Why Loan Wizard Wins

| Dimension | Loan Wizard | Typical NBFC Solution |
|---|---|---|
| **Fraud signals** | 7 continuous ML features | Binary checks (pass/fail) |
| **Prior history** | 7-feature history vector | Ignored |
| **Feature depth** | 35 features, 9 groups | 10–15 features |
| **Offer amount** | Capped at customer's request | May over-offer |
| **Explainability** | SHAP per-prediction narration | Black box |
| **Offer generation** | Deterministic matrix | LLM-generated (unreliable) |
| **Decline reason** | Specific rule or PD score | Generic message |
| **Human oversight** | HITL queue with email notification | Manual callback |
| **Audit trail** | Per-node immutable log | Request-level only |
| **Pipeline resilience** | DB-checkpointed, resumable | Stateless, restarts from scratch |

---

## 🛠️ Local Development Setup

### Prerequisites

```bash
# Required
Python 3.11+
Node.js 20+
Docker + Docker Compose
PostgreSQL 15 (or Supabase project)

# Optional for full local setup
LiveKit server (docker-compose includes it)
```

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/agentic_ai_video_KYC.git
cd agentic_ai_video_KYC
```

### 2. Backend Setup

```bash
cd backend
cp .env.example .env        # fill in your credentials
pip install -r requirements.txt
alembic upgrade head        # run migrations
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd fincorp-pathfinder/frontend
cp .env.example .env        # set VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                 # starts on http://localhost:3000
```

### 4. With Docker Compose (Backend + LiveKit)

```bash
docker-compose up           # backend on :8000, LiveKit on :7880
```

### 5. Environment Variables

See [backend/README.md](./backend/README.md#environment-variables) and  
[frontend/README.md](./fincorp-pathfinder/frontend/README.md#environment-variables)  
for complete environment variable references.

---

## 📧 Email Notification Flow

```mermaid
flowchart TD
    E1["Admin sends KYC link\nPOST /admin/send-link"] -->|await| SES1["AWS SES\nKYC link email\n(link + expiry + instructions)"]
    E2["Pipeline: APPROVED\nnode_pdf_generation"] -->|await| SES2["AWS SES\nOffer email\n(amount + rate + PDF download link)"]
    E3["Pipeline: DECLINED\nnode_decline"] -->|await| SES3["AWS SES\nRejection email\n(reason + improvement tips)"]
    E4["Admin: HITL Approve\nPOST /admin/hitl/{id}/decision"] -->|BackgroundTasks| SES4["AWS SES\nOffer email\n(same as pipeline approval)"]
    E5["Admin: HITL Decline\nPOST /admin/hitl/{id}/decision"] -->|BackgroundTasks| SES5["AWS SES\nRejection email\n(admin's typed reason)"]

    style SES1 fill:#d97706,color:#fff
    style SES2 fill:#065f46,color:#fff
    style SES3 fill:#991b1b,color:#fff
    style SES4 fill:#065f46,color:#fff
    style SES5 fill:#991b1b,color:#fff
```

---

## 🤝 Team

| Name | Role |
|---|---|
| **Aryan** | Backend · ML Pipeline · LangGraph · Infra · Integration |
| **Atharva** | Railway · AWS · API Design |
| **Moksh** | ML model · Frontend · Admin Dashboard · UX |

---

## 📄 License

Built for Poonawalla Fincorp Hackathon · Problem Statement #3  
Internal use only · Not for public distribution

---

<div align="center">

**"AI extracts. AI scores. Rules decide. Every outcome is explainable, auditable, and compliant."**

*Loan Wizard doesn't replace the loan officer's judgement —  
it gives them everything they need to make better decisions, faster.*

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![AWS](https://img.shields.io/badge/AWS-FF9900?style=flat-square&logo=amazonaws&logoColor=white)](https://aws.amazon.com)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.app)

</div>

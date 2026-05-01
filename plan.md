# Aryan's Implementation Plan — Video KYC Loan Origination System

## Scope
Aryan owns everything except: Frontend (Atharva) and ML model training (Moksh).
That means: backend, all AI pipelines, video session, STT, LLM extraction, decision engine, PDF, APIs, infra.

---

## Week-by-Week Build Order

### Week 1 — Foundation
**Goal:** Running FastAPI server, database, JWT system, admin auth APIs.

**Tasks:**
- [ ] Project scaffold: FastAPI app, folder structure, `.env`, Docker Compose (app + postgres + redis)
- [ ] PostgreSQL schema: `sessions`, `customers`, `applications`, `decisions`, `audit_log`, `offer_pdfs` tables
- [ ] JWT token system: generate signed token (UUIDv4 session_id, customer_id, phone hash, product_code, max_amount, TTL, policy_ver, HMAC-SHA256 signature)
- [ ] Admin auth: `POST /admin/login` with bcrypt password hash
- [ ] Admin customer APIs: `GET /admin/customers`, `POST /admin/send-link`, `POST /admin/resend-link`, `GET /admin/session-status/{id}`, `GET /admin/hitl-queue`
- [ ] Redis setup: session state cache, checkpoint store

**Deliverable to Atharva:** Local server + API docs (auto-generated via FastAPI /docs) for admin endpoints.

---

### Week 2 — Pre-Session Intelligence
**Goal:** History check + all 3 pre-session risk scores + LiveKit room management wired up.

**Tasks:**
- [ ] Prior Application History Check:
  - Lookup by customer_id → phone SHA-256 → Aadhaar SHA-256 → name+DOB fuzzy match
  - Extract all 7 ML features: `prior_applications_count`, `prior_rejections_count`, `days_since_last_app`, `last_outcome_encoded`, `prior_risk_band_encoded`, `prior_loan_performance_encoded`, `application_velocity_30d`
  - Velocity fraud flag logic (>=3 in 30d = soft flag, >=7 in 7d = HITL pause)
  - Fast-track pre-fill response for returning approved + clean history customers
- [ ] Geo risk score: GPS vs MaxMind GeoIP2 + pincode risk DB; formula: `city_mismatch×0.40 + pincode_risk×0.40 + state_flag×0.20`
- [ ] IP risk score: MaxMind / ip-api + Tor exit node list + blacklist; formula: `min(vpn×0.30 + tor×0.40 + blacklist×0.50 + datacenter×0.25, 1.0)`
- [ ] Device risk score: FingerprintJS server-side validation, automation detection (Selenium/headless signals), 0.0–0.8 scale
- [ ] Hard-stop gate: expired JWT, replay attack, govt-prohibited IP, product-excluded pincode → return 403 with reason code
- [ ] LiveKit: SFU setup via Docker, room creation/deletion API, participant token generation
- [ ] `GET /session/{token}` endpoint: validates JWT, runs history check + pre-session scoring in parallel, returns session config

**Deliverable to Atharva:** `GET /session/{token}` endpoint docs.

---

### Week 3 — Live Video AI: Liveness, Consent, STT
**Goal:** WebSocket endpoints for liveness detection, verbal consent, and streaming STT during Q&A.

**Tasks:**
- [ ] **Liveness Pipeline (`WS /ws/liveness`):**
  - Accept 15 consecutive BGR frames (112×112×3) from frontend
  - InsightFace ArcFace inference: liveness_score, is_live, spoof_type, face_detected, face_confidence, frames_analyzed
  - If score < 0.75 → trigger active challenge (MediaPipe face landmarks: blink twice)
  - If score < 0.40 after challenge → emit HITL signal
  - Age estimation (InsightFace): estimated_age, age_range, gender, face_quality → compute `age_consistency_score`
  - Stream results back frame-by-frame via WebSocket
- [ ] **Consent STT (`WS /ws/consent`):**
  - faster-whisper transcription of consent utterance
  - LLM validates: does the transcript constitute valid verbal consent?
  - `consent_confidence` score; if < 0.70 → prompt replay; second failure → helpline
  - Store consent record: SHA-256 hash of transcript + microsecond UTC timestamp
- [ ] **Q&A Streaming STT (`WS /ws/qa`):**
  - faster-whisper large-v3, GPU float16, VAD filter, word timestamps
  - 5s audio chunks with 1s overlap, chunk latency target < 800ms
  - Intent detection: 2.5s silence auto-advance signal + confidence plateau detection
  - Manual "Stop & proceed" signal from frontend → flush current partial transcript
  - Send live transcript tokens back to frontend in real-time

**Deliverable to Atharva:** All 3 WebSocket endpoint specs with message schemas.

---

### Week 4 — LLM Extraction + LangGraph Orchestration
**Goal:** Full LLM field extraction pipeline and LangGraph session state machine.

**Tasks:**
- [ ] **LLM Field Extraction:**
  - Deploy Llama 3.1 8B or Qwen2.5 7B via Ollama (local) or vLLM
  - JSON-mode prompts for each of 8 questions (exact schemas from blueprint spec)
  - Confidence handling: 0.90+ = auto-fill green, 0.70–0.89 = amber, 0.50–0.69 = orange flag, < 0.50 = HITL queue, null = follow-up question
  - Cross-field consistency check → `inconsistency_score` (0.0–1.0) + flagged conflict list
  - Schema validation with Pydantic
- [ ] **LangGraph Orchestration:**
  - Define all nodes: `history_check`, `pre_scoring`, `liveness`, `consent`, `qa_engine`, `llm_extract`, `consistency`, `form_assembly`, `hard_rules`, `ml_scoring`, `offer_matrix`, `pdf_generation`, `hitl_review`, `audit_commit`
  - Conditional edges: liveness_fail → HITL, low_conf → follow-up, velocity_high → pause, hard_rules_fail → decline
  - Session resume from Redis checkpoint (any node can resume)
  - Retry logic: 3 attempts per AI node, then HITL fallback
  - `extraction_confidence_avg` computed over all Q1–Q8

---

### Week 5 — Decision Engine
**Goal:** Hard rules + model integration + offer matrix, all wired into LangGraph.

**Tasks:**
- [ ] **Hard Rules Engine:**
  - Policy rules loaded from YAML config (not hardcoded)
  - 8 rules: min age 21, max age 65, income >= 15K, bureau >= 650, no 90+ DPD in 24m, FOIR <= 50%, pincode exclusion list, liveness_score >= 0.40
  - Rules engine returns: pass/fail per rule, first failing rule code, reason text
- [ ] **35-Feature Vector Assembly:**
  - Assemble numpy array in exact order from `features.json` (Moksh's deliverable)
  - All 5 feature groups: Bureau, Income/Employment, Loan Request, Liabilities, Pre-session Scores, CV Signals, Session Behavior, LLM Quality, Prior History
  - Until Moksh delivers model: dummy function returning `pd_score=0.05`, `risk_band=LOW`
- [ ] **Model Integration:**
  - Load `risk_model_v1.lgb` + `calibrator.pkl` (Moksh's deliverables)
  - SHAP TreeExplainer: compute shap_values for all 35 features, extract top 3 positive + negative
  - Output: pd_score, risk_band, eligible bool, shap_values, top features, model_version, scored_at
- [ ] **Offer Matrix:**
  - Deterministic lookup: risk_band × income_bucket × bureau_bucket → approved_amount, rate, tenure_options
  - EMI calculation: standard reducing-balance formula
  - Store offer_matrix_version with each decision
  - `GET /session/{id}/offer` endpoint

---

### Week 6 — PDF, Storage, Audit Trail
**Goal:** Offer letter PDF, S3 delivery, complete audit trail.

**Tasks:**
- [ ] **PDF Generation (`ReportLab`):**
  - Sections: letterhead, customer details, offer box (amount + rate + validity), EMI table (3 tenure options), SHAP approval basis (3 plain-English reasons), fees table, consent record (session ID + time + SHA-256 fingerprint), next steps, regulatory footer
  - Password protection: last 4 digits of registered mobile (PyPDF2 / pikepdf)
  - SHA-256 hash of final PDF stored in DB
- [ ] **S3 Storage (MinIO for dev / AWS S3 for prod):**
  - AES-256 encrypted upload for video/audio (7-year retention lifecycle policy)
  - Pre-signed URL for PDF download (30-day expiry)
  - `GET /offers/{offer_ref_id}/download` → redirect to pre-signed URL
- [ ] **Email trigger:** PDF delivered to customer via SendGrid/SES after offer is generated
- [ ] **Audit Trail:**
  - `audit_log` table: every session event + 35-feature vector + SHAP values + policy_ver + model_version stored atomically in `audit_commit` LangGraph node
  - Immutable append-only log (no UPDATE/DELETE on audit_log)
  - Timestamps in microsecond UTC, all stored as TIMESTAMPTZ

---

### Week 7 — End-to-End Integration, Testing, Demo
**Goal:** Full flow working end-to-end, handoff to team, demo-ready.

**Tasks:**
- [ ] Integration testing: full Ramesh Kumar example flow (from blueprint §13)
- [ ] API documentation: finalize all request/response schemas for Atharva
- [ ] Stress test: liveness pipeline latency, STT chunk latency, LLM extraction latency
- [ ] HITL queue: `GET /admin/hitl-queue`, `POST /admin/hitl/{session_id}/decision` endpoints
- [ ] Error handling: all timeout/failure paths return structured JSON error codes
- [ ] Demo environment: Docker Compose `docker-compose up` brings everything up locally
- [ ] Latency validation against blueprint targets (see below)

---

## Latency Targets (from blueprint)
| Step | Target |
|---|---|
| JWT validation | < 50ms |
| History lookup | < 150ms |
| Pre-session scoring | < 250ms |
| Liveness (15 frames) | < 500ms |
| STT per 5s chunk | < 800ms |
| LLM extraction per question | < 1.5s |
| Consistency check | < 2s |
| LightGBM inference | < 50ms |
| Offer matrix lookup | < 5ms |
| PDF generation | < 6s |
| Total session | 10–12 minutes |

---

## API Endpoints (Aryan owns all of these)

### Admin
- `POST /admin/login`
- `GET /admin/customers`
- `POST /admin/send-link`
- `POST /admin/resend-link`
- `GET /admin/session-status/{id}`
- `GET /admin/hitl-queue`
- `POST /admin/hitl/{session_id}/decision`

### Customer Session
- `GET /session/{token}` — validate JWT, run pre-checks, return session config
- `WS /ws/liveness` — stream frames, get liveness + age results
- `WS /ws/consent` — stream audio, get consent validation
- `WS /ws/qa` — stream Q&A audio, get live transcript + intent signals
- `GET /session/{id}/offer` — get offer details after decision
- `GET /offers/{offer_ref_id}/download` — pre-signed PDF URL

---

## Integration Points
| From | To | What |
|---|---|---|
| Aryan | Atharva | All REST + WebSocket endpoints, exact JSON schemas, local dev server |
| Moksh | Aryan | `risk_model_v1.lgb`, `features.json`, `thresholds.json`, `calibrator.pkl`, `test_inference.py` |

---

## What I Do NOT Build
- Frontend screens (Atharva)
- ML model training / hyperparameter tuning (Moksh)
- Email HTML template (Atharva, SendGrid side)

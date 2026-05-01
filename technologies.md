# Technologies — Aryan's Stack (Final)

## Backend Framework
| Technology | Purpose |
|---|---|
| **FastAPI** 0.115.x | Main API framework — async, WebSocket support, auto OpenAPI docs |
| **Uvicorn** | ASGI server |
| **Pydantic v2** | Request/response validation, LLM output schemas |
| **Python 3.11** | Runtime |

## Database & Storage
| Technology | Purpose |
|---|---|
| **Supabase** (hosted PostgreSQL) | Primary DB — sessions, customers, applications, decisions, audit_log, offer_pdfs |
| **SQLAlchemy 2.x async** + asyncpg | ORM + async queries against Supabase PostgreSQL |
| **Alembic** | DB migrations |
| **Supabase Storage** | Object storage — video recordings, audio, PDFs (free tier: 1GB) |
| **supabase-py** | Python client for Supabase Storage + DB helpers |
| **LangGraph PostgreSQL checkpointer** | Session state / graph checkpointing via `langgraph-checkpoint-postgres` against Supabase |

## Authentication & Security
| Technology | Purpose |
|---|---|
| **PyJWT** | JWT generation + HMAC-SHA256 signature (custom tokens, not Supabase auth) |
| **bcrypt** (passlib) | Admin password hashing |
| **cryptography** | AES-256 encryption for stored video/audio |
| **hashlib (stdlib)** | SHA-256 for phone/Aadhaar hashing, PDF fingerprint, consent hash |

## Real-Time Video & Audio
| Technology | Purpose |
|---|---|
| **LiveKit SFU** | Selective Forwarding Unit — low-latency WebRTC media server (self-hosted via Docker) |
| **livekit-server-sdk (Python)** | Room management, participant token generation |

## Pre-Session Risk Scoring
| Technology | Purpose |
|---|---|
| **Browser Geolocation API** | User grants location permission → precise GPS coords sent to backend |
| **ip-api.com** (free) | VPN/Tor/datacenter/proxy detection from IP |
| **geoip2** + **MaxMind GeoLite2** (free) | Geo lookup: city/state/pincode from IP (fallback when GPS unavailable) |
| **Tor exit node list** | Static list refreshed daily |
| **FingerprintJS (open-source)** | Device fingerprint — bot/automation detection |

## Computer Vision — Liveness & Age
| Technology | Purpose |
|---|---|
| **InsightFace** | ArcFace liveness scoring (15 frames), age estimation, gender |
| **MediaPipe** | Active liveness challenge — face landmark detection (blink) |
| **OpenCV** | Frame preprocessing, BGR handling |
| **ONNX Runtime** | Fast CPU/GPU inference backend for InsightFace models |

## Speech-to-Text
| Technology | Purpose |
|---|---|
| **faster-whisper** (large-v3) | GPU-accelerated Whisper, float16, VAD filter, word timestamps, 5s chunks < 800ms |
| **WhisperX** | Post-session diarization for audit trail |
| **soundfile** | Audio preprocessing — 16kHz mono 16-bit PCM |

## LLM
| Technology | Purpose |
|---|---|
| **Gemini 2.5 Flash** | All LLM tasks: field extraction (Q1–Q8 JSON-mode), consent validation, consistency check, SHAP plain-English reasons |
| **google-generativeai** SDK | Python client for Gemini API (free tier: 1500 req/day) |

## Orchestration
| Technology | Purpose |
|---|---|
| **LangGraph** | Session state machine — 14 nodes, conditional edges, Supabase PostgreSQL checkpointing, session resume |

## Decision Engine
| Technology | Purpose |
|---|---|
| **PyYAML** | Load hard rules from `policy_rules.yaml` |
| **LightGBM** | Load Moksh's `risk_model_v1.lgb`, run inference |
| **SHAP** | TreeExplainer on LightGBM — 35-feature SHAP values |
| **scikit-learn** | Load Moksh's `calibrator.pkl` |
| **NumPy** | 35-feature vector assembly |

## PDF Generation & Delivery
| Technology | Purpose |
|---|---|
| **ReportLab** | PDF generation — all sections per blueprint |
| **pikepdf** | Password protection (last 4 digits of mobile) |
| **Supabase Storage** | PDF upload + pre-signed URL (30-day expiry) |

## Email
| Technology | Purpose |
|---|---|
| **SendGrid** (free: 100 emails/day) | Transactional email — send PDF + KYC link to customer |

## Dev & Infra
| Technology | Purpose |
|---|---|
| **Docker + Docker Compose** | Local dev: app + LiveKit only (Supabase is remote) |
| **pytest + pytest-asyncio** | Tests |
| **python-dotenv** | `.env` management |

---

## What Changed from Initial Plan
- ~~Ollama / vLLM / Llama / Qwen~~ → **Gemini 2.5 Flash** (free tier, no GPU needed for LLM)
- ~~Redis~~ → **Supabase PostgreSQL** (LangGraph postgres checkpointer)
- ~~AWS S3~~ → **Supabase Storage** (free, same platform)
- ~~PostgreSQL self-hosted~~ → **Supabase** (hosted, free tier)
- ~~MaxMind Commercial~~ → **GeoLite2 free** + browser GPS (more accurate when user grants permission)

## GPU Requirement
- Still needed for: **faster-whisper large-v3** and **InsightFace ONNX**
- Gemini runs in cloud — zero local GPU for LLM
- CPU fallback: `faster-whisper small` model for no-GPU dev environment

# Video KYC — WebSocket & REST Protocol Reference

**For:** Atharva (Frontend)  
**Base URL (dev):** `http://localhost:8000` / `ws://localhost:8000`

All `session_id` values are the **JWT ID (`jti`)** returned in the `session_id` field from `GET /session/{token}`.

---

## Flow Order

```
Admin sends link → Customer opens URL with JWT token
  1. GET  /session/{token}          → get session config + LiveKit token
  2. WS   /ws/liveness/{session_id} → passive + active liveness
  3. WS   /ws/consent/{session_id}  → spoken consent capture
  4. WS   /ws/qa/{session_id}       → 8-question Q&A
  5. Poll GET /session/{session_id}/offer → wait for decision
  6. GET  /offers/{offer_ref_id}/download → get PDF download URL
```

---

## 1. REST — Session Initialisation

### `GET /session/{token}`

Called when the customer opens the KYC link. Pass location and device fingerprint as query params.

**Query Parameters**

| Param | Type | Required | Description |
|---|---|---|---|
| `latitude` | float | No | GPS latitude from `navigator.geolocation` |
| `longitude` | float | No | GPS longitude from `navigator.geolocation` |
| `device_fingerprint` | string | No | Browser fingerprint (canvas hash, fonts, UA) |

**Response 200**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "b21a7c6d-...",
  "customer_name": "Ramesh Kumar",
  "product_code": "PL_STANDARD",
  "max_amount": 500000.0,
  "is_fast_track": false,
  "pre_fill": null,
  "scores": {
    "geo_risk_score": 0.08,
    "ip_risk_score": 0.05,
    "device_risk_score": 0.03,
    "hard_stop": false,
    "hard_stop_reason": null
  },
  "livekit_token": "eyJhbGci...",
  "livekit_url": "wss://livekit.example.com",
  "policy_ver": "v1.0"
}
```

**Error Responses**

| Status | `detail` | Meaning |
|---|---|---|
| 410 | `session_expired` | JWT TTL exceeded |
| 401 | `session_invalid` | JWT tampered |
| 403 | `velocity_fraud_pause` | Too many applications — flag for review |
| 403 | `prohibited_ip` / `tor_exit_node` | Hard-stop from IP risk |
| 409 | `session_approved` etc. | Session already completed |

---

## 2. WebSocket — Liveness

**Endpoint:** `ws://localhost:8000/ws/liveness/{session_id}`

### Client → Server

Send raw **JPEG bytes** (binary frames). Capture from the webcam at ~15fps. Send up to 15 frames for passive liveness, then continue sending if challenged.

```
[binary: JPEG frame bytes]
```

### Server → Client Messages

#### `frame_result` — after each of the 15 passive frames

```json
{
  "type": "frame_result",
  "frame_index": 3,
  "face_detected": true,
  "face_confidence": 0.94
}
```

Use this to show a real-time face detection indicator. If `face_detected` is false for several frames, prompt the user to centre their face.

#### `challenge` — passive score 0.40–0.74 (blink required)

```json
{
  "type": "challenge",
  "instruction": "Please blink twice slowly.",
  "liveness_score_so_far": 0.62
}
```

Show the instruction on screen. Continue sending JPEG frames (another 30 frames ~2 seconds).

#### `challenge_frame` — during active challenge (progress)

```json
{
  "type": "challenge_frame",
  "frames_received": 14,
  "frames_needed": 30
}
```

Optional: use to show a progress bar during the blink window.

#### `liveness_result` — final result (always last message before close)

```json
{
  "type": "liveness_result",
  "liveness_score": 0.91,
  "is_live": true,
  "spoof_type": null,
  "anti_spoof_score": 0.89,
  "anti_spoof_passed": true,
  "face_detected": true,
  "face_confidence": 0.96,
  "frames_analyzed": 15,
  "estimated_age": 34,
  "estimated_gender": "male",
  "gender_confidence": 0.94,
  "age_range": "31–37",
  "age_consistency_score": 0.88,
  "active_challenge_required": false,
  "hitl_required": false,
  "challenge_passed": null,
  "blinks_detected": null
}
```

If `hitl_required: true` → show "Our team will verify manually. You'll hear from us within 2 hours."  
If `is_live: true` → advance to consent screen.

`challenge_passed` and `blinks_detected` are only present when an active challenge was run.

#### `error`

```json
{
  "type": "error",
  "detail": "invalid_frame"
}
```

---

## 3. WebSocket — Consent

**Endpoint:** `ws://localhost:8000/ws/consent/{session_id}`

### Server → Client (first message on open)

```json
{
  "type": "ready",
  "consent_text": "I give my consent to Poonawalla Fincorp to record this video session, use my personal information for loan assessment, and verify my identity. I confirm I am providing this consent voluntarily.",
  "instruction": "Please say 'I agree' or 'Yes, I consent' after reading."
}
```

Display the `consent_text` on screen. Read it aloud via TTS or display it for the user to read and respond verbally.

### Client → Server

Send the user's voice response as **raw audio bytes** (WAV or PCM, 16-bit, 16kHz mono).

```
[binary: WAV/PCM audio bytes]
```

Send the full utterance as a single binary message (not chunked) — this is a short response of 2–5 seconds.

### Server → Client (after audio received)

#### `transcript` — what the system heard

```json
{
  "type": "transcript",
  "text": "Yes I agree to give my consent",
  "attempt": 1
}
```

Show this to the user so they know they were heard.

#### `consent_result` — success

```json
{
  "type": "consent_result",
  "is_valid": true,
  "consent_confidence": 0.97,
  "consent_hash": "a3f82b...",
  "timestamp": "2026-04-30T10:15:00.123456+00:00",
  "replay_required": false,
  "helpline_required": false
}
```

Advance to Q&A screen.

#### `replay_required` — first failure (confidence < 0.70)

```json
{
  "type": "replay_required",
  "attempt": 1,
  "reason": "Could not confirm your consent. Please say 'I agree' clearly."
}
```

Show the reason message. Let the user try again — send audio bytes again.

#### `helpline_required` — second failure

```json
{
  "type": "helpline_required",
  "message": "We were unable to capture your consent. Our team will contact you within 2 hours."
}
```

Show the message. End the session on frontend.

#### `error`

```json
{
  "type": "error",
  "detail": "session_not_found"
}
```

---

## 4. WebSocket — Q&A

**Endpoint:** `ws://localhost:8000/ws/qa/{session_id}`

There are 8 questions. Each follows a two-phase cycle. Audio is streamed as PCM chunks.

### Phase 1: Display (30 seconds, mic OFF)

Server sends:

```json
{
  "type": "question",
  "index": 0,
  "text": "What is your full name as it appears on your Aadhaar?",
  "phase": "display",
  "display_seconds": 30,
  "total_questions": 8
}
```

Show the question. Run a 30-second countdown. Keep mic off. After 30 seconds the server automatically sends Phase 2.

### Phase 2: Answer (2 minutes, mic ON)

Server sends:

```json
{
  "type": "question",
  "index": 0,
  "text": "What is your full name as it appears on your Aadhaar?",
  "phase": "answer",
  "timer_seconds": 120
}
```

Start recording. Stream PCM audio chunks as binary messages.

### Client → Server (audio streaming)

```
[binary: raw PCM chunk, 16-bit, 16kHz, mono]
```

Send chunks continuously while the user is speaking. The buffer internally groups them into ~5-second windows with 1-second overlap.

### Client → Server (manual advance — optional)

Send a text message to skip to the next question early:

```json
{"type": "manual_advance"}
```

### Server → Client (during answer phase)

#### `transcript_chunk` — live partial transcript

```json
{
  "type": "transcript_chunk",
  "question_index": 0,
  "text": "My name is Ramesh Kumar",
  "is_final": false
}
```

Show this in a rolling transcript area. The last chunk for a question will have `is_final: true`.

#### `auto_advance` — silence detected (2.5 seconds)

```json
{
  "type": "auto_advance",
  "question_index": 0
}
```

The buffer detected 2.5s of silence. Stop recording, transition to the next question's display phase.

### Server → Client (after answer collected)

#### `extraction_result` — Gemini extracted the fields

```json
{
  "type": "extraction_result",
  "index": 0,
  "fields": {
    "full_name": "Ramesh Kumar",
    "full_name_confidence": 0.98
  },
  "avg_confidence": 0.98,
  "confidence_tier": "green"
}
```

`confidence_tier` values:
- `green` — ≥ 0.90, all good
- `amber` — 0.70–0.89, acceptable
- `orange` — 0.50–0.69, may trigger retry offer
- `hitl` — < 0.50, HITL likely

#### `retry_offer` — low confidence, one retry available

```json
{
  "type": "retry_offer",
  "question_index": 2,
  "message": "We didn't quite catch that. Would you like to answer again?"
}
```

Show the offer for 10 seconds. User can accept or skip.

**Client → Server to accept retry:**

```json
{"type": "retry_accept"}
```

If accepted, server will send a `question` message again with `phase: "answer"` and `timer_seconds: 60`.  
If the user ignores it for 10 seconds, the system moves on automatically.

### End of Q&A

After all 8 questions:

#### `processing`

```json
{
  "type": "processing",
  "message": "Reading your answers..."
}
```

Show a loading state. Gemini consistency check is running.

#### `pipeline_started`

```json
{
  "type": "pipeline_started",
  "extraction_confidence_avg": 0.944,
  "message": "Checking your eligibility..."
}
```

WebSocket closes after this. Switch to polling `GET /session/{session_id}/offer`.

#### `error`

```json
{
  "type": "error",
  "detail": "session_not_found"
}
```

---

## 5. REST — Offer Polling

### `GET /session/{session_id}/offer`

Poll every 3 seconds after `pipeline_started`. The pipeline takes 10–30 seconds.

**Response 202 (still processing)**

```json
{"detail": "processing"}
```

**Response 200 — Approved**

```json
{
  "eligible": true,
  "approved_amount": 400000.0,
  "interest_rate_pct": 12.5,
  "recommended_tenure_months": 24,
  "emi_options": [
    {"tenure_months": 12, "emi_amount": 35611.0, "total_payable": 427332.0},
    {"tenure_months": 24, "emi_amount": 18942.0, "total_payable": 454608.0},
    {"tenure_months": 36, "emi_amount": 13332.0, "total_payable": 479952.0}
  ],
  "processing_fee_pct": 2.0,
  "offer_ref_id": "OFR-20260430-ABC123",
  "offer_valid_until": "2026-05-07T10:15:00+00:00",
  "approval_reasons": ["Strong credit history", "Healthy monthly income", "Stable employment tenure"],
  "risk_band": "MEDIUM_LOW",
  "decline_reason": null,
  "decline_tips": []
}
```

**Response 200 — Declined**

```json
{
  "eligible": false,
  "decline_reason": "Bureau score below minimum threshold (742 < 650 not met — wait, that passed). FOIR 0.82 exceeds maximum 0.50.",
  "decline_tips": [
    "Reduce your existing EMI obligations below 50% of income before applying."
  ],
  "approved_amount": null,
  "emi_options": []
}
```

**Response 400** — session is HITL, DROPPED, or not yet in a terminal state.

---

## 6. REST — PDF Download

### `GET /offers/{offer_ref_id}/download`

**Response 200**

```json
{
  "download_url": "https://njmeotfultzbgvfbknuv.supabase.co/storage/v1/object/sign/kyc-pdfs/...",
  "expires_at": "2026-05-30T10:15:00+00:00"
}
```

Redirect user to `download_url` in a new tab (or download directly). The URL is a Supabase pre-signed URL valid for 30 days.

**Response 410** — link expired.

---

## Audio Format

All audio sent over WebSockets must be:

| Property | Value |
|---|---|
| Format | Raw PCM (consent) or raw PCM chunks (Q&A) |
| Sample rate | 16,000 Hz |
| Bit depth | 16-bit signed |
| Channels | 1 (mono) |
| Encoding | Little-endian |

For consent, send a single WAV or raw PCM blob after the user finishes speaking.  
For Q&A, stream PCM chunks as the user speaks (the backend buffers them).

To capture this in the browser:
```js
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=pcm' });
```

Or use `AudioWorkletProcessor` to get raw PCM at 16kHz.

---

## Connection Lifecycle

- WebSocket connections are **single-use** — one per stage (liveness / consent / QA).
- The server closes the connection after sending the final result message.
- If the connection drops mid-session, re-open the same WebSocket and resume from the last checkpoint where possible.
- Q&A: if disconnected during answer collection, that question's audio is lost. The session status becomes `DROPPED` — show an error and offer to restart.

---

## Summary of All Message Types

| WS | Direction | `type` | Trigger |
|---|---|---|---|
| liveness | S→C | `frame_result` | After each of 15 frames |
| liveness | S→C | `challenge` | Passive score 0.40–0.74 |
| liveness | S→C | `challenge_frame` | During active challenge |
| liveness | S→C | `liveness_result` | Final result (pass/fail/hitl) |
| consent | S→C | `ready` | On connection open |
| consent | S→C | `transcript` | After STT on audio |
| consent | S→C | `consent_result` | Consent accepted |
| consent | S→C | `replay_required` | Low confidence, attempt 1 |
| consent | S→C | `helpline_required` | Failed both attempts |
| qa | S→C | `question` (display) | Start of each question |
| qa | S→C | `question` (answer) | After 30s display window |
| qa | S→C | `transcript_chunk` | Live STT partial result |
| qa | S→C | `auto_advance` | 2.5s silence detected |
| qa | S→C | `extraction_result` | Gemini fields extracted |
| qa | S→C | `retry_offer` | Confidence < 0.50 |
| qa | S→C | `processing` | After Q8 collected |
| qa | S→C | `pipeline_started` | Pipeline kicked off |
| qa | C→S | binary | PCM audio chunks |
| qa | C→S | `manual_advance` | User skips early |
| qa | C→S | `retry_accept` | User accepts retry |
| all | S→C | `error` | Any server error |

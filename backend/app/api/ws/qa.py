"""
WS /ws/qa/{session_id}

Full Q&A session: 8 questions with streaming STT + Gemini extraction.

Protocol per question:
  Server → Client: {"type": "question", "index": N, "text": "...", "phase": "display"}
  [30s display window — mic OFF]
  Server → Client: {"type": "question", "index": N, "text": "...", "phase": "answer", "timer_seconds": 120}
  Client → Server: binary PCM audio chunks (streaming, until silence or manual stop)
  Server → Client: {"type": "transcript_chunk", "text": "...", "is_final": false}
  Server → Client: {"type": "auto_advance"} OR Client → Server: {"type": "manual_advance"}
  Server → Client: {"type": "extraction_result", "index": N, "fields": {...}, "confidence": ...}
  → next question

After Q8:
  Server → Client: {"type": "processing"}
  [LangGraph pipeline kicks off]
  Server → Client: {"type": "pipeline_started"}
"""
import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Session, SessionStatus, Application, AuditLog
from app.services.stt_service import AudioStreamBuffer
from app.services.llm_extraction_service import (
    QUESTIONS, extract_question_fields, merge_extracted_fields,
    run_consistency_check,
)
from app.orchestration.graph import run_post_qa_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

_DISPLAY_WINDOW_S = 15
_MAX_ANSWER_S = 60


@router.websocket("/ws/qa/{session_id}")
async def ws_qa(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info("Q&A WS opened: session=%s", session_id)

    async with AsyncSessionLocal() as db:
        sess_result = await db.execute(select(Session).where(Session.token_jti == session_id))
        session = sess_result.scalar_one_or_none()
        if not session:
            await websocket.send_json({"type": "error", "detail": "session_not_found"})
            await websocket.close()
            return

        all_transcripts: list[str] = []
        all_extractions: list[dict] = []
        question_latencies: list[float] = []
        all_audio_chunks: list[bytes] = []
        hesitation_count = 0
        retry_count = 0

        try:
            for q in QUESTIONS:
                q_idx = q["index"]
                q_text = q["text"]

                # Phase 1: Display window (mic OFF)
                await websocket.send_json({
                    "type": "question",
                    "index": q_idx,
                    "text": q_text,
                    "phase": "display",
                    "display_seconds": _DISPLAY_WINDOW_S,
                    "total_questions": len(QUESTIONS),
                })
                await _wait_display_phase(websocket, _DISPLAY_WINDOW_S)

                # Phase 2: Answer window (mic ON)
                await websocket.send_json({
                    "type": "question",
                    "index": q_idx,
                    "text": q_text,
                    "phase": "answer",
                    "timer_seconds": _MAX_ANSWER_S,
                })

                transcript, latency_ms, hesitations, _silence, audio_chunks = await _collect_answer(
                    websocket, q_idx, _MAX_ANSWER_S
                )
                all_audio_chunks.extend(audio_chunks)
                all_transcripts.append(transcript)
                question_latencies.append(latency_ms)
                hesitation_count += hesitations

                # Run Gemini extraction
                extraction = await extract_question_fields(q_idx, transcript)
                all_extractions.append(extraction)

                # Determine confidence level for this question
                confidence_values = [
                    v for k, v in extraction.items()
                    if k.endswith("_confidence") and isinstance(v, (int, float))
                ]
                avg_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

                await websocket.send_json({
                    "type": "extraction_result",
                    "index": q_idx,
                    "fields": extraction,
                    "avg_confidence": round(avg_conf, 4),
                    "confidence_tier": _confidence_tier(avg_conf),
                })

                # If very low confidence and not last question — offer retry once
                if avg_conf < 0.50 and q_idx < len(QUESTIONS) - 1:
                    retry_answer = await _maybe_retry(websocket, q_idx, q_text)
                    if retry_answer:
                        retry_extraction = await extract_question_fields(q_idx, retry_answer)
                        retry_confs = [
                            v for k, v in retry_extraction.items()
                            if k.endswith("_confidence") and isinstance(v, (int, float))
                        ]
                        retry_avg = sum(retry_confs) / len(retry_confs) if retry_confs else 0.0
                        if retry_avg > avg_conf:
                            all_extractions[-1] = retry_extraction
                        retry_count += 1

            # All 8 questions done — commit PROCESSING immediately so a WS
            # disconnect during merge/consistency won't roll back this status.
            session.status = SessionStatus.PROCESSING
            await db.commit()

            merged = merge_extracted_fields(all_extractions)

            await websocket.send_json({"type": "processing", "message": "Reading your answers..."})

            consistency = await run_consistency_check(merged, session.estimated_age)
            merged["inconsistency_score"] = consistency["inconsistency_score"]
            merged["flagged_inconsistencies"] = consistency.get("flagged_conflicts", [])

            # Save session behaviour metrics
            avg_latency = sum(question_latencies) / len(question_latencies) if question_latencies else 0
            session.avg_response_latency_ms = round(avg_latency, 1)
            session.hesitation_count = hesitation_count
            session.question_retry_count = retry_count
            session.status = SessionStatus.PROCESSING

            # Upsert application record (re-runs of same session must not crash)
            existing_app_result = await db.execute(
                select(Application).where(Application.session_id == session.id)
            )
            app = existing_app_result.scalar_one_or_none()

            app_fields = dict(
                customer_id=session.customer_id,
                full_name=merged.get("full_name"),
                dob=_parse_date(merged.get("dob")),
                address_line=merged.get("address_line"),
                city=merged.get("city"),
                state=merged.get("state"),
                pincode=merged.get("pincode"),
                employment_type=merged.get("employment_type"),
                monthly_income=merged.get("monthly_income"),
                employer_name=merged.get("employer_name"),
                job_tenure_years=merged.get("job_tenure_years"),
                loan_purpose=merged.get("loan_purpose"),
                requested_amount=merged.get("requested_amount"),
                preferred_tenure_months=merged.get("preferred_tenure_months"),
                existing_emi_monthly=merged.get("existing_emi_monthly", 0.0),
                has_existing_loans=merged.get("has_existing_loans"),
                extraction_confidence_avg=merged.get("extraction_confidence_avg"),
                inconsistency_score=merged.get("inconsistency_score"),
                flagged_inconsistencies=merged.get("flagged_inconsistencies"),
            )

            if app is not None:
                for k, v in app_fields.items():
                    setattr(app, k, v)
                logger.info("Updated existing Application %s for session %s", app.id, session.id)
            else:
                app = Application(session_id=session.id, **app_fields)
                db.add(app)
                logger.info("Created new Application for session %s", session.id)

            await db.flush()

            # Re-score geo risk using stated location vs IP-derived location
            from app.services.scoring_service import compute_location_mismatch_score
            mismatch = compute_location_mismatch_score(
                stated_city=merged.get("city"),
                stated_state=merged.get("state"),
                stated_pincode=merged.get("pincode"),
                ip_city=session.ip_city,
                ip_state=session.ip_state,
                ip_zip=session.ip_zip,
            )
            if mismatch > 0:
                session.geo_risk_score = round(
                    min((session.geo_risk_score or 0.0) + mismatch * 0.60, 1.0), 4
                )

            log = AuditLog(
                session_id=session.id,
                node_name="qa_engine",
                event_type="qa_complete",
                event_data={
                    "transcripts": all_transcripts,
                    "extraction_confidence_avg": merged.get("extraction_confidence_avg"),
                    "inconsistency_score": merged.get("inconsistency_score"),
                    "avg_response_latency_ms": avg_latency,
                },
                policy_ver=session.policy_ver,
            )
            db.add(log)
            # Commit Application + AuditLog before firing pipeline or sending
            # pipeline_started, so the task always sees committed data.
            await db.commit()

            # Fire-and-forget S3 upload of full QA recording
            if all_audio_chunks:
                from app.services.s3_service import upload_audio_recording
                asyncio.create_task(_upload_qa_recording(session, all_audio_chunks))

            asyncio.create_task(
                run_post_qa_pipeline(
                    session_id=str(session.id),
                    session_token_jti=session_id,
                    application_id=str(app.id),
                )
            )

            await websocket.send_json({
                "type": "pipeline_started",
                "extraction_confidence_avg": merged.get("extraction_confidence_avg"),
                "message": "Checking your eligibility...",
            })

        except WebSocketDisconnect:
            logger.info("Q&A WS disconnected: session=%s", session_id)
            if session.status == SessionStatus.QA:
                if len(all_extractions) == len(QUESTIONS):
                    session.status = SessionStatus.PROCESSING
                else:
                    session.status = SessionStatus.DROPPED
                await db.commit()
        except Exception as e:
            logger.exception("Q&A WS error: %s", e)
            try:
                await websocket.send_json({"type": "error", "detail": str(e)})
            except Exception:
                pass


# ── Answer collection ──────────────────────────────────────────────────────────

async def _collect_answer(
    websocket: WebSocket,
    question_index: int,
    max_seconds: int,
) -> tuple[str, float, int, bool, list[bytes]]:
    """
    Collect audio chunks until silence_timeout, manual_advance, or deadline.
    Returns (full_transcript, latency_ms, hesitation_count, silence_triggered, pcm_chunks).
    """
    buf = AudioStreamBuffer()
    full_text_parts: list[str] = []
    pcm_chunks: list[bytes] = []
    hesitations = 0
    silence_triggered = False
    t_start = time.perf_counter()
    deadline = t_start + max_seconds

    while time.perf_counter() < deadline:
        remaining = deadline - time.perf_counter()
        try:
            data = await asyncio.wait_for(websocket.receive(), timeout=min(remaining, 5.0))
        except asyncio.TimeoutError:
            break

        msg_type = data.get("type", "")
        if msg_type == "websocket.disconnect":
            raise WebSocketDisconnect()

        raw_bytes = data.get("bytes")
        raw_text = data.get("text")

        if raw_bytes:
            pcm_chunks.append(raw_bytes)
            chunk = await buf.push(raw_bytes)
            if chunk:
                if chunk.text:
                    full_text_parts.append(chunk.text)
                    await websocket.send_json({
                        "type": "transcript_chunk",
                        "question_index": question_index,
                        "text": chunk.text,
                        "is_final": False,
                    })
                if chunk.silence_detected:
                    hesitations += 1

        elif raw_text:
            try:
                msg = json.loads(raw_text)
                mtype = msg.get("type")
                if mtype == "manual_advance":
                    break
                elif mtype == "silence_timeout":
                    # Client detected 5s of silence — acknowledge and close
                    silence_triggered = True
                    await websocket.send_json({
                        "type": "transcript_chunk",
                        "question_index": question_index,
                        "text": "Thank you.",
                        "is_final": True,
                    })
                    await websocket.send_json({
                        "type": "auto_advance",
                        "question_index": question_index,
                    })
                    break
            except json.JSONDecodeError:
                pass

    # Flush remainder
    final = await buf.flush()
    if final and final.text:
        full_text_parts.append(final.text)
        await websocket.send_json({
            "type": "transcript_chunk",
            "question_index": question_index,
            "text": final.text,
            "is_final": True,
        })

    full_transcript = " ".join(full_text_parts).strip()
    latency_ms = (time.perf_counter() - t_start) * 1000
    return full_transcript, latency_ms, hesitations, silence_triggered, pcm_chunks


async def _maybe_retry(websocket: WebSocket, q_idx: int, q_text: str) -> str | None:
    """Offer one retry for low-confidence question. Returns new transcript or None."""
    await websocket.send_json({
        "type": "retry_offer",
        "question_index": q_idx,
        "message": "We didn't quite catch that. Would you like to answer again?",
    })
    try:
        data = await asyncio.wait_for(websocket.receive(), timeout=10.0)
        if "text" in data:
            msg = json.loads(data["text"])
            if msg.get("type") == "retry_accept":
                await websocket.send_json({
                    "type": "question",
                    "index": q_idx,
                    "text": q_text,
                    "phase": "answer",
                    "timer_seconds": 60,
                })
                transcript, _, _, _, _ = await _collect_answer(websocket, q_idx, 60)
                return transcript
    except (asyncio.TimeoutError, json.JSONDecodeError):
        pass
    return None


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _wait_display_phase(websocket: WebSocket, seconds: int) -> None:
    """
    Wait up to `seconds` for the display phase, but exit early if the client
    sends {"type": "skip_display"} or disconnects.
    """
    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    deadline = loop.time() + seconds
    while loop.time() < deadline:
        remaining = deadline - loop.time()
        try:
            data = await _asyncio.wait_for(websocket.receive(), timeout=min(0.4, remaining))
        except _asyncio.TimeoutError:
            continue
        if data.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect()
        raw_text = data.get("text")
        if raw_text:
            try:
                msg = json.loads(raw_text)
                if msg.get("type") == "skip_display":
                    return
            except json.JSONDecodeError:
                pass


def _confidence_tier(score: float) -> str:
    if score >= 0.90:
        return "green"
    elif score >= 0.70:
        return "amber"
    elif score >= 0.50:
        return "orange"
    return "red"


def _parse_date(dob_str: str | None):
    if not dob_str:
        return None
    try:
        from datetime import date
        return date.fromisoformat(dob_str)
    except (ValueError, TypeError):
        return None


async def _upload_qa_recording(session, pcm_chunks: list[bytes]) -> None:
    from app.services.s3_service import upload_audio_recording
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    key = await upload_audio_recording(session.token_jti, pcm_chunks, label="qa")
    if not key:
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.token_jti == session.token_jti)
        )
        s = result.scalar_one_or_none()
        if s:
            s.recording_path = key
            await db.commit()

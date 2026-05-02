"""
WS /ws/consent/{session_id}

Protocol:
  Server → Client: {"type": "ready", "consent_text": "..."}   (TTS text for frontend)
  Client → Server: binary WAV/PCM audio bytes (full utterance)
  Server → Client: {"type": "consent_result", ...}
  If consent_confidence < 0.70: Server → Client: {"type": "replay_required"}
    Client → Server: audio again
    Second failure: {"type": "helpline_required"}
"""
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Session, SessionStatus, AuditLog
from app.services.stt_service import transcribe_full_audio
from app.services.llm_extraction_service import validate_consent

logger = logging.getLogger(__name__)
router = APIRouter()

CONSENT_TEXT = (
    "I give my consent to Poonawalla Fincorp to record this video session, "
    "use my personal information for loan assessment, and verify my identity. "
    "I confirm I am providing this consent voluntarily."
)

_CONSENT_THRESHOLD = 0.50
_MAX_ATTEMPTS = 3


@router.websocket("/ws/consent/{session_id}")
async def ws_consent(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info("Consent WS opened: session=%s", session_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Session).where(Session.token_jti == session_id))
        session = result.scalar_one_or_none()
        if not session:
            await websocket.send_json({"type": "error", "detail": "session_not_found"})
            await websocket.close()
            return

        # Send consent text so frontend can display + TTS it
        await websocket.send_json({
            "type": "ready",
            "consent_text": CONSENT_TEXT,
            "instruction": "Please say 'I agree' or 'Yes, I consent' after reading.",
        })

        attempt = 0
        try:
            while attempt < _MAX_ATTEMPTS:
                audio_bytes = await websocket.receive_bytes()

                # STT
                chunk = await transcribe_full_audio(audio_bytes, language="en")
                transcript = chunk.text

                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "attempt": attempt + 1,
                })

                # Empty transcript — no speech detected, skip Gemini
                if not transcript.strip():
                    attempt += 1
                    if attempt < _MAX_ATTEMPTS:
                        await websocket.send_json({
                            "type": "replay_required",
                            "attempt": attempt,
                            "reason": "No speech detected. Please speak clearly and say 'I agree'.",
                        })
                        continue
                    else:
                        session.status = SessionStatus.HITL
                        db.add(AuditLog(
                            session_id=session.id, node_name="consent", event_type="hitl_triggered",
                            event_data={"reason": "consent_no_speech", "attempts": attempt},
                            policy_ver=session.policy_ver,
                        ))
                        await db.commit()
                        await websocket.send_json({"type": "helpline_required",
                            "message": "We could not detect speech. Our team will contact you within 2 hours."})
                        await websocket.close()
                        return

                # Gemini consent validation
                validation = await validate_consent(transcript)
                consent_confidence = validation["consent_confidence"]
                is_valid = validation["is_valid"]

                if is_valid and consent_confidence >= _CONSENT_THRESHOLD:
                    # Store consent record
                    consent_hash = hashlib.sha256(transcript.encode()).hexdigest()
                    consent_ts = datetime.now(timezone.utc)

                    # Upload consent audio to S3 (non-blocking)
                    from app.services.s3_service import upload_raw_audio
                    consent_key = await upload_raw_audio(session.token_jti, audio_bytes, label="consent")

                    session.consent_confidence = consent_confidence
                    session.consent_hash = consent_hash
                    session.consent_timestamp = consent_ts
                    session.consent_transcript = transcript
                    session.consent_recording_key = consent_key
                    session.status = SessionStatus.QA

                    log = AuditLog(
                        session_id=session.id,
                        node_name="consent",
                        event_type="consent_captured",
                        event_data={
                            "consent_hash": consent_hash,
                            "consent_confidence": consent_confidence,
                            "timestamp_utc": consent_ts.isoformat(),
                            "language_detected": validation.get("language_detected"),
                            "consent_recording_key": consent_key,
                        },
                        policy_ver=session.policy_ver,
                    )
                    db.add(log)
                    await db.commit()

                    await websocket.send_json({
                        "type": "consent_result",
                        "is_valid": True,
                        "consent_confidence": consent_confidence,
                        "consent_hash": consent_hash,
                        "timestamp": consent_ts.isoformat(),
                        "replay_required": False,
                        "helpline_required": False,
                    })
                    await websocket.close()
                    return

                else:
                    attempt += 1
                    if attempt < _MAX_ATTEMPTS:
                        await websocket.send_json({
                            "type": "replay_required",
                            "attempt": attempt,
                            "reason": "Could not confirm your consent. Please say 'I agree' clearly.",
                        })
                    else:
                        # Second failure → helpline
                        session.status = SessionStatus.HITL
                        log = AuditLog(
                            session_id=session.id,
                            node_name="consent",
                            event_type="hitl_triggered",
                            event_data={"reason": "consent_validation_failed", "attempts": attempt},
                            policy_ver=session.policy_ver,
                        )
                        db.add(log)
                        await db.commit()

                        await websocket.send_json({
                            "type": "helpline_required",
                            "message": "We were unable to capture your consent. Our team will contact you within 2 hours.",
                        })
                        await websocket.close()
                        return

        except WebSocketDisconnect:
            logger.info("Consent WS disconnected: session=%s", session_id)
        except Exception as e:
            logger.exception("Consent WS error: %s", e)
            try:
                await websocket.send_json({"type": "error", "detail": str(e)})
            except Exception:
                pass

"""
WS /ws/liveness/{session_id}

Protocol:
  Client → Server: binary JPEG frame bytes (repeated, up to 15 frames)
  Server → Client: JSON per frame result
  After 15 frames: JSON LivenessResult
  If active_challenge_required: Server sends {"type": "challenge", "instruction": "blink twice"}
    Client → Server: more binary frames
    Server → Client: JSON challenge result + final LivenessResult
"""
import logging

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Session, SessionStatus, AuditLog
from app.services.liveness_service import (
    analyze_frame, run_blink_challenge, run_passive_liveness,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PASSIVE_FRAME_COUNT = 15
_CHALLENGE_FRAME_COUNT = 30   # 2-second blink window at 15fps


@router.websocket("/ws/liveness/{session_id}")
async def ws_liveness(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info("Liveness WS opened: session=%s", session_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Session).where(Session.token_jti == session_id))
        session = result.scalar_one_or_none()
        if not session:
            await websocket.send_json({"type": "error", "detail": "session_not_found"})
            await websocket.close()
            return

        session.status = SessionStatus.FACE_CHECK
        await db.commit()

        frames_bgr: list[np.ndarray] = []
        challenge_frames: list[np.ndarray] = []
        in_challenge = False

        try:
            while True:
                data = await websocket.receive_bytes()
                frame_bgr = _decode_jpeg(data)
                if frame_bgr is None:
                    await websocket.send_json({"type": "error", "detail": "invalid_frame"})
                    continue

                if not in_challenge:
                    frames_bgr.append(frame_bgr)
                    frame_idx = len(frames_bgr) - 1

                    # Per-frame lightweight result
                    fr = analyze_frame(frame_bgr, frame_idx)
                    await websocket.send_json({
                        "type": "frame_result",
                        "frame_index": frame_idx,
                        "face_detected": fr.face_detected,
                        "face_confidence": fr.face_confidence,
                    })

                    if len(frames_bgr) == _PASSIVE_FRAME_COUNT:
                        result_passive = run_passive_liveness(frames_bgr)

                        if result_passive.hitl_required:
                            # < 0.40 after passive — HITL
                            session.liveness_score = result_passive.liveness_score
                            session.face_confidence = result_passive.face_confidence
                            session.estimated_age = result_passive.estimated_age
                            session.age_consistency_score = result_passive.age_consistency_score or 0.5
                            session.status = SessionStatus.HITL
                            await _log_audit(db, session, "liveness", "hitl_triggered", {
                                "reason": "liveness_fail",
                                "liveness_score": result_passive.liveness_score,
                            })
                            await db.commit()
                            await websocket.send_json({
                                "type": "liveness_result",
                                **_result_to_dict(result_passive),
                            })
                            await websocket.close()
                            return

                        if result_passive.active_challenge_required:
                            # 0.40–0.74 — ask for blink
                            in_challenge = True
                            await websocket.send_json({
                                "type": "challenge",
                                "instruction": "Please blink twice slowly.",
                                "liveness_score_so_far": result_passive.liveness_score,
                            })
                        else:
                            # >= 0.75 — passed passive
                            await _save_liveness(db, session, result_passive)
                            await websocket.send_json({
                                "type": "liveness_result",
                                **_result_to_dict(result_passive),
                            })
                            await websocket.close()
                            return

                else:
                    # Active challenge phase
                    challenge_frames.append(frame_bgr)
                    await websocket.send_json({
                        "type": "challenge_frame",
                        "frames_received": len(challenge_frames),
                        "frames_needed": _CHALLENGE_FRAME_COUNT,
                    })

                    if len(challenge_frames) == _CHALLENGE_FRAME_COUNT:
                        blink_result = run_blink_challenge(challenge_frames, required_blinks=2)
                        # Re-run passive on combined frames with challenge context
                        combined = frames_bgr + challenge_frames
                        final_passive = run_passive_liveness(combined)

                        if not blink_result["challenge_passed"] or final_passive.liveness_score < 0.40:
                            # Challenge failed → HITL
                            final_passive.hitl_required = True
                            final_passive.active_challenge_required = False
                            session.status = SessionStatus.HITL
                            await _log_audit(db, session, "liveness", "hitl_triggered", {
                                "reason": "active_challenge_fail",
                                "blinks_detected": blink_result["blinks_detected"],
                                "liveness_score": final_passive.liveness_score,
                            })
                        else:
                            final_passive.is_live = True
                            final_passive.hitl_required = False

                        await _save_liveness(db, session, final_passive)
                        await websocket.send_json({
                            "type": "liveness_result",
                            "challenge_passed": blink_result["challenge_passed"],
                            "blinks_detected": blink_result["blinks_detected"],
                            **_result_to_dict(final_passive),
                        })
                        await websocket.close()
                        return

        except WebSocketDisconnect:
            logger.info("Liveness WS disconnected: session=%s", session_id)
        except Exception as e:
            logger.exception("Liveness WS error: %s", e)
            try:
                await websocket.send_json({"type": "error", "detail": str(e)})
            except Exception:
                pass


# ── Helpers ────────────────────────────────────────────────────────────────────

def _decode_jpeg(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame  # None if decode fails


def _result_to_dict(r) -> dict:
    return {
        "liveness_score": r.liveness_score,
        "is_live": r.is_live,
        "spoof_type": r.spoof_type,
        "face_detected": r.face_detected,
        "face_confidence": r.face_confidence,
        "frames_analyzed": r.frames_analyzed,
        "estimated_age": r.estimated_age,
        "age_range": r.age_range,
        "age_consistency_score": r.age_consistency_score,
        "active_challenge_required": r.active_challenge_required,
        "hitl_required": r.hitl_required,
    }


async def _save_liveness(db: AsyncSession, session: Session, result) -> None:
    session.liveness_score = result.liveness_score
    session.face_confidence = result.face_confidence
    session.estimated_age = result.estimated_age
    session.age_consistency_score = result.age_consistency_score or 0.5
    if not result.hitl_required:
        session.status = SessionStatus.CONSENT
    await _log_audit(db, session, "liveness", "liveness_complete", {
        "liveness_score": result.liveness_score,
        "estimated_age": result.estimated_age,
        "age_consistency_score": result.age_consistency_score,
        "spoof_type": result.spoof_type,
    })
    await db.commit()


async def _log_audit(db: AsyncSession, session: Session, node: str, event_type: str, data: dict) -> None:
    log = AuditLog(
        session_id=session.id,
        node_name=node,
        event_type=event_type,
        event_data=data,
        policy_ver=session.policy_ver,
    )
    db.add(log)

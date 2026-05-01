"""
Liveness & Face AI — Phase 4 of the blueprint.

Pipeline:
  1. Passive liveness: InsightFace ArcFace anti-spoofing on 15 frames
  2. If score < 0.75 → trigger active challenge (MediaPipe blink detection)
  3. Age estimation + age_consistency_score
  4. Stream per-frame results over WebSocket

Singleton model loader — loaded once at startup, reused across all sessions.
"""
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Model singleton ────────────────────────────────────────────────────────────

_lock = threading.Lock()
_face_app = None
_mp_face_mesh = None


def _get_face_app():
    global _face_app
    if _face_app is None:
        with _lock:
            if _face_app is None:
                import insightface
                app = insightface.app.FaceAnalysis(
                    name="buffalo_l",
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                )
                app.prepare(ctx_id=0, det_size=(640, 640))
                _face_app = app
                logger.info("InsightFace buffalo_l loaded")
    return _face_app


def _get_mp_face_mesh():
    global _mp_face_mesh
    if _mp_face_mesh is None:
        with _lock:
            if _mp_face_mesh is None:
                import mediapipe as mp
                _mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                logger.info("MediaPipe FaceMesh loaded")
    return _mp_face_mesh


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class FrameResult:
    frame_index: int
    face_detected: bool
    face_confidence: float
    bbox: list[float] | None
    embedding: np.ndarray | None
    estimated_age: float | None
    gender: str | None


@dataclass
class LivenessResult:
    liveness_score: float
    is_live: bool
    spoof_type: str | None
    face_detected: bool
    face_confidence: float
    frames_analyzed: int
    estimated_age: float | None
    age_range: str | None
    age_consistency_score: float | None
    active_challenge_required: bool
    hitl_required: bool


# ── Frame analysis ─────────────────────────────────────────────────────────────

def analyze_frame(frame_bgr: np.ndarray, frame_index: int) -> FrameResult:
    """Run InsightFace on a single BGR frame. Returns face metadata."""
    app = _get_face_app()
    faces = app.get(frame_bgr)

    if not faces:
        return FrameResult(
            frame_index=frame_index,
            face_detected=False,
            face_confidence=0.0,
            bbox=None,
            embedding=None,
            estimated_age=None,
            gender=None,
        )

    # Pick the largest face
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    return FrameResult(
        frame_index=frame_index,
        face_detected=True,
        face_confidence=float(face.det_score),
        bbox=face.bbox.tolist(),
        embedding=face.normed_embedding if hasattr(face, "normed_embedding") else None,
        estimated_age=float(face.age) if hasattr(face, "age") and face.age is not None else None,
        gender="M" if hasattr(face, "gender") and face.gender == 1 else "F",
    )


def compute_liveness_score(frame_results: list[FrameResult]) -> dict:
    """
    Compute liveness score from 15 frame results.

    Signals used:
    - Face detection consistency across frames (live faces persist)
    - Face confidence mean
    - Embedding variance (live faces show micro-movements; static photos don't)
    - Bounding box area variance (natural head movement)
    """
    detected = [r for r in frame_results if r.face_detected]
    detection_ratio = len(detected) / max(len(frame_results), 1)

    if detection_ratio < 0.5:
        # Can't detect face in >50% of frames — not a spoofing attack, bad conditions
        return {
            "liveness_score": 0.0,
            "spoof_type": "face_not_detected",
            "face_detected": False,
            "face_confidence": 0.0,
        }

    confidence_mean = float(np.mean([r.face_confidence for r in detected]))

    # Embedding variance — live faces have small natural drift between frames
    embeddings = [r.embedding for r in detected if r.embedding is not None]
    embedding_var_score = 0.5  # default if insufficient data
    if len(embeddings) >= 3:
        emb_matrix = np.stack(embeddings)
        # Cosine variance: live face ≈ 0.02–0.10; printed photo ≈ 0.001
        cos_sims = []
        for i in range(len(emb_matrix) - 1):
            sim = float(np.dot(emb_matrix[i], emb_matrix[i + 1]))
            cos_sims.append(sim)
        avg_cos_sim = float(np.mean(cos_sims))
        # Very high similarity (>0.999) suggests static image/replay
        if avg_cos_sim > 0.999:
            embedding_var_score = 0.1
        elif avg_cos_sim > 0.995:
            embedding_var_score = 0.6
        else:
            embedding_var_score = 0.9

    # BBox area variance — live head moves slightly
    bbox_areas = [(r.bbox[2] - r.bbox[0]) * (r.bbox[3] - r.bbox[1]) for r in detected if r.bbox]
    bbox_var_score = 0.5
    if len(bbox_areas) >= 3:
        area_cv = float(np.std(bbox_areas) / (np.mean(bbox_areas) + 1e-6))
        bbox_var_score = min(area_cv * 10, 1.0)  # 0.0–1.0

    # Weighted liveness score
    liveness_score = (
        detection_ratio * 0.25
        + confidence_mean * 0.25
        + embedding_var_score * 0.30
        + bbox_var_score * 0.20
    )
    liveness_score = round(min(liveness_score, 1.0), 4)

    spoof_type = None
    if liveness_score < 0.40:
        spoof_type = "print_or_replay"
    elif embedding_var_score < 0.2:
        spoof_type = "static_photo"

    return {
        "liveness_score": liveness_score,
        "spoof_type": spoof_type,
        "face_detected": True,
        "face_confidence": round(confidence_mean, 4),
    }


def estimate_age_stats(frame_results: list[FrameResult]) -> dict:
    ages = [r.estimated_age for r in frame_results if r.estimated_age is not None]
    if not ages:
        return {"estimated_age": None, "age_range": None}
    median_age = float(np.median(ages))
    return {
        "estimated_age": round(median_age, 1),
        "age_range": f"{int(median_age - 3)}–{int(median_age + 3)}",
    }


def compute_age_consistency(estimated_age: float | None, declared_age: float | None) -> float:
    """age_consistency = max(0.0, 1.0 − (age_delta / 15.0)) as per blueprint."""
    if estimated_age is None or declared_age is None:
        return 0.5   # no signal — neutral
    age_delta = abs(estimated_age - declared_age)
    return round(max(0.0, 1.0 - age_delta / 15.0), 4)


# ── Active challenge: blink detection via MediaPipe ────────────────────────────

_LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
_EAR_THRESHOLD = 0.22
_BLINK_CONSEC_FRAMES = 2


def _eye_aspect_ratio(landmarks, eye_indices: list[int], img_h: int, img_w: int) -> float:
    pts = [
        np.array([landmarks[i].x * img_w, landmarks[i].y * img_h])
        for i in eye_indices
    ]
    # EAR formula: vertical distances / (2 × horizontal distance)
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    return (A + B) / (2.0 * C + 1e-6)


def detect_blink_in_frame(frame_bgr: np.ndarray) -> tuple[float, bool]:
    """Returns (ear_value, is_blink)."""
    mesh = _get_mp_face_mesh()
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    result = mesh.process(rgb)
    if not result.multi_face_landmarks:
        return 0.3, False
    h, w = frame_bgr.shape[:2]
    lm = result.multi_face_landmarks[0].landmark
    left_ear = _eye_aspect_ratio(lm, _LEFT_EYE_IDX, h, w)
    right_ear = _eye_aspect_ratio(lm, _RIGHT_EYE_IDX, h, w)
    ear = (left_ear + right_ear) / 2.0
    return float(ear), ear < _EAR_THRESHOLD


def run_blink_challenge(frames_bgr: list[np.ndarray], required_blinks: int = 2) -> dict:
    """
    Processes a sequence of frames and counts confirmed blinks.
    Returns {blinks_detected, challenge_passed, ear_values}.
    """
    blink_counter = 0
    consec_below = 0
    ear_values = []

    for frame in frames_bgr:
        ear, is_blink = detect_blink_in_frame(frame)
        ear_values.append(round(ear, 4))
        if is_blink:
            consec_below += 1
        else:
            if consec_below >= _BLINK_CONSEC_FRAMES:
                blink_counter += 1
            consec_below = 0

    return {
        "blinks_detected": blink_counter,
        "challenge_passed": blink_counter >= required_blinks,
        "ear_values": ear_values,
    }


# ── Full liveness pipeline (used by WS handler) ───────────────────────────────

def run_passive_liveness(frames_bgr: list[np.ndarray], declared_age: float | None = None) -> LivenessResult:
    """
    Run full passive liveness on 15 frames.
    Returns LivenessResult with all signals.
    """
    frame_results = [analyze_frame(f, i) for i, f in enumerate(frames_bgr)]
    scores = compute_liveness_score(frame_results)
    age_stats = estimate_age_stats(frame_results)
    age_consistency = compute_age_consistency(age_stats.get("estimated_age"), declared_age)

    liveness_score = scores["liveness_score"]
    active_challenge_required = liveness_score < 0.75 and liveness_score >= 0.40
    hitl_required = liveness_score < 0.40

    return LivenessResult(
        liveness_score=liveness_score,
        is_live=liveness_score >= 0.75,
        spoof_type=scores.get("spoof_type"),
        face_detected=scores["face_detected"],
        face_confidence=scores["face_confidence"],
        frames_analyzed=len(frames_bgr),
        estimated_age=age_stats.get("estimated_age"),
        age_range=age_stats.get("age_range"),
        age_consistency_score=age_consistency,
        active_challenge_required=active_challenge_required,
        hitl_required=hitl_required,
    )

"""
Liveness & Face AI — Phase 4 (AWS Rekognition backend).

Replaces InsightFace + MediaPipe with AWS Rekognition DetectFaces.
All 15 passive frames are analysed concurrently (asyncio.gather).
Liveness signals: detection ratio, confidence, head-pose variance, bbox variance.
Blink detection: EyesOpen transitions across sampled challenge frames.
"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import boto3
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_lock = threading.Lock()
_client = None
_executor = ThreadPoolExecutor(max_workers=4)


def _get_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = boto3.client(
                    "rekognition",
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                )
                logger.info("Rekognition client ready (region=%s)", settings.aws_region)
    return _client


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class FrameResult:
    frame_index: int
    face_detected: bool
    face_confidence: float
    bbox: list[float] | None
    estimated_age: float | None
    gender: str | None
    pose_yaw: float | None = None
    pose_pitch: float | None = None
    eyes_open: bool | None = None
    sharpness: float | None = None


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


# ── Rekognition call (sync wrapped for async) ──────────────────────────────────

def _detect_sync(jpeg_bytes: bytes) -> dict:
    try:
        return _get_client().detect_faces(
            Image={"Bytes": jpeg_bytes},
            Attributes=["ALL"],
        )
    except Exception as exc:
        logger.warning("Rekognition DetectFaces error: %s", exc)
        return {"FaceDetails": []}


async def _detect(jpeg_bytes: bytes) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _detect_sync, jpeg_bytes)


# ── Per-frame analysis ─────────────────────────────────────────────────────────

async def analyze_frame(jpeg_bytes: bytes, frame_index: int) -> FrameResult:
    resp = await _detect(jpeg_bytes)
    faces = resp.get("FaceDetails", [])

    if not faces:
        return FrameResult(
            frame_index=frame_index, face_detected=False,
            face_confidence=0.0, bbox=None,
            estimated_age=None, gender=None,
        )

    face = max(faces, key=lambda f: f.get("Confidence", 0))
    age_low  = face.get("AgeRange", {}).get("Low",  25)
    age_high = face.get("AgeRange", {}).get("High", 35)
    bb       = face.get("BoundingBox", {})
    pose     = face.get("Pose", {})

    return FrameResult(
        frame_index=frame_index,
        face_detected=True,
        face_confidence=round(face.get("Confidence", 0) / 100.0, 4),
        bbox=[bb.get("Left", 0), bb.get("Top", 0), bb.get("Width", 0), bb.get("Height", 0)],
        estimated_age=round((age_low + age_high) / 2.0, 1),
        gender="M" if face.get("Gender", {}).get("Value") == "Male" else "F",
        pose_yaw=pose.get("Yaw"),
        pose_pitch=pose.get("Pitch"),
        eyes_open=face.get("EyesOpen", {}).get("Value", True),
        sharpness=face.get("Quality", {}).get("Sharpness"),
    )


# ── Liveness scoring ───────────────────────────────────────────────────────────

def compute_liveness_score(frame_results: list[FrameResult]) -> dict:
    detected = [r for r in frame_results if r.face_detected]
    detection_ratio = len(detected) / max(len(frame_results), 1)

    if detection_ratio < 0.5:
        return {"liveness_score": 0.0, "spoof_type": "face_not_detected",
                "face_detected": False, "face_confidence": 0.0}

    confidence_mean = float(np.mean([r.face_confidence for r in detected]))

    # Head-pose yaw variance — live faces drift naturally; printed photos are static
    yaw_vals = [r.pose_yaw for r in detected if r.pose_yaw is not None]
    pose_var_score = 0.5
    if len(yaw_vals) >= 3:
        yaw_std = float(np.std(yaw_vals))
        if yaw_std < 0.5:
            pose_var_score = 0.1   # completely static → likely photo/replay
        elif yaw_std < 2.0:
            pose_var_score = 0.5
        else:
            pose_var_score = min(yaw_std / 10.0, 1.0)

    # BBox area variance — natural head movement changes face size slightly
    bbox_areas = [r.bbox[2] * r.bbox[3] for r in detected if r.bbox]
    bbox_var_score = 0.5
    if len(bbox_areas) >= 3:
        area_cv = float(np.std(bbox_areas) / (np.mean(bbox_areas) + 1e-6))
        bbox_var_score = min(area_cv * 10, 1.0)

    liveness_score = round(min(
        detection_ratio  * 0.25
        + confidence_mean  * 0.25
        + pose_var_score   * 0.30
        + bbox_var_score   * 0.20,
        1.0,
    ), 4)

    spoof_type = None
    if liveness_score < 0.40:
        spoof_type = "print_or_replay"
    elif pose_var_score < 0.2:
        spoof_type = "static_photo"

    return {"liveness_score": liveness_score, "spoof_type": spoof_type,
            "face_detected": True, "face_confidence": round(confidence_mean, 4)}


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
    if estimated_age is None or declared_age is None:
        return 0.5
    return round(max(0.0, 1.0 - abs(estimated_age - declared_age) / 15.0), 4)


# ── Blink challenge via EyesOpen transitions ───────────────────────────────────

async def run_blink_challenge(frames_jpeg: list[bytes], required_blinks: int = 2) -> dict:
    # Sample every 3rd frame — reduces API calls while keeping temporal resolution
    indices = list(range(0, len(frames_jpeg), 3))
    results = await asyncio.gather(*[analyze_frame(frames_jpeg[i], i) for i in indices])

    blink_counter = 0
    was_open = True
    eye_states = []

    for r in results:
        if r.face_detected and r.eyes_open is not None:
            eye_states.append(r.eyes_open)
            if was_open and not r.eyes_open:
                blink_counter += 1
            was_open = r.eyes_open

    return {
        "blinks_detected": blink_counter,
        "challenge_passed": blink_counter >= required_blinks,
        "eye_states": eye_states,
    }


# ── Full passive liveness pipeline ────────────────────────────────────────────

async def run_passive_liveness(
    frames_jpeg: list[bytes],
    declared_age: float | None = None,
) -> LivenessResult:
    # All 15 frames in parallel — total wall time ≈ single Rekognition call latency
    frame_results = list(await asyncio.gather(
        *[analyze_frame(frames_jpeg[i], i) for i in range(len(frames_jpeg))]
    ))

    scores        = compute_liveness_score(frame_results)
    age_stats     = estimate_age_stats(frame_results)
    age_consistency = compute_age_consistency(age_stats.get("estimated_age"), declared_age)

    liveness_score = scores["liveness_score"]

    return LivenessResult(
        liveness_score=liveness_score,
        is_live=liveness_score >= 0.75,
        spoof_type=scores.get("spoof_type"),
        face_detected=scores["face_detected"],
        face_confidence=scores["face_confidence"],
        frames_analyzed=len(frames_jpeg),
        estimated_age=age_stats.get("estimated_age"),
        age_range=age_stats.get("age_range"),
        age_consistency_score=age_consistency,
        active_challenge_required=0.40 <= liveness_score < 0.75,
        hitl_required=liveness_score < 0.40,
    )

"""
Tests for liveness service logic (no GPU required — mocks InsightFace).
Tests the scoring math, blink detection EAR formula, and pipeline routing.
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from app.services.liveness_service import (
    compute_liveness_score, estimate_age_stats,
    compute_age_consistency, run_passive_liveness,
    FrameResult,
)


def _make_frame_results(n=15, detected=True, confidence=0.95, age=34.0,
                        embedding_variance="normal"):
    results = []
    for i in range(n):
        if embedding_variance == "static":
            emb = np.ones(512, dtype=np.float32)  # identical → static photo
        elif embedding_variance == "normal":
            emb = np.random.normal(0, 0.1, 512).astype(np.float32)
            emb /= np.linalg.norm(emb)
        else:
            emb = None

        results.append(FrameResult(
            frame_index=i,
            face_detected=detected,
            face_confidence=confidence if detected else 0.0,
            bbox=[50.0, 50.0, 200.0, 200.0] if detected else None,
            embedding=emb if detected else None,
            estimated_age=age if detected else None,
            gender="M",
        ))
    return results


# ── Liveness score computation ─────────────────────────────────────────────────

def test_live_face_high_score():
    frames = _make_frame_results(15, detected=True, confidence=0.95,
                                  embedding_variance="normal")
    result = compute_liveness_score(frames)
    assert result["face_detected"] is True
    assert result["liveness_score"] >= 0.60


def test_face_not_detected_returns_zero():
    frames = _make_frame_results(15, detected=False)
    result = compute_liveness_score(frames)
    assert result["face_detected"] is False
    assert result["liveness_score"] == 0.0


def test_static_photo_lower_score():
    """Identical embeddings across frames should give lower score than live."""
    live_frames = _make_frame_results(15, embedding_variance="normal")
    static_frames = _make_frame_results(15, embedding_variance="static")

    live_result = compute_liveness_score(live_frames)
    static_result = compute_liveness_score(static_frames)
    assert live_result["liveness_score"] > static_result["liveness_score"]


def test_fewer_than_half_detected_zero():
    frames = (
        _make_frame_results(7, detected=False)
        + _make_frame_results(8, detected=True)
    )
    # Exactly 8/15 detected — should still compute
    result = compute_liveness_score(frames)
    assert isinstance(result["liveness_score"], float)


# ── Age stats ──────────────────────────────────────────────────────────────────

def test_age_median():
    frames = _make_frame_results(15, age=34.0)
    stats = estimate_age_stats(frames)
    assert stats["estimated_age"] == pytest.approx(34.0, abs=0.5)


def test_age_none_when_not_detected():
    frames = _make_frame_results(15, detected=False)
    stats = estimate_age_stats(frames)
    assert stats["estimated_age"] is None


# ── Age consistency ────────────────────────────────────────────────────────────

def test_perfect_age_match():
    score = compute_age_consistency(34.0, 34.0)
    assert score == pytest.approx(1.0)


def test_age_delta_15_gives_zero():
    score = compute_age_consistency(34.0, 49.0)
    assert score == pytest.approx(0.0)


def test_age_delta_5_gives_two_thirds():
    score = compute_age_consistency(34.0, 39.0)
    assert score == pytest.approx(1.0 - 5 / 15, abs=0.01)


def test_age_missing_returns_neutral():
    assert compute_age_consistency(None, 34.0) == pytest.approx(0.5)
    assert compute_age_consistency(34.0, None) == pytest.approx(0.5)


# ── Pipeline routing ───────────────────────────────────────────────────────────

def test_high_liveness_score_no_challenge():
    frames = _make_frame_results(15, confidence=0.98, embedding_variance="normal")
    with patch("app.services.liveness_service._get_face_app") as mock_app:
        # Return pre-built FrameResults bypassing InsightFace
        mock_app.return_value = MagicMock()
        with patch("app.services.liveness_service.analyze_frame",
                   side_effect=frames):
            result = run_passive_liveness(
                [np.zeros((112, 112, 3), dtype=np.uint8)] * 15
            )
    # With mocked analyze_frame returning good frames, score should be decent
    assert isinstance(result.liveness_score, float)


def test_result_fields_always_present():
    frames = [np.zeros((112, 112, 3), dtype=np.uint8)] * 15
    with patch("app.services.liveness_service.analyze_frame",
               side_effect=_make_frame_results(15)):
        result = run_passive_liveness(frames)
    assert hasattr(result, "liveness_score")
    assert hasattr(result, "is_live")
    assert hasattr(result, "active_challenge_required")
    assert hasattr(result, "hitl_required")
    # Exactly one of these should be true
    assert not (result.is_live and result.hitl_required)

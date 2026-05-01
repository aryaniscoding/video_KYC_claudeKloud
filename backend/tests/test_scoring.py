"""Tests for pre-session risk scoring."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.scoring_service import (
    _compute_ip_risk, _compute_device_risk,
    compute_pre_session_scores, update_geo_risk_with_pincode,
)


# ── IP risk ────────────────────────────────────────────────────────────────────

def test_clean_ip_zero_risk():
    score = _compute_ip_risk({"is_vpn": False, "is_tor": False,
                               "is_datacenter": False, "is_blacklisted": False})
    assert score == 0.0


def test_vpn_adds_risk():
    score = _compute_ip_risk({"is_vpn": True, "is_tor": False,
                               "is_datacenter": False, "is_blacklisted": False})
    assert score == pytest.approx(0.30)


def test_tor_adds_more_risk():
    score = _compute_ip_risk({"is_vpn": False, "is_tor": True,
                               "is_datacenter": False, "is_blacklisted": False})
    assert score == pytest.approx(0.40)


def test_blacklisted_ip_max_risk():
    score = _compute_ip_risk({"is_vpn": False, "is_tor": False,
                               "is_datacenter": False, "is_blacklisted": True})
    assert score == pytest.approx(0.50)


def test_combined_risk_capped_at_1():
    score = _compute_ip_risk({"is_vpn": True, "is_tor": True,
                               "is_datacenter": True, "is_blacklisted": True})
    assert score == pytest.approx(1.0)


# ── Device risk ────────────────────────────────────────────────────────────────

def test_no_fingerprint_gives_moderate_risk():
    assert _compute_device_risk(None) == pytest.approx(0.3)


def test_known_fingerprint_low_risk():
    assert _compute_device_risk("fp_abc123") == pytest.approx(0.0)


# ── Full scoring pipeline ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clean_session_scores():
    with patch("app.services.scoring_service._fetch_ip_flags",
               new=AsyncMock(return_value={
                   "is_vpn": False, "is_tor": False,
                   "is_datacenter": False, "is_blacklisted": False,
               })):
        result = await compute_pre_session_scores(
            latitude=18.52, longitude=73.85,
            ip_address="1.2.3.4", pincode=None,
            device_fingerprint="fp_abc",
        )
    assert result["hard_stop"] is False
    assert result["ip_risk_score"] == 0.0
    assert result["device_risk_score"] == 0.0


@pytest.mark.asyncio
async def test_prohibited_ip_hard_stop():
    with patch("app.services.scoring_service._GOVT_PROHIBITED_IPS", {"10.0.0.1"}):
        result = await compute_pre_session_scores(
            latitude=None, longitude=None,
            ip_address="10.0.0.1", pincode=None,
            device_fingerprint=None,
        )
    assert result["hard_stop"] is True
    assert result["hard_stop_reason"] == "prohibited_ip"


# ── Pincode risk update ────────────────────────────────────────────────────────

def test_clean_pincode_no_change():
    original = 0.10
    updated = update_geo_risk_with_pincode(original, "411027")
    assert updated == pytest.approx(original)


def test_excluded_pincode_increases_risk():
    with patch("app.services.scoring_service._EXCLUDED_PINCODES", {"999999"}):
        updated = update_geo_risk_with_pincode(0.10, "999999")
    assert updated > 0.10
    assert updated <= 1.0

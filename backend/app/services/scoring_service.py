"""
Pre-Session Risk Scoring — Phase 3 of the blueprint.

Computes geo_risk_score, ip_risk_score, device_risk_score.
All scores are 0.0–1.0 ML features — NOT hard-reject gates (except blacklisted IPs).
"""
import logging
from pathlib import Path

import geoip2.database
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Government-prohibited IP ranges (placeholder — extend with real list)
_GOVT_PROHIBITED_IPS: set[str] = set()

# High-risk pincode list (placeholder — loaded from config/pincode_exclusions.txt)
_EXCLUDED_PINCODES: set[str] = set()

# Tor exit node IPs — refreshed from https://check.torproject.org/torbulkexitlist
_TOR_EXIT_NODES: set[str] = set()


def _load_tor_list() -> None:
    tor_file = Path("/app/data/tor_exit_nodes.txt")
    if tor_file.exists():
        _TOR_EXIT_NODES.update(tor_file.read_text().splitlines())


_load_tor_list()


async def _fetch_ip_flags(ip: str) -> dict:
    """
    ip-api.com free tier: 45 req/min, no API key needed.
    Returns proxy/vpn/tor/datacenter flags.
    """
    if ip in ("127.0.0.1", "::1", "unknown"):
        return {"is_vpn": False, "is_tor": False, "is_datacenter": False, "is_blacklisted": False}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,proxy,hosting,org,countryCode,city,regionName,zip,lat,lon"},
            )
        data = resp.json()
        if data.get("status") != "success":
            return {"is_vpn": False, "is_tor": False, "is_datacenter": False, "is_blacklisted": False}

        is_tor = ip in _TOR_EXIT_NODES
        return {
            "is_vpn": bool(data.get("proxy")),
            "is_tor": is_tor,
            "is_datacenter": bool(data.get("hosting")),
            "is_blacklisted": ip in _GOVT_PROHIBITED_IPS,
            "country_code": data.get("countryCode"),
            "ip_city": data.get("city"),
            "ip_state": data.get("regionName"),
            "ip_zip": data.get("zip"),
            "ip_latitude": data.get("lat"),
            "ip_longitude": data.get("lon"),
        }
    except Exception as exc:
        logger.warning("ip-api lookup failed for %s: %s", ip, exc)
        return {"is_vpn": False, "is_tor": False, "is_datacenter": False, "is_blacklisted": False}


def _compute_ip_risk(flags: dict) -> float:
    score = (
        (0.30 if flags.get("is_vpn") else 0.0)
        + (0.40 if flags.get("is_tor") else 0.0)
        + (0.50 if flags.get("is_blacklisted") else 0.0)
        + (0.25 if flags.get("is_datacenter") else 0.0)
    )
    return min(score, 1.0)


def _compute_geo_risk(
    latitude: float | None,
    longitude: float | None,
    ip_city: str | None,
    ip_state: str | None,
) -> float:
    """
    Formula: city_mismatch×0.40 + pincode_risk_tier×0.40 + state_flag×0.20
    When GPS is available, city_mismatch is GPS-city vs IP-city.
    Without GPS, we can't compute mismatch — default to 0.10 (slight uncertainty).
    """
    if latitude is None or longitude is None:
        return 0.10

    # Reverse geocode GPS coords to city/state using GeoIP2 (same DB, lookup by lat/lon not available)
    # For now we use a simple distance heuristic: if GPS and IP give same country, low risk.
    # Real implementation: use a reverse geocoding service or MaxMind Insights
    gps_city = _reverse_geocode_city(latitude, longitude)

    city_mismatch_score = 0.0
    state_flag = 0.0

    if ip_city and gps_city:
        # Normalize to lowercase for comparison
        if ip_city.lower() not in gps_city.lower() and gps_city.lower() not in ip_city.lower():
            city_mismatch_score = 0.6   # cities don't match at all

    pincode_risk_tier = 0.0   # populated later when pincode extracted from Q&A

    return min(city_mismatch_score * 0.40 + pincode_risk_tier * 0.40 + state_flag * 0.20, 1.0)


def _reverse_geocode_city(lat: float, lon: float) -> str | None:
    """Use MaxMind GeoLite2 for approximate city from GPS coords — best effort."""
    db_path = settings.geoip_db_path
    if not Path(db_path).exists():
        return None
    try:
        # GeoIP2 doesn't do reverse GPS→city; this is a placeholder.
        # In production: use Google Maps Geocoding API (free tier: 200$/month credit) or Nominatim.
        return None
    except Exception:
        return None


def _compute_device_risk(device_fingerprint: str | None) -> float:
    """
    0.0 = known good device
    0.3 = new/unknown device
    0.8 = device on fraud blacklist
    """
    if not device_fingerprint:
        return 0.3
    # TODO: check device_fingerprint against fraud blacklist DB
    return 0.0


async def compute_pre_session_scores(
    latitude: float | None,
    longitude: float | None,
    ip_address: str,
    pincode: str | None,
    device_fingerprint: str | None,
) -> dict:
    # Hard stop: govt-prohibited IP
    if ip_address in _GOVT_PROHIBITED_IPS:
        return {
            "geo_risk_score": 1.0,
            "ip_risk_score": 1.0,
            "device_risk_score": 0.0,
            "hard_stop": True,
            "hard_stop_reason": "prohibited_ip",
        }

    ip_flags = await _fetch_ip_flags(ip_address)
    ip_risk_score = _compute_ip_risk(ip_flags)
    geo_risk_score = _compute_geo_risk(latitude, longitude, ip_flags.get("ip_city"), ip_flags.get("ip_state"))
    device_risk_score = _compute_device_risk(device_fingerprint)

    return {
        "geo_risk_score": round(geo_risk_score, 4),
        "ip_risk_score": round(ip_risk_score, 4),
        "device_risk_score": round(device_risk_score, 4),
        "hard_stop": False,
        "hard_stop_reason": None,
        "ip_latitude": ip_flags.get("ip_latitude"),
        "ip_longitude": ip_flags.get("ip_longitude"),
    }


def update_geo_risk_with_pincode(geo_risk_score: float, pincode: str) -> float:
    """Called after Q&A extracts pincode. Re-computes pincode_risk_tier component."""
    pincode_risk_tier = 1.0 if pincode in _EXCLUDED_PINCODES else 0.0
    # Add pincode contribution (0.40 weight) without changing city component
    updated = min(geo_risk_score + pincode_risk_tier * 0.40, 1.0)
    return round(updated, 4)

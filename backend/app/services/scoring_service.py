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


async def _compute_geo_risk(
    latitude: float | None,
    longitude: float | None,
    ip_city: str | None,
    ip_state: str | None,
) -> float:
    """
    Formula: city_mismatch×0.40 + pincode_risk_tier×0.40 + state_flag×0.20
    When GPS is available, reverse-geocodes via Nominatim and compares to IP city.
    Without GPS, falls back to 0.10 (slight uncertainty).
    """
    if latitude is None or longitude is None:
        return 0.10

    gps_city, gps_state = await _reverse_geocode_city_nominatim(latitude, longitude)

    city_mismatch_score = 0.0
    state_flag = 0.0

    if ip_city and gps_city:
        if ip_city.lower() not in gps_city.lower() and gps_city.lower() not in ip_city.lower():
            city_mismatch_score = 0.6

    if ip_state and gps_state:
        if ip_state.lower() not in gps_state.lower() and gps_state.lower() not in ip_state.lower():
            state_flag = 0.4

    pincode_risk_tier = 0.0   # populated later when pincode extracted from Q&A

    return min(city_mismatch_score * 0.40 + pincode_risk_tier * 0.40 + state_flag * 0.20, 1.0)


async def _reverse_geocode_city_nominatim(lat: float, lon: float) -> tuple[str | None, str | None]:
    """
    Reverse geocode GPS coordinates to (city, state) using OpenStreetMap Nominatim.
    Free, no API key required. Returns (city, state) or (None, None) on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
                headers={"User-Agent": "PoonawallFincorpKYC/1.0"},
            )
        data = resp.json()
        addr = data.get("address", {})
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("county")
        )
        state = addr.get("state")
        return city, state
    except Exception as exc:
        logger.warning("Nominatim reverse geocode failed (%.5f, %.5f): %s", lat, lon, exc)
        return None, None


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
    geo_risk_score = await _compute_geo_risk(latitude, longitude, ip_flags.get("ip_city"), ip_flags.get("ip_state"))
    device_risk_score = _compute_device_risk(device_fingerprint)

    return {
        "geo_risk_score": round(geo_risk_score, 4),
        "ip_risk_score": round(ip_risk_score, 4),
        "device_risk_score": round(device_risk_score, 4),
        "hard_stop": False,
        "hard_stop_reason": None,
        "ip_latitude": ip_flags.get("ip_latitude"),
        "ip_longitude": ip_flags.get("ip_longitude"),
        "ip_city": ip_flags.get("ip_city"),
        "ip_state": ip_flags.get("ip_state"),
        "ip_zip": ip_flags.get("ip_zip"),
    }


def update_geo_risk_with_pincode(geo_risk_score: float, pincode: str) -> float:
    """Called after Q&A extracts pincode. Re-computes pincode_risk_tier component."""
    pincode_risk_tier = 1.0 if pincode in _EXCLUDED_PINCODES else 0.0
    updated = min(geo_risk_score + pincode_risk_tier * 0.40, 1.0)
    return round(updated, 4)


def compute_location_mismatch_score(
    stated_city: str | None,
    stated_state: str | None,
    stated_pincode: str | None,
    ip_city: str | None,
    ip_state: str | None,
    ip_zip: str | None,
) -> float:
    """
    Compares user's stated location (from Q&A) against IP-derived location.
    Returns a mismatch risk score 0.0–1.0.

    Weights:
      state mismatch  × 0.40  (strongest signal — state is hard to fake accidentally)
      city mismatch   × 0.35
      zip prefix mis  × 0.25  (first 3 digits of Indian pincode = district)
    """
    if not any([ip_city, ip_state, ip_zip]):
        return 0.0  # no IP data to compare against

    def _fuzzy_no_match(a: str | None, b: str | None) -> bool:
        if not a or not b:
            return False  # missing data → don't penalise
        a, b = a.strip().lower(), b.strip().lower()
        return a not in b and b not in a

    state_mismatch = 1.0 if _fuzzy_no_match(stated_state, ip_state) else 0.0
    city_mismatch  = 1.0 if _fuzzy_no_match(stated_city, ip_city) else 0.0

    zip_mismatch = 0.0
    if stated_pincode and ip_zip and len(stated_pincode) >= 3 and len(ip_zip) >= 3:
        if stated_pincode[:3] != ip_zip[:3]:
            zip_mismatch = 1.0

    score = state_mismatch * 0.40 + city_mismatch * 0.35 + zip_mismatch * 0.25

    if score > 0:
        logger.warning(
            "Location mismatch — stated: %s/%s/%s  IP-derived: %s/%s/%s  score=%.2f",
            stated_city, stated_state, stated_pincode,
            ip_city, ip_state, ip_zip, score,
        )

    return round(min(score, 1.0), 4)

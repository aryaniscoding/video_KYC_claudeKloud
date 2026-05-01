"""Tests for JWT session token generation and validation."""
import time
import uuid
import pytest
from unittest.mock import patch

from app.services.jwt_service import (
    create_session_token, decode_session_token,
    create_admin_token, decode_admin_token,
    TokenExpiredError, TokenTamperedError,
)


def _make_token(**kwargs):
    defaults = dict(
        customer_id=uuid.uuid4(),
        phone_hash="abc123",
        product_code="PL_STANDARD",
        max_amount=500000.0,
    )
    defaults.update(kwargs)
    return create_session_token(**defaults)


# ── Session tokens ─────────────────────────────────────────────────────────────

def test_create_and_decode_session_token():
    cid = uuid.uuid4()
    token, payload = create_session_token(
        customer_id=cid,
        phone_hash="deadbeef",
        product_code="PL_STANDARD",
        max_amount=400000.0,
    )
    assert token
    decoded = decode_session_token(token)
    assert decoded["sub"] == str(cid)
    assert decoded["product_code"] == "PL_STANDARD"
    assert decoded["max_amount"] == 400000.0
    assert "jti" in decoded
    assert "sig" in decoded


def test_session_token_has_hmac_sig():
    token, payload = _make_token()
    assert len(payload["sig"]) == 64   # SHA-256 hex


def test_expired_token_raises():
    token, _ = _make_token(ttl_seconds=1)
    time.sleep(2)
    with pytest.raises(TokenExpiredError):
        decode_session_token(token)


def test_tampered_token_raises():
    token, _ = _make_token()
    # Flip one char in the token body
    parts = token.split(".")
    tampered_payload = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    tampered = ".".join([parts[0], tampered_payload, parts[2]])
    with pytest.raises((TokenTamperedError, Exception)):
        decode_session_token(tampered)


def test_wrong_secret_raises():
    token, _ = _make_token()
    with patch("app.services.jwt_service.settings") as mock_settings:
        mock_settings.jwt_secret = "wrong_secret_entirely"
        mock_settings.jwt_algorithm = "HS256"
        with pytest.raises((TokenTamperedError, Exception)):
            decode_session_token(token)


def test_ttl_is_respected():
    token, payload = _make_token(ttl_seconds=3600)
    decoded = decode_session_token(token)
    assert decoded["exp"] - decoded["iat"] == 3600


# ── Admin tokens ───────────────────────────────────────────────────────────────

def test_admin_token_round_trip():
    admin_id = uuid.uuid4()
    token = create_admin_token(admin_id, "admin@test.com")
    decoded = decode_admin_token(token)
    assert decoded["sub"] == str(admin_id)
    assert decoded["role"] == "admin"
    assert decoded["email"] == "admin@test.com"


def test_admin_token_has_8h_expiry():
    token = create_admin_token(uuid.uuid4(), "x@x.com")
    decoded = decode_admin_token(token)
    ttl = decoded["exp"] - decoded["iat"]
    assert 28700 < ttl <= 28800   # ~8 hours ± small jitter

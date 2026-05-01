"""
Session token service.

Tokens are HMAC-SHA256 signed JWTs. The payload is frozen at creation time —
any field change (policy_ver, product_code, etc.) invalidates the signature.
"""
import hashlib
import hmac
import uuid
from datetime import datetime, timezone, timedelta

import jwt
from jwt import InvalidTokenError

from app.config import get_settings

settings = get_settings()


class TokenError(Exception):
    pass


class TokenExpiredError(TokenError):
    pass


class TokenTamperedError(TokenError):
    pass


def _body_signature(payload: dict) -> str:
    """Deterministic HMAC over the stable payload fields."""
    stable = "|".join(str(payload[k]) for k in sorted(payload.keys()) if k != "sig")
    return hmac.new(settings.jwt_secret.encode(), stable.encode(), hashlib.sha256).hexdigest()


def create_session_token(
    customer_id: uuid.UUID,
    phone_hash: str,
    product_code: str,
    max_amount: float,
    policy_ver: str = "v1.0",
    ttl_seconds: int | None = None,
) -> tuple[str, dict]:
    """
    Returns (encoded_jwt, payload_dict).
    payload_dict is stored in the DB so we can validate without re-decoding.
    """
    ttl = ttl_seconds or settings.session_token_ttl_seconds
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())

    payload = {
        "jti": session_id,
        "sub": str(customer_id),
        "phone_hash": phone_hash,
        "product_code": product_code,
        "max_amount": max_amount,
        "policy_ver": policy_ver,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    payload["sig"] = _body_signature(payload)

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, payload


def decode_session_token(token: str) -> dict:
    """
    Decode and fully validate a session token.
    Raises TokenExpiredError, TokenTamperedError, or TokenError.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["jti", "sub", "exp", "iat", "sig"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Session link has expired") from e
    except InvalidTokenError as e:
        raise TokenTamperedError("Token is invalid or tampered") from e

    expected_sig = _body_signature({k: v for k, v in payload.items() if k != "sig"})
    if not hmac.compare_digest(payload["sig"], expected_sig):
        raise TokenTamperedError("Token signature mismatch — possible replay attack")

    return payload


# ── Admin access tokens (short-lived, simple) ─────────────────────────────────

def create_admin_token(admin_id: uuid.UUID, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "email": email,
        "role": "admin",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_admin_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "role", "exp"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Admin session expired — please log in again") from e
    except InvalidTokenError as e:
        raise TokenTamperedError("Invalid admin token") from e

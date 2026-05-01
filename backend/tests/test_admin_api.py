"""Tests for admin REST endpoints."""
import hashlib
import uuid
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from passlib.context import CryptContext

from app.models import AdminUser, Customer

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest_asyncio.fixture
async def admin_user(db):
    admin = AdminUser(
        id=uuid.uuid4(),
        username="testadmin",
        email="admin@test.com",
        password_hash=pwd_ctx.hash("Password123"),
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    return admin


@pytest_asyncio.fixture
async def auth_headers(client, admin_user):
    resp = await client.post("/admin/login", json={
        "email": "admin@test.com",
        "password": "Password123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Login ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    resp = await client.post("/admin/login", json={
        "email": "admin@test.com",
        "password": "Password123",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    resp = await client.post("/admin/login", json={
        "email": "admin@test.com",
        "password": "WrongPassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    resp = await client.post("/admin/login", json={
        "email": "nobody@test.com",
        "password": "anything",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client):
    resp = await client.get("/admin/customers")
    assert resp.status_code == 403


# ── Customer CRUD ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_customer(client, auth_headers):
    resp = await client.post("/admin/customers", json={
        "name": "Ramesh Kumar",
        "email": "ramesh@example.com",
        "phone": "9876543210",
        "credit_score": 742,
    }, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Ramesh Kumar"
    assert body["phone_last4"] == "3210"


@pytest.mark.asyncio
async def test_create_customer_idempotent(client, auth_headers):
    """Same phone number returns existing customer without error."""
    payload = {"name": "User A", "email": "a@a.com", "phone": "1111111111"}
    r1 = await client.post("/admin/customers", json=payload, headers=auth_headers)
    r2 = await client.post("/admin/customers", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_list_customers(client, auth_headers):
    # Create one first
    await client.post("/admin/customers", json={
        "name": "List Test", "email": "list@t.com", "phone": "2222222222",
    }, headers=auth_headers)
    resp = await client.get("/admin/customers", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_create_customer_invalid_phone(client, auth_headers):
    """Phone must be exactly 10 digits."""
    resp = await client.post("/admin/customers", json={
        "name": "Bad Phone", "email": "b@b.com", "phone": "123",
    }, headers=auth_headers)
    assert resp.status_code == 422


# ── Send link ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_link_creates_session(client, auth_headers):
    # Create customer first
    r = await client.post("/admin/customers", json={
        "name": "Link User", "email": "link@t.com", "phone": "3333333333",
    }, headers=auth_headers)
    customer_id = r.json()["id"]

    with patch("app.api.admin.send_kyc_link_email", new=AsyncMock(return_value=None)):
        resp = await client.post("/admin/send-link", json={
            "customer_id": customer_id,
            "ttl_hours": 24,
        }, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert "kyc_url" in body
    assert "session_id" in body


@pytest.mark.asyncio
async def test_send_link_unknown_customer(client, auth_headers):
    resp = await client.post("/admin/send-link", json={
        "customer_id": str(uuid.uuid4()),
        "ttl_hours": 24,
    }, headers=auth_headers)
    assert resp.status_code == 404

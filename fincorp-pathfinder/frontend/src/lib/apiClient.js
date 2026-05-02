/**
 * Unified API client — delegates to mock or real backend based on VITE_USE_MOCK.
 *
 * Session flow components import from here instead of mock/api directly.
 * Admin components also import from here.
 */

import * as mockApi from "@/mock/api";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ── Helpers ─────────────────────────────────────────────────────

function adminHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("lw_admin_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(path, { headers: extraHeaders = {}, ...rest } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...extraHeaders },
    ...rest,
  });
  if (!res.ok) {
    const err = new Error(`API ${res.status}`);
    err.status = res.status;
    try {
      const body = await res.json();
      // FastAPI 422 detail is an array of {loc, msg, type} objects
      if (Array.isArray(body.detail)) {
        err.detail = body.detail.map((e) => `${e.loc?.slice(1).join(".")||"field"}: ${e.msg}`).join("; ");
      } else {
        err.detail = body.detail || body.message || null;
      }
    } catch { /* no body */ }
    throw err;
  }
  return res.json();
}

// ── Session Initialisation ──────────────────────────────────────
// GET /session/{token}?latitude=...&longitude=...&device_fingerprint=...

export async function getSession(token, { latitude, longitude, deviceFingerprint } = {}) {
  if (USE_MOCK) return mockApi.getSession(token);

  const params = new URLSearchParams();
  if (latitude != null) params.set("latitude", latitude);
  if (longitude != null) params.set("longitude", longitude);
  if (deviceFingerprint) params.set("device_fingerprint", deviceFingerprint);
  const qs = params.toString();
  return apiFetch(`/session/${token}${qs ? `?${qs}` : ""}`);
}

// ── Offer Polling ───────────────────────────────────────────────
// GET /session/{session_id}/offer — poll every 3s after pipeline_started
// Returns { processing: true } for 202, or the full offer for 200.

export async function pollOffer(sessionId) {
  if (USE_MOCK) return mockApi.getOffer(sessionId);

  const res = await fetch(`${API_BASE}/session/${sessionId}/offer`);
  if (res.status === 202) return { processing: true };
  if (!res.ok) {
    const err = new Error(`API ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// ── PDF Download ────────────────────────────────────────────────
// GET /offers/{offer_ref_id}/download

export async function getDownloadUrl(offerRefId) {
  if (USE_MOCK) return mockApi.getDownloadUrl(offerRefId);
  return apiFetch(`/offers/${offerRefId}/download`);
}

// ── PAN Submission ──────────────────────────────────────────────
// POST /session/{session_id}/pan

export async function submitPan(sessionId, panNumber) {
  if (USE_MOCK) return { success: true };
  return apiFetch(`/session/${sessionId}/pan`, {
    method: "POST",
    body: JSON.stringify({ pan_number: panNumber }),
  });
}

// ── WebSocket URL builder ───────────────────────────────────────

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";

export function wsUrl(path) {
  if (USE_MOCK) return `ws://localhost:8000${path}`;
  return `${WS_BASE}${path}`;
}

// ── Admin — Auth ────────────────────────────────────────────────
// POST /admin/login

export async function adminLogin(email, password) {
  if (USE_MOCK) return mockApi.adminLogin(email, password);
  const r = await apiFetch("/admin/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  // Map backend shape { access_token, name, email } → { token, name, email }
  return { token: r.access_token, name: r.name || r.email, email: r.email };
}

// ── Admin — Customers ───────────────────────────────────────────
// GET /admin/customers

export async function getCustomers() {
  if (USE_MOCK) return mockApi.getCustomers();
  return apiFetch("/admin/customers", { headers: adminHeaders() });
}

// POST /admin/customers

export async function createCustomer(payload) {
  if (USE_MOCK) return mockApi.createCustomer ? mockApi.createCustomer(payload) : null;
  return apiFetch("/admin/customers", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  });
}

// ── Admin — Send / Resend Link ──────────────────────────────────
// POST /admin/send-link

export async function sendLink(customerId, _email, expiryHours = 24) {
  if (USE_MOCK) return mockApi.sendLink(customerId, _email, expiryHours);
  const r = await apiFetch("/admin/send-link", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({ customer_id: customerId, ttl_hours: expiryHours }),
  });
  return { session_url: r.kyc_url, ...r };
}

// POST /admin/resend-link

// customerId is the customer UUID (c.id from the table row)
export async function resendLink(customerId) {
  if (USE_MOCK) return mockApi.resendLink(customerId);
  const r = await apiFetch("/admin/resend-link", {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({ customer_id: customerId }),
  });
  return { session_url: r.kyc_url, ...r };
}

// ── Admin — Session Status ──────────────────────────────────────
// GET /admin/session-status/{session_id}

export async function getSessionStatus(sessionId) {
  if (USE_MOCK) return mockApi.getSessionStatus(sessionId);
  return apiFetch(`/admin/session-status/${sessionId}`, { headers: adminHeaders() });
}

// ── Admin — HITL Queue ──────────────────────────────────────────
// GET /admin/hitl-queue

export async function getHitlQueue() {
  if (USE_MOCK) return mockApi.getHitlQueue();
  return apiFetch("/admin/hitl-queue", { headers: adminHeaders() });
}

// POST /admin/hitl/{session_id}/decision

export async function submitHitlDecision(sessionId, decision, notes = "") {
  if (USE_MOCK) return { status: "ok" };
  return apiFetch(`/admin/hitl/${sessionId}/decision`, {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify({ decision, notes }),
  });
}

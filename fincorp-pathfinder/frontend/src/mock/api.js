// Mock API layer - all functions return Promises with 700ms delay
const delay = (ms = 700) => new Promise((r) => setTimeout(r, ms));

let customersStore = null;
function seedCustomers() {
  if (customersStore) return customersStore;
  customersStore = [
    { id: "c1", name: "Ramesh Kumar", phone: "+91 98765 43210", product: "PL_STANDARD", created_date: "28 Apr 2026", status: "Link Sent" },
    { id: "c2", name: "Anjali Mehta", phone: "+91 98220 11223", product: "PL_PREMIUM", created_date: "27 Apr 2026", status: "In Progress" },
    { id: "c3", name: "Vikram Singh", phone: "+91 99887 76655", product: "PL_STANDARD", created_date: "26 Apr 2026", status: "Approved" },
    { id: "c4", name: "Pooja Desai", phone: "+91 97654 32109", product: "PL_LITE", created_date: "26 Apr 2026", status: "Declined" },
    { id: "c5", name: "Suresh Patil", phone: "+91 90909 80808", product: "PL_STANDARD", created_date: "25 Apr 2026", status: "HITL" },
    { id: "c6", name: "Neha Iyer", phone: "+91 93456 78901", product: "PL_PREMIUM", created_date: "24 Apr 2026", status: "Expired" },
    { id: "c7", name: "Arjun Reddy", phone: "+91 91234 55667", product: "PL_STANDARD", created_date: "23 Apr 2026", status: "Dropped" },
    { id: "c8", name: "Kavita Joshi", phone: "+91 99001 22334", product: "PL_LITE", created_date: "22 Apr 2026", status: "Processing" },
  ];
  return customersStore;
}

export const getSession = async (token) => {
  await delay();
  return {
    session_id: "550e8400-e29b-41d4-a716-446655440000",
    customer_id: "b21a7c6d-mock-0001",
    customer_name: "Ramesh Kumar",
    product_code: "PL_STANDARD",
    is_fast_track: false,
    pre_fill: null,
    scores: {
      geo_risk_score: 0.08,
      ip_risk_score: 0.05,
      device_risk_score: 0.03,
      hard_stop: false,
      hard_stop_reason: null,
    },
    livekit_token: "mock-livekit-token",
    livekit_url: "wss://livekit.example.com",
    policy_ver: "v1.0",
    token,
  };
};

export const adminLogin = async (email, _password) => {
  await delay();
  return { token: "mock-admin-jwt", name: "Priya Sharma", email };
};

export const getCustomers = async () => {
  await delay();
  return [...seedCustomers()];
};

export const sendLink = async (customerId, email, expiryHours) => {
  await delay();
  const list = seedCustomers();
  const c = list.find((x) => x.id === customerId);
  if (c) c.status = "Link Sent";

  const sessionUrl = "https://loanwizard.in/session/mock-token-abc123";
  const mockResponse = { session_url: sessionUrl, customerId, email, expiryHours };

  // Attempt real email send in the background — never blocks or breaks UI
  const emailServerUrl = import.meta.env.VITE_EMAIL_SERVER_URL;
  if (emailServerUrl && email) {
    const customerName = c?.name || "Customer";
    fetch(`${emailServerUrl}/api/send-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ toEmail: email, customerName, sessionUrl, expiryHours }),
    }).catch(() => {
      // Silently swallow — email server may not be running
    });
  }

  return mockResponse;
};

export const resendLink = async (customerId) => {
  return sendLink(customerId, "", 24);
};

export const getSessionStatus = async (sessionId) => {
  await delay();
  return {
    sessionId,
    status: "In Progress",
    timeline: [
      { event: "Link sent", time: "30 Apr 2026, 10:00 AM" },
      { event: "Session started", time: "30 Apr 2026, 10:15 AM" },
      { event: "Face check passed", time: "30 Apr 2026, 10:16 AM" },
      { event: "Q&A in progress (Q4/8)", time: "30 Apr 2026, 10:20 AM" },
    ],
  };
};

export const getHitlQueue = async () => {
  await delay();
  return [
    { id: "h1", customer_name: "Suresh Patil", session_id: "sess-9981", flagged_at: "30 Apr 2026, 09:42 AM", flag_reason: "Liveness score borderline (0.62)" },
    { id: "h2", customer_name: "Anita Shah", session_id: "sess-9982", flagged_at: "30 Apr 2026, 10:01 AM", flag_reason: "Application velocity: 4 apps in 30 days" },
    { id: "h3", customer_name: "Rohit Mehra", session_id: "sess-9983", flagged_at: "30 Apr 2026, 10:18 AM", flag_reason: "Age inconsistency detected" },
  ];
};

let offerCallCount = {};
export const getOffer = async (sessionId) => {
  await delay(200);
  offerCallCount[sessionId] = (offerCallCount[sessionId] || 0) + 1;
  return {
    eligible: true,
    approved_amount: 400000,
    interest_rate_pct: 12.5,
    recommended_tenure_months: 24,
    emi_options: [
      { tenure_months: 12, emi_amount: 35611, total_payable: 427332 },
      { tenure_months: 24, emi_amount: 18942, total_payable: 454608 },
      { tenure_months: 36, emi_amount: 13332, total_payable: 479952 },
    ],
    processing_fee_pct: 2.0,
    offer_ref_id: "OFR-20260430-ABC123",
    offer_valid_until: "2026-05-30T10:15:00+00:00",
    approval_reasons: [
      "Strong credit history (score 742)",
      "Stable employment — 6 years at TCS",
      "Low existing EMI obligations (FOIR: 0.14)",
    ],
    risk_band: "MEDIUM_LOW",
  };
};

export const getDownloadUrl = async (offerRefId) => {
  await delay(300);
  return { download_url: `https://example.com/mock-offer-${offerRefId}.pdf` };
};

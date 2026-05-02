<div align="center">

# 🟠 Loan Wizard — Frontend
### React · TanStack · Vite · Tailwind CSS · LiveKit WebRTC

[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-7.3-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![TanStack](https://img.shields.io/badge/TanStack-Router+Query-FF4154?style=for-the-badge)](https://tanstack.com)
[![Tailwind](https://img.shields.io/badge/Tailwind-4.2-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Railway](https://img.shields.io/badge/Hosted_on-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

> The complete UI for Loan Wizard — both the customer-facing KYC session and the  
> admin dashboard for loan officers.

</div>

---

## 📁 Directory Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── SessionFlow.jsx         → Customer KYC session (all steps)
│   │   ├── AdminCustomers.jsx      → Admin: customer management table
│   │   ├── AdminHitl.jsx           → Admin: manual review queue + decisions
│   │   └── AdminLogin.jsx          → Admin: login page
│   │
│   ├── components/
│   │   ├── admin/
│   │   │   ├── SessionStatusDrawer.jsx  → Full session detail modal
│   │   │   ├── CustomerTable.jsx        → Customer list table
│   │   │   ├── AddCustomerModal.jsx     → Create customer (+ duplicate handling)
│   │   │   ├── SendLinkModal.jsx        → Send / resend KYC link
│   │   │   ├── StatusBadge.jsx          → Session status pill badge
│   │   │   └── NavBar.jsx               → Admin navigation tabs
│   │   │
│   │   ├── session/
│   │   │   ├── ProgressBar.jsx          → 5-step progress indicator
│   │   │   └── steps/
│   │   │       ├── WelcomeStep.jsx      → Step 1: Policy + start
│   │   │       ├── LivenessStep.jsx     → Step 2: Face liveness (LiveKit)
│   │   │       ├── ConsentStep.jsx      → Step 3: Verbal consent recording
│   │   │       ├── PanStep.jsx          → Step 4: PAN card entry
│   │   │       ├── QAStep.jsx           → Step 5: 8-question Q&A
│   │   │       ├── ProcessingStep.jsx   → Polling + animated loader
│   │   │       ├── OfferStep.jsx        → Approved: offer + EMI table
│   │   │       ├── DeclinedStep.jsx     → Declined: reason + tips
│   │   │       ├── ManualReviewStep.jsx → HITL: under review message
│   │   │       └── ExpiredStep.jsx      → Expired: recontact message
│   │   │
│   │   └── DemoBadge.jsx                → (disabled — returns null)
│   │
│   ├── lib/
│   │   └── apiClient.js            → Unified API client (mock + real backend)
│   │
│   ├── mock/
│   │   └── api.js                  → Mock API responses (dev only)
│   │
│   └── routes/                     → TanStack Router file-based routes
│
├── server/
│   └── index.js                    → Legacy Node.js email relay server
│
├── .env                            → Environment variables
├── vite.config.js
├── tailwind.config.js
├── package.json
└── Dockerfile                      → Multi-stage: node:20 → nginx:1.27
```

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
# Set VITE_API_BASE_URL and VITE_WS_BASE_URL (see below)

# 3. Start development server
npm run dev
# → http://localhost:3000

# 4. Build for production
npm run build
# → dist/ folder (served by nginx in Docker)
```

---

## 🗺️ Application Routes

### Customer Routes

| Route | Component | Description |
|---|---|---|
| `/session/:token` | `SessionFlow` | Full KYC session flow (token is JWT) |

### Admin Routes

| Route | Component | Description |
|---|---|---|
| `/admin/login` | `AdminLogin` | Login with email + password |
| `/admin/customers` | `AdminCustomers` | Customer table + session management |
| `/admin/hitl` | `AdminHitl` | Manual review queue + approve/decline |

---

## 🎨 Customer Session Flow

```
SessionFlow.jsx manages step routing:

  "welcome"        → WelcomeStep        (policy display + start button)
       ↓
  "liveness"       → LivenessStep       (LiveKit WebRTC + face check)
       ↓
  "consent"        → ConsentStep        (verbal consent + audio recording)
       ↓
  "pan"            → PanStep            (PAN card input + validation)
       ↓
  "qa"             → QAStep             (8-question streaming Q&A)
       ↓
  "processing"     → ProcessingStep     (animated loader + polling GET /offer)
       ↓
  "approved"       → OfferStep          (loan offer + EMI table + PDF download)
  "declined"       → DeclinedStep       (reason + CIBIL tips)
  "hitl"           → ManualReviewStep   (under review message)
  "expired"        → ExpiredStep        (link expired message)
```

### QAStep — Streaming Q&A Protocol

```javascript
// WebSocket binary protocol
// 1. Server sends question (JSON text frame)
// 2. 30-second display phase (mic disabled)
// 3. Server sends answer phase (mic enabled)
// 4. Client streams binary PCM audio chunks
// 5. Server returns transcript_chunk events
// 6. Server returns extraction_result with confidence
// 7. Repeat for all 8 questions
// 8. Server sends pipeline_started → show ProcessingStep
```

---

## 🏦 Admin Dashboard Features

### All Customers Tab (`AdminCustomers.jsx`)

- **Full customer table**: Name, Email, Phone (masked), CIBIL Score, Status badge, Created date
- **Auto-refresh**: Every 30 seconds via `setInterval`
- **Manual refresh**: Button triggers immediate re-fetch
- **Add Customer**: Opens `AddCustomerModal`
- **Send Link / Resend Link**: Per row actions
- **Click row**: Opens `SessionStatusDrawer` for full session detail

### Session Status Drawer (`SessionStatusDrawer.jsx`)

Full-screen modal with complete session intelligence:

**Left column:**
- Identity: Full Name, DOB, CIBIL Score, PAN
- Address: Street, City, State, Pincode
- Employment & Income: Type, Employer, Tenure, Monthly Income, FOIR
- Loan Request: Purpose, Amount, Preferred Tenure
- LLM Quality: Extraction confidence + inconsistency score (progress bars)

**Right column:**
- Decision Explanation (auto-generated from signals)
- Layer 1 (Hard Rules): pass/fail with specific failing rule
- Layer 2 (ML Scoring): PD score bar, risk band, SHAP features
- Layer 3 (Offer): Approved amount, rate, EMI options table
- Biometrics: Live face frame (S3 presigned URL), liveness + spoof scores
- Network & Fraud: IP address, geo coordinates, risk score bars
- Behaviour & Consent: Response latency, hesitation count, consent transcript

**Bottom strip:**
- Session Timeline (events with timestamps)
- Session metadata (ID, product, dates)

**HITL action panel** (shows only when status = `hitl`):
- Notes textarea (required for decline)
- ✓ Approve Loan button (green)
- ✕ Decline button (red, disabled until notes filled)
- Success confirmation after action

### Manual Review Tab (`AdminHitl.jsx`)

HITL queue with inline actions per row:

```
┌──────────────┬──────────────────────────┬────────────────┬────────────────┬────────────────────────────────┐
│ Customer Name│ Session ID               │ Flagged At     │ Flag Reason    │ Action                         │
├──────────────┼──────────────────────────┼────────────────┼────────────────┼────────────────────────────────┤
│ Testing 7    │ bbebd849-32ba-4720...    │ 5/2/2026 3:48  │ HIGH_RISK_BAND │ [✓ Approve] [✕ Decline] [Review]│
└──────────────┴──────────────────────────┴────────────────┴────────────────┴────────────────────────────────┘
```

- **✓ Approve**: Fires immediately, triggers offer email to customer
- **✕ Decline**: Opens reason modal (required), triggers rejection email with reason
- **Review**: Opens full `SessionStatusDrawer` for detailed review before deciding

### Add Customer Modal (`AddCustomerModal.jsx`)

Duplicate detection with full existing customer card:

```
If phone already exists → 409 response → show amber card:
┌─────────────────────────────────────────────────────┐
│ ⚠ Customer already exists                          │
│                                                     │
│ Full Name   Ramesh Kumar                           │
│ Phone       ****3210                               │
│ Email       ramesh@example.com                     │
│ PAN         ABCDE1234F                             │
│ CIBIL       742 (shown in green)                   │
│ Created     01 Apr 2026                            │
│                                                     │
│ [Send KYC Link to this Customer]                   │
└─────────────────────────────────────────────────────┘
```

---

## 🔌 API Client (`lib/apiClient.js`)

Single unified client that delegates to mock or real backend based on `VITE_USE_MOCK`:

```javascript
import { createCustomer, sendLink, getSessionStatus, submitHitlDecision } from "@/lib/apiClient";

// All functions:
getSession(token, { latitude, longitude, deviceFingerprint })
pollOffer(sessionId)
submitPan(sessionId, panNumber)
getOfferDownload(offerRefId)
adminLogin(email, password)
listCustomers()
createCustomer(payload)           // 409 on duplicate phone
sendLink(customerId, email, ttlHours)
resendLink(customerId)
getSessionStatus(sessionId)
getHitlQueue()
submitHitlDecision(sessionId, decision, notes)
```

### Error Handling

```javascript
// apiFetch sets err.status and err.detail on non-2xx responses
// For 409 duplicate detection:
catch (err) {
  if (err.status === 409 && err.detail?.code === "customer_exists") {
    setExisting(err.detail);  // show existing customer card
  }
}
```

---

## 🎨 Design System

### Colors (Tailwind + CSS Variables)

```css
--color-amber:           #F97316   /* primary orange accent */
--color-ink:             #0A0F1E   /* deep navy background */
--color-surface:         #111827   /* card background */
--color-border:          #1F2937   /* card borders */
--color-status-green-fg: #22C55E   /* approved/pass */
--color-status-amber-fg: #F59E0B   /* warning/HITL */
--color-destructive:     #EF4444   /* declined/fail */
```

### Reusable Classes

```html
<!-- Cards -->
<div class="lw-card p-4">...</div>

<!-- Buttons -->
<button class="lw-btn lw-btn-primary">Submit</button>
<button class="lw-btn lw-btn-outline">Cancel</button>

<!-- Inputs -->
<input class="lw-input" />
<label class="lw-label">Field Name</label>

<!-- Badges -->
<span class="lw-badge bg-status-amber-bg text-status-amber-fg">HITL</span>
```

---

## 🔑 Environment Variables

```env
# Toggle mock vs real backend
VITE_USE_MOCK=false                              # "false" = use real backend

# Backend URLs
VITE_API_BASE_URL=https://your-backend.railway.app
VITE_WS_BASE_URL=wss://your-backend.railway.app

# Email server (legacy, for node server)
VITE_EMAIL_SERVER_URL=https://your-email.railway.app

# Admin default password hint (shown on login page in dev)
VITE_ADMIN_DEFAULT_PASSWORD=admin123
```

---

## 🐳 Docker (Production)

Multi-stage Dockerfile:

```dockerfile
# Stage 1: Build React app
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ARG VITE_WS_BASE_URL
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```bash
docker build \
  --build-arg VITE_API_BASE_URL=https://your-backend.railway.app \
  --build-arg VITE_WS_BASE_URL=wss://your-backend.railway.app \
  -t loan-wizard-frontend .

docker run -p 3000:80 loan-wizard-frontend
```

---

## 📦 Key Dependencies

```json
{
  "@tanstack/react-start": "1.167.14",
  "@tanstack/react-router": "1.168.0",
  "@tanstack/react-query": "5.83.0",
  "react": "^19.0.0",
  "vite": "^7.3.1",
  "tailwindcss": "^4.2.1",
  "@radix-ui/*": "17 packages",
  "react-hook-form": "7.71.2",
  "zod": "3.24.2",
  "lucide-react": "0.575.0",
  "recharts": "2.15.4"
}
```

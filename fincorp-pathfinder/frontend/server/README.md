<div align="center">

# 📧 Loan Wizard — Email Server
### Node.js · Express · Legacy Relay Service

[![Node](https://img.shields.io/badge/Node.js-20-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)](https://nodejs.org)
[![Express](https://img.shields.io/badge/Express-5.2-000000?style=for-the-badge&logo=express&logoColor=white)](https://expressjs.com)
[![Railway](https://img.shields.io/badge/Hosted_on-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

> **Note**: This server is a legacy component. All production transactional emails  
> (KYC link, offer, rejection) are now sent directly by the FastAPI backend via **AWS SES**.  
> This server remains as a fallback/dev relay.

</div>

---

## Purpose

This Express server was originally used to send emails from the frontend (before AWS SES was integrated into the backend). It accepts a `POST /api/send-email` request and relays via SMTP (originally Nodemailer → later Resend API → now superseded by AWS SES in the backend).

**Current status**: Runs on Railway port 3001. Still handles any legacy email calls from the frontend's `VITE_EMAIL_SERVER_URL`. Backend AWS SES handles all new email flows.

---

## 📁 Structure

```
server/
├── index.js        → Express app: POST /api/send-email + GET /api/health
├── .env            → SMTP / email credentials
└── README.md       → This file
```

---

## ⚡ Quick Start

```bash
# From frontend directory
cd fincorp-pathfinder/frontend

# Install dependencies (server uses same node_modules)
npm install

# Start email server
npm run start
# → Email server running on port 3001
```

---

## 🌐 Endpoints

### `POST /api/send-email`

Accepts an email payload and relays it.

**Request:**
```json
{
  "to": "customer@example.com",
  "subject": "Your KYC Link — Poonawalla Fincorp",
  "html": "<html>...</html>"
}
```

**Response 200:**
```json
{ "success": true, "messageId": "..." }
```

**Response 500:**
```json
{ "success": false, "error": "SMTP error message" }
```

### `GET /api/health`

```json
{ "status": "ok", "service": "email-relay" }
```

---

## 🔑 Environment Variables (`server/.env`)

```env
# Email relay configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-gmail@gmail.com
EMAIL_PASS=your-app-password         # Gmail App Password (not account password)

# Or use an SMTP service
# EMAIL_HOST=smtp.sendgrid.net
# EMAIL_USER=apikey
# EMAIL_PASS=your-sendgrid-api-key

FRONTEND_URL=https://your-frontend.railway.app
PORT=3001
```

---

## 🐳 Docker

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY server/ ./server/
EXPOSE 3001
CMD ["node", "server/index.js"]
```

---

## ⚠️ Migration Note

All transactional emails are now handled by the **FastAPI backend** using **AWS SES**:

| Email Type | Old Flow | Current Flow |
|---|---|---|
| KYC link sent | Frontend → this server → SMTP | Backend `POST /admin/send-link` → AWS SES |
| Loan approved | Frontend → this server | Backend `node_pdf_generation` → AWS SES |
| Loan declined | Frontend → this server | Backend `node_decline` → AWS SES |
| HITL decision | Not available | Backend `POST /admin/hitl/{id}/decision` → AWS SES |

See [backend/README.md](../../../backend/README.md) for AWS SES configuration.

---

## 📦 Dependencies

```json
{
  "express": "^5.2.1",
  "nodemailer": "^8.0.7",
  "cors": "^2.8.6",
  "dotenv": "^17.4.2"
}
```

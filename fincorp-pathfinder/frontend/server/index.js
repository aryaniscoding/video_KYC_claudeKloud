import dotenv from "dotenv";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, ".env") });

import express from "express";
import cors from "cors";
import { sendKycEmail } from "./emailService.js";

const app = express();
const PORT = process.env.PORT || 3001;

// Allow localhost in dev + the deployed frontend URL in production (set FRONTEND_URL env var)
const _localhostRe = /^http:\/\/localhost(:\d+)?$/;
app.use(cors({
  origin: (origin, cb) => {
    if (!origin) return cb(null, true); // non-browser (curl, Render health checks)
    const productionUrl = process.env.FRONTEND_URL;
    if (_localhostRe.test(origin) || (productionUrl && origin === productionUrl)) {
      return cb(null, true);
    }
    cb(new Error(`CORS: origin ${origin} not allowed`));
  },
}));
app.use(express.json());

// Request logger — so you can confirm the frontend is reaching the server
app.use((req, _res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
  next();
});

// ─── Health check ──────────────────────────────────────────────
app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date() });
});

// ─── Send KYC email ────────────────────────────────────────────
app.post("/api/send-email", async (req, res) => {
  const { toEmail, customerName, sessionUrl, expiryHours } = req.body;

  if (!toEmail || !customerName || !sessionUrl || !expiryHours) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  try {
    const result = await sendKycEmail({ toEmail, customerName, sessionUrl, expiryHours });
    return res.json({ success: true, messageId: result.messageId });
  } catch (err) {
    console.error("Email send error:", err);
    return res.status(500).json({ error: "Failed to send email", detail: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Email server running on port ${PORT}`);
});

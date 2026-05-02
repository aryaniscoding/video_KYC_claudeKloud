import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, ".env") });

const TEMPLATE_PATH = join(__dirname, "email-template.html");

export function previewEmail(customerName, sessionUrl, expiryHours) {
  const raw = readFileSync(TEMPLATE_PATH, "utf-8");
  return raw
    .replace(/\{\{CUSTOMER_NAME\}\}/g, customerName)
    .replace(/\{\{SESSION_URL\}\}/g, sessionUrl)
    .replace(/\{\{EXPIRY_HOURS\}\}/g, String(expiryHours));
}

/**
 * Send a KYC session email via Brevo HTTP API.
 * Requires BREVO_API_KEY, EMAIL_FROM_ADDRESS, EMAIL_FROM_NAME in env.
 */
export async function sendKycEmail({ toEmail, customerName, sessionUrl, expiryHours }) {
  const html = previewEmail(customerName, sessionUrl, expiryHours);

  const apiKey = process.env.BREVO_API_KEY;
  if (!apiKey) throw new Error("BREVO_API_KEY not set");

  const fromName = process.env.EMAIL_FROM_NAME || "Loan Wizard";
  const fromAddress = process.env.EMAIL_FROM_ADDRESS;
  if (!fromAddress) throw new Error("EMAIL_FROM_ADDRESS not set");

  const res = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: {
      "accept": "application/json",
      "api-key": apiKey,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      sender: { name: fromName, email: fromAddress },
      to: [{ email: toEmail, name: customerName }],
      subject: "Your Video KYC Link — Poonawalla Fincorp Personal Loan",
      htmlContent: html,
      textContent: `Hi ${customerName}, your KYC session is ready. Visit: ${sessionUrl} — expires in ${expiryHours} hours.`,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Brevo API ${res.status}: ${body}`);
  }

  const data = await res.json();
  return { success: true, messageId: data.messageId || "sent" };
}

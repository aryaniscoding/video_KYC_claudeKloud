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

export async function sendKycEmail({ toEmail, customerName, sessionUrl, expiryHours }) {
  const html = previewEmail(customerName, sessionUrl, expiryHours);

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) throw new Error("RESEND_API_KEY not set");

  const fromAddress = process.env.EMAIL_FROM_ADDRESS || "onboarding@resend.dev";
  const fromName = process.env.EMAIL_FROM_NAME || "Loan Wizard";

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: `${fromName} <${fromAddress}>`,
      to: [toEmail],
      subject: "Your Video KYC Link — Poonawalla Fincorp Personal Loan",
      html,
      text: `Hi ${customerName}, your KYC session is ready. Visit: ${sessionUrl} — expires in ${expiryHours} hours.`,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Resend API ${res.status}: ${body}`);
  }

  const data = await res.json();
  return { success: true, messageId: data.id };
}

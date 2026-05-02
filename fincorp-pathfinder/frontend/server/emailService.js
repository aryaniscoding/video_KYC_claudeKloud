import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import * as SibApiV3Sdk from "@getbrevo/brevo";
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
 * Send a KYC session email via Brevo HTTP API (avoids SMTP port blocks on Railway).
 * Set BREVO_API_KEY in Railway Variables — use the same key shown on Brevo SMTP & API page.
 * Set EMAIL_FROM_NAME and EMAIL_FROM_ADDRESS for the sender identity.
 */
export async function sendKycEmail({ toEmail, customerName, sessionUrl, expiryHours }) {
  const html = previewEmail(customerName, sessionUrl, expiryHours);

  const apiKey = process.env.BREVO_API_KEY || process.env.EMAIL_PASS;
  if (!apiKey) {
    throw new Error("BREVO_API_KEY not set");
  }

  const apiInstance = new SibApiV3Sdk.TransactionalEmailsApi();
  apiInstance.authentications["api-key"].apiKey = apiKey;

  const fromName = process.env.EMAIL_FROM_NAME || "Loan Wizard";
  const fromAddress = process.env.EMAIL_FROM_ADDRESS || process.env.EMAIL_USER || "noreply@example.com";

  const sendSmtpEmail = new SibApiV3Sdk.SendSmtpEmail();
  sendSmtpEmail.subject = "Your Video KYC Link — Poonawalla Fincorp Personal Loan";
  sendSmtpEmail.htmlContent = html;
  sendSmtpEmail.sender = { name: fromName, email: fromAddress };
  sendSmtpEmail.to = [{ email: toEmail, name: customerName }];
  sendSmtpEmail.textContent = `Hi ${customerName}, your KYC session is ready. Visit: ${sessionUrl} — expires in ${expiryHours} hours.`;

  const data = await apiInstance.sendTransacEmail(sendSmtpEmail);
  return { success: true, messageId: data.body?.messageId || data.messageId || "sent" };
}

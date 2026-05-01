import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import nodemailer from "nodemailer";
import dotenv from "dotenv";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, ".env") });

const TEMPLATE_PATH = join(__dirname, "email-template.html");

/**
 * Compile the HTML template by replacing placeholders.
 * Exported separately so the template can be previewed without sending.
 */
export function previewEmail(customerName, sessionUrl, expiryHours) {
  const raw = readFileSync(TEMPLATE_PATH, "utf-8");
  return raw
    .replace(/\{\{CUSTOMER_NAME\}\}/g, customerName)
    .replace(/\{\{SESSION_URL\}\}/g, sessionUrl)
    .replace(/\{\{EXPIRY_HOURS\}\}/g, String(expiryHours));
}

/**
 * Send a KYC session email to a customer.
 *
 * @param {Object} opts
 * @param {string} opts.toEmail      — recipient address
 * @param {string} opts.customerName — name shown in the greeting
 * @param {string} opts.sessionUrl   — one-time KYC link
 * @param {number} opts.expiryHours  — hours until the link expires
 * @returns {Promise<{ success: true, messageId: string }>}
 */
export async function sendKycEmail({ toEmail, customerName, sessionUrl, expiryHours }) {
  const html = previewEmail(customerName, sessionUrl, expiryHours);

  const transporter = nodemailer.createTransport({
    host: process.env.EMAIL_HOST || "smtp.gmail.com",
    port: Number(process.env.EMAIL_PORT) || 587,
    secure: false,
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS,
    },
  });

  const from = process.env.EMAIL_FROM || "Loan Wizard <noreply@loanwizard.in>";

  const info = await transporter.sendMail({
    from,
    to: toEmail,
    subject: "Your Video KYC Link — Poonawalla Fincorp Personal Loan",
    html,
    text: `Hi ${customerName}, your KYC session is ready. Visit: ${sessionUrl} — expires in ${expiryHours} hours.`,
  });

  return { success: true, messageId: info.messageId };
}

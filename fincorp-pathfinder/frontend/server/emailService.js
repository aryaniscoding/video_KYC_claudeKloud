import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import nodemailer from "nodemailer";
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
 * Send via AWS SES SMTP endpoint — works on Railway (port 587 is allowed for SES).
 * Requires: AWS_SES_SMTP_USER, AWS_SES_SMTP_PASS, AWS_SES_REGION, EMAIL_FROM in env.
 *
 * Get SMTP credentials from: AWS Console → SES → SMTP Settings → Create SMTP credentials
 * These are DIFFERENT from your regular AWS access keys.
 */
export async function sendKycEmail({ toEmail, customerName, sessionUrl, expiryHours }) {
  const html = previewEmail(customerName, sessionUrl, expiryHours);

  const region = process.env.AWS_SES_REGION || "ap-south-1";
  const transporter = nodemailer.createTransport({
    host: `email-smtp.${region}.amazonaws.com`,
    port: 587,
    secure: false,
    auth: {
      user: process.env.AWS_SES_SMTP_USER,
      pass: process.env.AWS_SES_SMTP_PASS,
    },
  });

  const from = process.env.EMAIL_FROM || `Loan Wizard <${process.env.AWS_SES_SMTP_USER}>`;

  const info = await transporter.sendMail({
    from,
    to: toEmail,
    subject: "Your Video KYC Link — Poonawalla Fincorp Personal Loan",
    html,
    text: `Hi ${customerName}, your KYC session is ready. Visit: ${sessionUrl} — expires in ${expiryHours} hours.`,
  });

  return { success: true, messageId: info.messageId };
}

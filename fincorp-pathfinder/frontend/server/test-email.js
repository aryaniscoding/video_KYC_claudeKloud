// One-off test — run with: node server/test-email.js
import "dotenv/config";
import { sendKycEmail } from "./emailService.js";

console.log("Sending test email to:", process.env.EMAIL_USER);

try {
  const result = await sendKycEmail({
    toEmail: process.env.EMAIL_USER,
    customerName: "Atharva (Test)",
    sessionUrl: "https://loanwizard.in/session/test-token-123",
    expiryHours: 24,
  });
  console.log("✅ Email sent successfully!");
  console.log("   Message ID:", result.messageId);
} catch (err) {
  console.error("❌ Email failed:", err.message);
  process.exit(1);
}

import React, { useState } from "react";
import { sendLink } from "@/lib/apiClient";

const EMAIL_SERVER = import.meta.env.VITE_EMAIL_SERVER_URL;

async function sendViaNodemailer(toEmail, customerName, sessionUrl, expiryHours) {
  if (!EMAIL_SERVER) return { sent: false, reason: "no email server configured" };
  const res = await fetch(`${EMAIL_SERVER}/api/send-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ toEmail, customerName, sessionUrl, expiryHours }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Email server ${res.status}`);
  }
  return { sent: true };
}

export default function SendLinkModal({ customer, onClose, onSent }) {
  const [email, setEmail] = useState(customer.email || `${customer.name.split(" ")[0].toLowerCase()}@example.com`);
  const [expiry, setExpiry] = useState(24);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null); // { sessionUrl, emailSent, emailError }

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const r = await sendLink(customer.id, email, expiry);
      const kycUrl = r.session_url || r.kyc_url;

      // Try Nodemailer email server; don't block on failure
      let emailSent = r.email_sent || false;
      let emailError = null;
      if (!emailSent && EMAIL_SERVER) {
        try {
          await sendViaNodemailer(email, customer.name, kycUrl, expiry);
          emailSent = true;
        } catch (err) {
          emailError = err.message;
        }
      }

      setResult({ sessionUrl: kycUrl, emailSent, emailError });
      onSent && onSent(customer.id, kycUrl);
    } catch (err) {
      setError(err.detail || err.message || "Failed to create KYC link.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-ink/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="lw-card w-full max-w-md p-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-6">
          <h2 className="text-xl font-semibold">Send KYC Link</h2>
          <button onClick={onClose} className="text-on-surface-variant hover:text-amber text-xl leading-none">×</button>
        </div>
        <p className="lw-label mb-6">{customer.name}</p>
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="lw-label block mb-2">Email</label>
            <input className="lw-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="lw-label block mb-2">Link Expiry</label>
            <div className="flex gap-2">
              {[24, 48, 72].map((h) => (
                <button type="button" key={h} onClick={() => setExpiry(h)}
                  className={`lw-btn flex-1 ${expiry === h ? "lw-btn-primary" : "lw-btn-outline"}`}>
                  {h}h
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="lw-label block mb-2">Note (optional)</label>
            <textarea className="lw-input" rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {result && (
            <div className="space-y-2">
              {result.emailSent ? (
                <p className="text-sm text-status-green-fg">✓ Email sent to {email}</p>
              ) : (
                <p className="text-sm text-amber-600">
                  Link created — email not sent{result.emailError ? ` (${result.emailError})` : ""}. Copy below:
                </p>
              )}
              <div className="flex gap-2 items-center">
                <input readOnly className="lw-input text-xs font-mono flex-1" value={result.sessionUrl} />
                <button type="button" className="lw-btn lw-btn-outline text-xs px-3"
                  onClick={() => navigator.clipboard?.writeText(result.sessionUrl)}>
                  Copy
                </button>
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="lw-btn lw-btn-outline flex-1">Cancel</button>
            <button type="submit" disabled={loading || !!result} className="lw-btn lw-btn-primary flex-1">
              {loading ? "Sending..." : result ? "Sent ✓" : "Send KYC Link"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

import React, { useState } from "react";
import { createCustomer, sendLink } from "@/lib/apiClient";

function ExistingCustomerBanner({ existing, onSendLink, onClose }) {
  const [sending, setSending] = useState(false);
  const [sent,    setSent]    = useState(false);
  const [sendErr, setSendErr] = useState(null);

  const handleSend = async () => {
    setSending(true);
    setSendErr(null);
    try {
      await sendLink(existing.id);
      setSent(true);
    } catch (e) {
      setSendErr(e.detail || e.message || "Failed to send link.");
    } finally {
      setSending(false);
    }
  };

  const createdDate = existing.created_at
    ? new Date(existing.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
    : null;

  return (
    <div className="rounded-xl border-2 border-status-amber-fg/50 bg-status-amber-bg overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-status-amber-fg/10 border-b border-status-amber-fg/20">
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-status-amber-fg shrink-0">
          <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
        </svg>
        <p className="text-sm font-bold text-status-amber-fg">Customer already exists</p>
      </div>

      {/* Details grid */}
      <div className="px-4 py-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <div>
          <p className="text-xs text-on-surface-variant mb-0.5">Full Name</p>
          <p className="font-semibold">{existing.name}</p>
        </div>
        <div>
          <p className="text-xs text-on-surface-variant mb-0.5">Phone</p>
          <p className="font-semibold font-mono">****{existing.phone_last4}</p>
        </div>
        <div>
          <p className="text-xs text-on-surface-variant mb-0.5">Email</p>
          <p className="font-semibold break-all">{existing.email}</p>
        </div>
        {existing.pan_number && (
          <div>
            <p className="text-xs text-on-surface-variant mb-0.5">PAN</p>
            <p className="font-semibold font-mono">{existing.pan_number}</p>
          </div>
        )}
        {existing.credit_score != null && (
          <div>
            <p className="text-xs text-on-surface-variant mb-0.5">CIBIL Score</p>
            <p className={`font-semibold ${existing.credit_score >= 750 ? "text-status-green-fg" : existing.credit_score >= 650 ? "text-status-amber-fg" : "text-destructive"}`}>
              {existing.credit_score}
            </p>
          </div>
        )}
        {existing.product_code && (
          <div>
            <p className="text-xs text-on-surface-variant mb-0.5">Product</p>
            <p className="font-semibold font-mono">{existing.product_code}</p>
          </div>
        )}
        {createdDate && (
          <div>
            <p className="text-xs text-on-surface-variant mb-0.5">Created</p>
            <p className="font-semibold">{createdDate}</p>
          </div>
        )}
      </div>

      {/* Action */}
      <div className="px-4 pb-4">
        {sent ? (
          <p className="text-sm text-status-green-fg font-semibold">✓ KYC link sent to {existing.email}</p>
        ) : (
          <>
            <button
              onClick={handleSend}
              disabled={sending}
              className="w-full rounded-lg bg-status-amber-fg text-white font-semibold py-2 text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {sending ? "Sending…" : "Send KYC Link to this Customer"}
            </button>
            {sendErr && <p className="text-xs text-destructive mt-1">{sendErr}</p>}
            <p className="text-xs text-on-surface-variant mt-2 text-center">
              Or find them in the All Customers table to manage their session.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function AddCustomerModal({ onClose, onAdded }) {
  const [form, setForm] = useState({
    name: "", email: "", phone: "", credit_score: "",
  });
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);
  const [existing, setExisting] = useState(null);

  const set = (k, v) => {
    setExisting(null); // clear duplicate banner when user edits the form
    setForm((f) => ({ ...f, [k]: v }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setExisting(null);
    setLoading(true);
    try {
      const payload = {
        ...form,
        credit_score: form.credit_score ? Number(form.credit_score) : null,
      };
      const customer = await createCustomer(payload);
      if (customer) onAdded && onAdded(customer);
      onClose();
    } catch (err) {
      if (err.status === 409 && err.detail?.code === "customer_exists") {
        setExisting(err.detail);
      } else {
        setError(err.detail || err.message || "Failed to create customer.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-ink/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="lw-card w-full max-w-lg p-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-6">
          <h2 className="text-xl font-semibold">Add Customer</h2>
          <button onClick={onClose} className="text-on-surface-variant hover:text-amber text-xl leading-none">×</button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="lw-label block mb-1">Full Name</label>
              <input className="lw-input" required value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Rahul Sharma" />
            </div>
            <div>
              <label className="lw-label block mb-1">Phone (10 digits)</label>
              <input className="lw-input" required pattern="\d{10}" maxLength={10} value={form.phone}
                onChange={(e) => set("phone", e.target.value.replace(/\D/g, ""))} placeholder="9876543210" />
            </div>
          </div>

          <div>
            <label className="lw-label block mb-1">Email</label>
            <input className="lw-input" type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="rahul@example.com" />
          </div>

          <div>
            <label className="lw-label block mb-1">CIBIL Score <span className="text-on-surface-variant font-normal">(300–900)</span></label>
            <input className="lw-input" type="number" min={300} max={900} required
              value={form.credit_score} onChange={(e) => set("credit_score", e.target.value)} placeholder="750" />
          </div>

          {existing && <ExistingCustomerBanner existing={existing} onClose={onClose} />}
          {error && <p className="text-sm text-destructive">{error}</p>}

          {!existing && (
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="lw-btn lw-btn-outline flex-1">Cancel</button>
              <button type="submit" disabled={loading} className="lw-btn lw-btn-primary flex-1">
                {loading ? "Creating..." : "Add Customer"}
              </button>
            </div>
          )}
          {existing && (
            <button type="button" onClick={onClose} className="lw-btn lw-btn-outline w-full">Close</button>
          )}
        </form>
      </div>
    </div>
  );
}

import React, { useState } from "react";
import { createCustomer } from "@/lib/apiClient";

const PRODUCTS = ["PL_STANDARD", "PL_PREMIUM", "PL_FLEXI", "HL_STANDARD", "BL_SME"];

export default function AddCustomerModal({ onClose, onAdded }) {
  const [form, setForm] = useState({
    name: "", email: "", phone: "",
    product_code: "PL_STANDARD",
    max_loan_amount: 500000,
    credit_score: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload = {
        ...form,
        max_loan_amount: Number(form.max_loan_amount),
        credit_score: form.credit_score ? Number(form.credit_score) : null,
      };
      const customer = await createCustomer(payload);
      onAdded && onAdded(customer);
      onClose();
    } catch (err) {
      setError(err.detail || err.message || "Failed to create customer.");
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="lw-label block mb-1">Product</label>
              <select className="lw-input" value={form.product_code} onChange={(e) => set("product_code", e.target.value)}>
                {PRODUCTS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="lw-label block mb-1">Max Loan Amount (₹)</label>
              <input className="lw-input" type="number" min={10000} max={5000000} step={10000}
                value={form.max_loan_amount} onChange={(e) => set("max_loan_amount", e.target.value)} />
            </div>
          </div>

          <div>
            <label className="lw-label block mb-1">Credit Score <span className="text-on-surface-variant font-normal">(optional, 300–900)</span></label>
            <input className="lw-input" type="number" min={300} max={900}
              value={form.credit_score} onChange={(e) => set("credit_score", e.target.value)} placeholder="750" />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="lw-btn lw-btn-outline flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="lw-btn lw-btn-primary flex-1">
              {loading ? "Creating..." : "Add Customer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

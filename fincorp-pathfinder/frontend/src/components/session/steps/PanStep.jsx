import React, { useState } from "react";
import { submitPan } from "@/lib/apiClient";

function validatePAN(pan) {
  return /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan);
}

export default function PanStep({ session, onComplete }) {
  const [pan, setPan] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const value = pan.trim().toUpperCase();
    if (!validatePAN(value)) {
      setError("Please enter a valid PAN (e.g. ABCDE1234F) — 5 letters, 4 digits, 1 letter.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await submitPan(session.session_id, value);
      onComplete();
    } catch (err) {
      setError(err.detail || err.message || "Failed to save PAN. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto px-4 md:px-6 py-8 md:py-12">
      <div className="text-center mb-8">
        <p className="lw-wordmark text-sm mb-3">LOAN WIZARD</p>
        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">PAN Card Verification</h1>
        <p className="mt-3 text-on-surface-variant text-sm md:text-base">
          Enter your PAN number exactly as it appears on your PAN card.
        </p>
      </div>

      <div className="lw-card p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="lw-label block mb-2">PAN Number</label>
            <input
              className="lw-input uppercase text-center text-lg tracking-widest font-mono"
              maxLength={10}
              value={pan}
              onChange={(e) => {
                setPan(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""));
                setError(null);
              }}
              placeholder="ABCDE1234F"
              autoFocus
              autoComplete="off"
            />
            <p className="mt-2 text-xs text-on-surface-variant">
              Format: 5 letters · 4 digits · 1 letter — all uppercase
            </p>
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || pan.length < 10}
            className="lw-btn lw-btn-primary w-full"
          >
            {loading ? "Verifying..." : "Continue"}
          </button>
        </form>
      </div>

      <p className="mt-6 text-center text-xs text-on-surface-variant">
        Your PAN is used only for identity verification and is stored securely.
      </p>
    </div>
  );
}

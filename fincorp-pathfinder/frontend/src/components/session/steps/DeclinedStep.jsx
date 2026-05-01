import React from "react";

export default function DeclinedStep({ result }) {
  const tips = result?.decline_tips || [
    "Reduce your existing EMI obligations before reapplying.",
    "Maintain a healthy credit score above 700.",
    "Reapply after 90 days for a fresh assessment.",
  ];
  return (
    <div className="max-w-2xl mx-auto px-6 py-12 text-center">
      <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center bg-status-amber-bg text-status-amber-fg">
        <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
        </svg>
      </div>
      <h1 className="text-2xl md:text-3xl font-semibold">We're unable to offer a loan at this time</h1>
      <p className="text-on-surface-variant mt-3">{result?.decline_reason || "Based on the information provided, you do not meet our current eligibility criteria."}</p>

      <div className="lw-card p-5 mt-8 text-left">
        <p className="lw-label mb-3">What can you do?</p>
        <ul className="space-y-2 text-sm">
          {tips.map((t, i) => <li key={i} className="flex gap-2"><span className="text-amber">▸</span>{t}</li>)}
        </ul>
      </div>

      <p className="mt-6 text-sm">Need help? Call <span className="font-semibold">1800-555-0000</span></p>
      <button className="lw-btn lw-btn-outline mt-6">Check other products →</button>
    </div>
  );
}

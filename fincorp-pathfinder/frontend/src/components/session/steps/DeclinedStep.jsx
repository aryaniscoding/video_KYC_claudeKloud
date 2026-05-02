import React from "react";

function RiskBadge({ band }) {
  const colors = {
    HIGH: "bg-red-100 text-red-700",
    VERY_HIGH: "bg-red-200 text-red-800",
    MEDIUM_HIGH: "bg-orange-100 text-orange-700",
    MEDIUM_LOW: "bg-yellow-100 text-yellow-700",
    LOW: "bg-green-100 text-green-700",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${colors[band] || "bg-surface-container-high text-on-surface"}`}>
      {band?.replace("_", " ")}
    </span>
  );
}

export default function DeclinedStep({ result }) {
  const tips = result?.decline_tips || [
    "Reduce your existing EMI obligations before reapplying.",
    "Maintain a healthy CIBIL score above 700.",
    "Reapply after 90 days for a fresh assessment.",
  ];
  const isMLDecline = result?.risk_band && !result?.failing_rule;
  const pdPct = result?.pd_score != null ? `${(result.pd_score * 100).toFixed(1)}%` : null;

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 text-center">
      <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center bg-status-amber-bg text-status-amber-fg">
        <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
        </svg>
      </div>
      <h1 className="text-2xl md:text-3xl font-semibold">We're unable to offer a loan at this time</h1>
      <p className="text-on-surface-variant mt-3">
        {result?.decline_reason || "Based on the information provided, you do not meet our current eligibility criteria."}
      </p>

      {/* Decision detail card */}
      <div className="lw-card p-5 mt-6 text-left space-y-4">
        <p className="lw-label">Decision details</p>

        {/* Hard rule failure */}
        {result?.failing_rule && (
          <div className="flex items-start gap-3">
            <span className="text-red-500 mt-0.5">✕</span>
            <div>
              <p className="text-sm font-medium">Rule not met</p>
              <p className="text-xs text-on-surface-variant mt-0.5 uppercase tracking-wide">{result.failing_rule.replace(/_/g, " ")}</p>
            </div>
          </div>
        )}

        {/* ML risk band + PD */}
        {result?.risk_band && (
          <div className="flex items-start gap-3">
            <span className="text-amber mt-0.5">◈</span>
            <div className="flex-1">
              <p className="text-sm font-medium">Risk assessment</p>
              <div className="flex items-center gap-2 mt-1">
                <RiskBadge band={result.risk_band} />
                {pdPct && (
                  <span className="text-xs text-on-surface-variant">Probability of default: <span className="font-medium text-on-surface">{pdPct}</span></span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Risk factors */}
        {result?.risk_factors?.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Contributing risk factors</p>
            <ul className="space-y-1">
              {result.risk_factors.map((f, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-red-400 shrink-0">▸</span>
                  <span className="text-on-surface-variant">{f}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Tips */}
      <div className="lw-card p-5 mt-4 text-left">
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

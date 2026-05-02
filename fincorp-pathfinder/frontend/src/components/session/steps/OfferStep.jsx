import React, { useState } from "react";
import { getDownloadUrl } from "@/lib/apiClient";

const fmtINR = (n) => "₹" + n.toLocaleString("en-IN");
const fmtDate = (iso) => new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export default function OfferStep({ offer }) {
  const [selected, setSelected] = useState(offer.recommended_tenure_months);
  const [accepted, setAccepted] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [celebrate, setCelebrate] = useState(true);

  React.useEffect(() => {
    const t = setTimeout(() => setCelebrate(false), 2100);
    return () => clearTimeout(t);
  }, []);

  const confettiPieces = React.useMemo(() => {
    const colors = ["var(--amber)", "oklch(0.70 0.15 150)", "oklch(0.65 0.14 240)", "var(--ink)"];
    return Array.from({ length: 36 }).map((_, i) => ({
      left: `${Math.random() * 100}%`,
      delay: `${Math.random() * 0.6}s`,
      bg: colors[i % colors.length],
      duration: `${1.4 + Math.random() * 0.8}s`,
    }));
  }, []);

  const selectedOption = offer.emi_options.find((o) => o.tenure_months === selected) || offer.emi_options[0];

  const download = async () => {
    setDownloading(true);
    await new Promise((r) => setTimeout(r, 1500));
    try {
      const r = await getDownloadUrl(offer.offer_ref_id);
      window.open(r.download_url, "_blank");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-6 py-8 md:py-10 relative">
      {celebrate && (
        <>
          <div className="lw-approve-pulse" />
          <div className="lw-confetti">
            {confettiPieces.map((p, i) => (
              <span key={i} style={{ left: p.left, background: p.bg, animationDelay: p.delay, animationDuration: p.duration }} />
            ))}
          </div>
        </>
      )}
      <div className="flex flex-col items-center text-center mb-8">
        <div className="lw-checkmark-circle mb-4">
          <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="3">
            <path d="M5 12l5 5L20 7" />
          </svg>
        </div>
        <h1 className="text-2xl md:text-3xl font-semibold">You're Approved!</h1>
        <p className="text-amber font-bold mt-6 tracking-tight leading-none"
           style={{ fontSize: "clamp(48px, 10vw, 88px)" }}>
          {fmtINR(offer.approved_amount)}
        </p>
        <div className="flex flex-wrap justify-center gap-2 mt-5">
          <span className="lw-badge bg-status-amber-bg text-status-amber-fg">{offer.interest_rate_pct}% p.a.</span>
          <span className="lw-badge bg-surface-container-high text-on-surface">Processing fee: {offer.processing_fee_pct}%</span>
        </div>
      </div>

      <p className="lw-label mb-4">Choose your repayment plan</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        {offer.emi_options.map((o) => {
          const isSel = selected === o.tenure_months;
          const isRec = o.tenure_months === offer.recommended_tenure_months;
          return (
            <button key={o.tenure_months} onClick={() => setSelected(o.tenure_months)}
              className={"lw-card p-5 text-left relative cursor-pointer transition-all min-h-[44px] " +
                (isSel ? "border-amber border-2" : "hover:border-amber")}>
              {isRec && <span className="absolute -top-3 left-4 lw-badge bg-amber text-ink">Recommended</span>}
              <p className="lw-label">{o.tenure_months} months</p>
              <p className="text-2xl font-semibold mt-3">{fmtINR(o.emi_amount)}<span className="text-xs text-on-surface-variant"> /mo</span></p>
              <p className="text-xs text-on-surface-variant mt-2">Total: {fmtINR(o.total_payable)}</p>
            </button>
          );
        })}
      </div>

      {/* Dynamic calc */}
      <div className="lw-card p-4 mb-6 bg-surface-container-high text-center">
        <p className="text-sm">
          You will pay <span className="text-amber font-bold">{fmtINR(selectedOption.total_payable)}</span> total over{" "}
          <span className="text-amber font-bold">{selectedOption.tenure_months} months</span>
        </p>
      </div>

      <div className="lw-card p-5 mb-4">
        <p className="lw-label mb-3">Why you were approved</p>
        <ul className="space-y-2 text-sm">
          {(offer.approval_reasons || []).map((r, i) => (
            <li key={i} className="flex gap-2"><span className="text-amber">▸</span>{r}</li>
          ))}
        </ul>
        {offer.pd_score != null && (
          <p className="text-xs text-on-surface-variant mt-3">
            Risk score: <span className="font-medium text-on-surface">{(offer.pd_score * 100).toFixed(1)}% PD</span>
            {offer.risk_band && <span className="ml-2 px-1.5 py-0.5 rounded bg-surface-container-high text-xs">{offer.risk_band.replace("_", " ")}</span>}
          </p>
        )}
      </div>

      {offer.risk_factors?.length > 0 && (
        <div className="lw-card p-5 mb-6">
          <p className="lw-label mb-3">Areas to improve for future applications</p>
          <ul className="space-y-2 text-sm">
            {offer.risk_factors.map((f, i) => (
              <li key={i} className="flex gap-2"><span className="text-on-surface-variant">◦</span>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-sm text-on-surface-variant mb-6">
        Offer valid until: <span className="text-on-surface font-medium">{fmtDate(offer.offer_valid_until)}</span>
      </p>

      <div className="flex flex-col gap-3">
        <button onClick={download} disabled={downloading}
          className="lw-btn lw-btn-primary py-4 min-h-[48px] flex items-center justify-center gap-2">
          {downloading ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-ink border-t-transparent rounded-full animate-spin" />
              Preparing...
            </>
          ) : "Download Offer Letter"}
        </button>
        <button onClick={() => setAccepted(true)} className="lw-btn lw-btn-dark py-4 min-h-[48px]">
          {accepted ? "✓ Offer Accepted — Our team will contact you" : "Accept This Offer →"}
        </button>
        <button className="lw-btn lw-btn-ghost text-xs underline min-h-[44px]">I'll decide later — offer saved for 30 days</button>
      </div>
    </div>
  );
}

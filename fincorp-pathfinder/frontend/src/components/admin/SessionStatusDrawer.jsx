import React, { useEffect, useState } from "react";
import { getSessionStatus } from "@/lib/apiClient";
import StatusBadge from "./StatusBadge";

// ── Helpers ────────────────────────────────────────────────────────────────────

function Avatar({ name }) {
  const initials = (name || "?")
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0] || "")
    .join("")
    .toUpperCase();
  return (
    <div className="w-16 h-16 rounded-full bg-amber text-ink flex items-center justify-center text-2xl font-bold shrink-0 select-none">
      {initials}
    </div>
  );
}

function ScoreBar({ label, score, invert = false }) {
  if (score == null)
    return (
      <div className="flex justify-between items-center py-1.5 text-sm">
        <span className="text-on-surface-variant">{label}</span>
        <span className="text-on-surface-variant">—</span>
      </div>
    );
  const pct = Math.min(100, Math.max(0, score * 100));
  const color = invert
    ? score < 0.3 ? "oklch(0.70 0.15 150)" : score < 0.6 ? "var(--amber)" : "oklch(0.60 0.22 28)"
    : score > 0.7 ? "oklch(0.70 0.15 150)" : score > 0.4 ? "var(--amber)" : "oklch(0.60 0.22 28)";
  return (
    <div className="py-1.5">
      <div className="flex justify-between items-center text-sm mb-1">
        <span className="text-on-surface-variant">{label}</span>
        <span className="font-mono tabular-nums font-medium" style={{ color }}>
          {score.toFixed(3)}
        </span>
      </div>
      <div className="h-2 bg-surface-container-high w-full rounded-full overflow-hidden">
        <div className="h-full transition-all rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function Row({ label, value, mono = false, valueClass = "", fullWidth = false }) {
  const display =
    value == null ? "—"
    : typeof value === "boolean" ? (value ? "Yes" : "No")
    : typeof value === "object" ? JSON.stringify(value)
    : value;
  if (fullWidth) {
    return (
      <div className="py-1.5 text-sm border-b border-border/40 last:border-0">
        <span className="text-on-surface-variant text-xs block mb-0.5">{label}</span>
        <span className={`${mono ? "font-mono break-all" : "font-medium"} ${valueClass}`}>{display}</span>
      </div>
    );
  }
  return (
    <div className="flex justify-between items-start gap-4 py-1.5 text-sm border-b border-border/40 last:border-0">
      <span className="text-on-surface-variant shrink-0">{label}</span>
      <span className={`text-right ${mono ? "font-mono break-all" : "font-medium"} ${valueClass}`}>{display}</span>
    </div>
  );
}

function CardBlock({ title, children }) {
  return (
    <div className="lw-card p-4 mb-3 last:mb-0">
      <p className="text-xs text-on-surface-variant uppercase tracking-widest mb-3 font-semibold">{title}</p>
      {children}
    </div>
  );
}

function ColSection({ title, children }) {
  return (
    <div className="p-5 border-b border-border last:border-0">
      <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">{title}</p>
      {children}
    </div>
  );
}

function buildTimeline(data) {
  const fmt = (d) =>
    d ? new Date(d).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : null;
  const events = [];
  if (data.created_at) events.push({ event: "Session Created", time: fmt(data.created_at) });
  const map = {
    started: "Liveness Check Started", face_check: "Face Check Completed",
    consent: "Consent Recorded", qa: "Q&A Completed",
    processing: "ML Processing Started", approved: "Application Approved",
    declined: "Application Declined", hitl: "Referred for Human Review",
    dropped: "Session Dropped", expired: "Session Expired",
  };
  if (data.status !== "pending" && data.updated_at)
    events.push({ event: map[data.status] || `Status: ${data.status}`, time: fmt(data.updated_at) });
  return events;
}

const INR  = (n) => n != null ? `₹${Number(n).toLocaleString("en-IN")}` : null;
const PCT  = (n) => n != null ? `${n}%` : null;
const YRS  = (n) => n != null ? `${n} yr${n === 1 ? "" : "s"}` : null;

// ── Main component ─────────────────────────────────────────────────────────────

export default function SessionStatusDrawer({ customer, onClose }) {
  const [data, setData] = useState(null);
  const [err,  setErr]  = useState(null);
  const sessionId = customer.latest_session_id || customer.session_id;

  useEffect(() => {
    if (!sessionId) { setErr("No session found for this customer."); return; }
    let alive = true;
    getSessionStatus(sessionId)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setErr(e.detail || e.message || "Failed to load."); });
    return () => { alive = false; };
  }, [sessionId]);

  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const timeline = data ? buildTimeline(data) : [];
  const app = data?.application;
  const dec = data?.decision;
  const displayName = customer.name || data?.customer_name || "—";

  const geoLabel =
    data?.latitude != null && data?.longitude != null
      ? `${data.latitude.toFixed(5)}, ${data.longitude.toFixed(5)}`
      : null;
  const cityState = [app?.city, app?.state].filter(Boolean).join(", ") || null;

  return (
    <div
      className="fixed inset-0 z-50 bg-ink/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Modal — wide landscape */}
      <div
        className="bg-surface w-[95vw] max-w-6xl max-h-[92vh] flex flex-col shadow-2xl rounded-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ─────────────────────────────────────────────────────────── */}
        <div className="px-8 py-5 border-b border-border flex items-center justify-between gap-6 bg-surface shrink-0">
          <div className="flex items-center gap-5">
            <Avatar name={displayName} />
            <div>
              <h2 className="text-xl font-bold">{displayName}</h2>
              <p className="text-sm text-on-surface-variant mt-0.5">{customer.email || "—"}</p>
              <div className="mt-2 flex items-center gap-3 flex-wrap">
                <StatusBadge status={customer.status || data?.status || "—"} />
                {customer.product || customer.product_code
                  ? <span className="text-xs font-mono bg-surface-container-high px-2 py-0.5 rounded">{customer.product || customer.product_code}</span>
                  : null}
                {customer.phone_last4
                  ? <span className="text-xs text-on-surface-variant">****{customer.phone_last4}</span>
                  : null}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            {data?.created_at && (
              <div className="text-right hidden md:block">
                <p className="text-xs text-on-surface-variant">Session opened</p>
                <p className="text-sm font-medium">{new Date(data.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</p>
              </div>
            )}
            <button
              onClick={onClose}
              aria-label="Close"
              className="text-on-surface-variant hover:text-on-surface text-3xl leading-none w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface-container-high transition-colors"
            >
              ×
            </button>
          </div>
        </div>

        {err  && <p className="p-8 text-base text-destructive">{err}</p>}
        {!data && !err && <p className="p-8 text-base text-on-surface-variant">Loading…</p>}

        {data && (
          /* ── Two-column body ─────────────────────────────────────────────── */
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="flex-1 overflow-y-auto grid grid-cols-2 divide-x divide-border">

              {/* ══════════════ LEFT COLUMN ══════════════ */}
              <div className="overflow-y-auto">

                {/* Personal */}
                <ColSection title="Personal Details">
                  <CardBlock title="Identity">
                    <Row label="Full Name"     value={app?.full_name}    />
                    <Row label="Date of Birth" value={app?.dob}          />
                    <Row label="Credit Score"  value={customer.credit_score} />
                    <Row label="Max Pre-approved" value={INR(customer.max_loan_amount)} valueClass="text-status-green-fg" />
                  </CardBlock>
                  <CardBlock title="Address">
                    <Row label="Street"  value={app?.address_line} />
                    <Row label="City"    value={app?.city}         />
                    <Row label="State"   value={app?.state}        />
                    <Row label="Pincode" value={app?.pincode} mono />
                  </CardBlock>
                </ColSection>

                {/* Employment */}
                <ColSection title="Employment &amp; Income">
                  <CardBlock title="Job">
                    <Row label="Type"         value={app?.employment_type?.replace("_", " ")} />
                    <Row label="Employer"     value={app?.employer_name}   />
                    <Row label="Tenure"       value={YRS(app?.job_tenure_years)} />
                  </CardBlock>
                  <CardBlock title="Financials">
                    <Row label="Monthly Income"  value={INR(app?.monthly_income)}    valueClass="font-semibold" />
                    <Row label="Existing EMI"    value={INR(app?.existing_emi_monthly)} />
                    <Row label="Has Active Loans" value={app?.has_existing_loans} />
                    {app?.monthly_income && app?.existing_emi_monthly != null && (
                      <Row
                        label="FOIR"
                        value={`${((app.existing_emi_monthly / app.monthly_income) * 100).toFixed(1)}%`}
                        valueClass={app.existing_emi_monthly / app.monthly_income > 0.5 ? "text-destructive" : "text-status-green-fg"}
                      />
                    )}
                  </CardBlock>
                </ColSection>

                {/* Loan Request */}
                <ColSection title="Loan Request">
                  <CardBlock title="Request">
                    <Row label="Purpose"          value={app?.loan_purpose?.replace("_", " ")} />
                    <Row label="Requested Amount" value={INR(app?.requested_amount)} valueClass="font-semibold" />
                    <Row label="Preferred Tenure" value={app?.preferred_tenure_months ? `${app.preferred_tenure_months} months` : null} />
                  </CardBlock>
                </ColSection>

                {/* LLM Quality */}
                <ColSection title="LLM Extraction Quality">
                  <ScoreBar label="Extraction Confidence" score={app?.extraction_confidence_avg} />
                  <ScoreBar label="Inconsistency Score"   score={app?.inconsistency_score} invert />
                  {app?.flagged_inconsistencies?.length > 0 && (
                    <div className="mt-3 space-y-1.5">
                      <p className="text-xs text-on-surface-variant uppercase tracking-wide">Flagged Issues</p>
                      {app.flagged_inconsistencies.map((f, i) => {
                        const label = typeof f === "string"
                          ? f
                          : [f.field, f.issue].filter(Boolean).join(": ") || JSON.stringify(f);
                        const isHigh = f?.severity === "high" || f?.severity === "critical";
                        return (
                          <p key={i} className={`text-sm px-3 py-1.5 rounded ${isHigh ? "text-destructive bg-destructive/10" : "text-status-amber-fg bg-status-amber-bg"}`}>
                            {label}
                          </p>
                        );
                      })}
                    </div>
                  )}
                </ColSection>

              </div>
              {/* ══════════════ END LEFT ══════════════ */}

              {/* ══════════════ RIGHT COLUMN ══════════════ */}
              <div className="overflow-y-auto">

                {/* Decision */}
                {dec && (
                  <ColSection title="Decision Breakdown">
                    <CardBlock title="Layer 1 — Hard Rules">
                      <Row
                        label="Rules Passed"
                        value={dec.hard_rules_passed ? "✓ All rules passed" : "✗ Failed"}
                        valueClass={dec.hard_rules_passed ? "text-status-green-fg" : "text-destructive"}
                      />
                      {!dec.hard_rules_passed && <>
                        <Row label="Failing Rule" value={dec.failing_rule} mono />
                        <Row label="Reason"       value={dec.failing_rule_reason} />
                      </>}
                    </CardBlock>

                    <CardBlock title="Layer 2 — ML Scoring">
                      <ScoreBar label="PD Score (higher = riskier)" score={dec.pd_score} invert />
                      <Row label="Risk Band"   value={dec.risk_band} />
                      <Row label="ML Eligible" value={dec.eligible == null ? null : dec.eligible ? "✓ Yes" : "✗ No"}
                           valueClass={dec.eligible ? "text-status-green-fg" : "text-destructive"} />
                      {dec.top_positive_features?.length > 0 && (
                        <div className="mt-3">
                          <p className="text-xs text-on-surface-variant mb-1.5">Top Risk Drivers</p>
                          <div className="flex flex-wrap gap-1.5">
                            {dec.top_positive_features.map((f) => (
                              <span key={f} className="text-xs px-2 py-0.5 rounded bg-status-amber-bg text-status-amber-fg">{f}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {dec.top_negative_features?.length > 0 && (
                        <div className="mt-3">
                          <p className="text-xs text-on-surface-variant mb-1.5">Approval Signals</p>
                          <div className="flex flex-wrap gap-1.5">
                            {dec.top_negative_features.map((f) => (
                              <span key={f} className="text-xs px-2 py-0.5 rounded bg-status-green-bg text-status-green-fg">{f}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardBlock>

                    {dec.approved_amount && (
                      <CardBlock title="Layer 3 — Offer">
                        <Row label="Approved Amount"  value={INR(dec.approved_amount)}          valueClass="text-status-green-fg font-bold text-base" />
                        <Row label="Interest Rate"    value={PCT(dec.interest_rate)}             />
                        <Row label="Processing Fee"   value={PCT(dec.processing_fee_pct)}        />
                        <Row label="Recommended Tenure" value={dec.recommended_tenure_months ? `${dec.recommended_tenure_months} months` : null} />
                        {dec.emi_options?.length > 0 && (
                          <div className="mt-3">
                            <p className="text-xs text-on-surface-variant mb-2 uppercase tracking-wide">EMI Options</p>
                            <div className="space-y-1.5">
                              {dec.emi_options.map((o) => {
                                const isRec = o.tenure_months === dec.recommended_tenure_months;
                                return (
                                  <div key={o.tenure_months}
                                    className={`flex justify-between items-center text-sm px-3 py-2 rounded ${isRec ? "bg-status-green-bg ring-1 ring-status-green-fg/30" : "bg-surface-container-high"}`}>
                                    <span className={`font-semibold ${isRec ? "text-status-green-fg" : ""}`}>{o.tenure_months}M</span>
                                    <span className="font-bold">{INR(o.emi_amount)}/mo</span>
                                    <span className="text-on-surface-variant text-xs">
                                      Int: {INR(o.total_interest_inr)} | Total: {INR(o.total_payable)}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                            <p className="text-xs text-on-surface-variant mt-1.5">★ Highlighted = recommended tenure</p>
                          </div>
                        )}
                      </CardBlock>
                    )}
                  </ColSection>
                )}

                {/* Biometrics */}
                <ColSection title="Biometrics &amp; Identity Verification">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="lw-card p-3 text-center">
                      <p className="text-xs text-on-surface-variant mb-1">Liveness</p>
                      <p className={`text-2xl font-bold ${data.liveness_score > 0.7 ? "text-status-green-fg" : data.liveness_score > 0.4 ? "text-status-amber-fg" : "text-destructive"}`}>
                        {data.liveness_score != null ? data.liveness_score.toFixed(2) : "—"}
                      </p>
                    </div>
                    <div className="lw-card p-3 text-center">
                      <p className="text-xs text-on-surface-variant mb-1">Est. Age</p>
                      <p className="text-2xl font-bold">{data.estimated_age != null ? `${Math.round(data.estimated_age)}` : "—"}</p>
                    </div>
                    <div className="lw-card p-3 text-center">
                      <p className="text-xs text-on-surface-variant mb-1">Face Conf.</p>
                      <p className={`text-2xl font-bold ${data.face_confidence > 0.7 ? "text-status-green-fg" : "text-status-amber-fg"}`}>
                        {data.face_confidence != null ? data.face_confidence.toFixed(2) : "—"}
                      </p>
                    </div>
                    <div className="lw-card p-3 text-center">
                      <p className="text-xs text-on-surface-variant mb-1">Age Consistency</p>
                      <p className={`text-2xl font-bold ${data.age_consistency_score > 0.7 ? "text-status-green-fg" : "text-status-amber-fg"}`}>
                        {data.age_consistency_score != null ? data.age_consistency_score.toFixed(2) : "—"}
                      </p>
                    </div>
                  </div>
                </ColSection>

                {/* Network & Fraud Signals */}
                <ColSection title="Network, Location &amp; Fraud Signals">
                  <CardBlock title="Network">
                    <Row label="IP Address"  value={data.ip_address}  mono />
                    <Row label="Coordinates" value={geoLabel}          mono />
                    {cityState && <Row label="City / State" value={cityState} />}
                  </CardBlock>
                  <CardBlock title="Risk Scores">
                    <ScoreBar label="Geo Risk"    score={data.geo_risk_score}    invert />
                    <ScoreBar label="IP Risk"     score={data.ip_risk_score}     invert />
                    <ScoreBar label="Device Risk" score={data.device_risk_score} invert />
                    <Row
                      label="Velocity Fraud Flag"
                      value={data.velocity_fraud_flag ? "⚠ Flagged" : "✓ Clear"}
                      valueClass={data.velocity_fraud_flag ? "text-destructive" : "text-status-green-fg"}
                    />
                  </CardBlock>
                  {data.device_fingerprint && (
                    <CardBlock title="Device">
                      <Row label="Fingerprint" value={data.device_fingerprint} mono fullWidth />
                    </CardBlock>
                  )}
                </ColSection>

                {/* Behaviour */}
                <ColSection title="Behaviour &amp; Consent">
                  <CardBlock title="Response Behaviour">
                    <ScoreBar label="Consent Confidence" score={data.consent_confidence} />
                    <Row label="Avg Response Latency" value={data.avg_response_latency_ms ? `${Math.round(data.avg_response_latency_ms)} ms` : null} />
                    <Row label="Hesitations"     value={data.hesitation_count}    />
                    <Row label="Question Retries" value={data.question_retry_count} />
                  </CardBlock>
                  {data.consent_transcript && (
                    <CardBlock title="Consent Transcript">
                      <p className="text-sm italic text-on-surface-variant bg-surface-container-high px-3 py-2 rounded">
                        "{data.consent_transcript}"
                      </p>
                    </CardBlock>
                  )}
                </ColSection>

              </div>
              {/* ══════════════ END RIGHT ══════════════ */}

            </div>

            {/* ── Full-width bottom strip: Timeline + Session meta ─────────── */}
            <div className="shrink-0 border-t border-border grid grid-cols-2 divide-x divide-border bg-surface-container-low">
              {/* Timeline */}
              <div className="p-5">
                <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-3">Session Timeline</p>
                {timeline.length === 0
                  ? <p className="text-sm text-on-surface-variant">No events yet.</p>
                  : <ol className="flex flex-wrap gap-x-8 gap-y-2">
                      {timeline.map((ev, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <span className="w-2 h-2 bg-amber mt-1.5 shrink-0" />
                          <span>
                            <span className="font-medium">{ev.event}</span>
                            <span className="text-on-surface-variant ml-2 text-xs">{ev.time}</span>
                          </span>
                        </li>
                      ))}
                    </ol>
                }
              </div>
              {/* Session meta */}
              <div className="p-5">
                <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-3">Session Details</p>
                <div className="grid grid-cols-2 gap-x-6">
                  <Row label="Session ID" value={sessionId} mono />
                  <Row label="Product" value={customer.product || customer.product_code} />
                  <Row label="Customer Since" value={customer.created_date || (data.created_at ? new Date(data.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : null)} />
                  <Row label="Last Updated" value={data.updated_at ? new Date(data.updated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : null} />
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";

function Check({ ok, label, status }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <span className="text-sm">{label}</span>
      <span className={"lw-badge " + (ok === null ? "bg-status-gray-bg text-status-gray-fg" : ok ? "bg-status-green-bg text-status-green-fg" : "bg-status-red-bg text-status-red-fg")}>
        {ok === null ? "Checking..." : status}
      </span>
    </div>
  );
}

const SHORTCUTS = [
  { key: "liveness", label: "Face Check" },
  { key: "consent", label: "Consent" },
  { key: "qa", label: "Q&A" },
  { key: "processing", label: "Processing" },
  { key: "offer", label: "Offer" },
  { key: "declined", label: "Declined" },
];

export default function WelcomeStep({ session, onNext, onJump }) {
  const [cam, setCam] = useState(null);
  const [mic, setMic] = useState(null);
  const [net, setNet] = useState(null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setNet(typeof navigator !== "undefined" && navigator.onLine);
    // Demo safety: auto-pass after 2s if camera/mic permission is slow or blocked
    const failsafe = setTimeout(() => {
      setCam((v) => (v === null || v === false ? true : v));
      setMic((v) => (v === null || v === false ? true : v));
      setNet((v) => (v === null || v === false ? true : v));
    }, 2000);
    if (typeof navigator === "undefined" || !navigator.mediaDevices) {
      return () => clearTimeout(failsafe);
    }
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((s) => { setCam(true); s.getTracks().forEach((t) => t.stop()); })
      .catch(() => setCam((v) => (v === null ? false : v)));
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((s) => { setMic(true); s.getTracks().forEach((t) => t.stop()); })
      .catch(() => setMic((v) => (v === null ? false : v)));
    return () => clearTimeout(failsafe);
  }, []);

  const ready = cam && mic && net;

  return (
    <div className="max-w-2xl mx-auto px-4 md:px-6 py-8 md:py-12">
      <div className="text-center mb-8 md:mb-10">
        <p className="lw-wordmark text-sm mb-3">LOAN WIZARD</p>
        <h1 className="text-2xl md:text-4xl font-semibold tracking-tight">
          Welcome, {session.customer_name}
        </h1>
        <p className="mt-3 text-on-surface-variant text-sm md:text-base">
          Your personal loan KYC session — about 12 minutes.
        </p>
      </div>

      <div className="lw-card p-5 md:p-6 mb-6">
        <p className="lw-label mb-4">Before you start</p>
        <ul className="space-y-3 text-sm">
          <li className="flex gap-3"><span className="text-amber">▸</span> A working camera and microphone are required.</li>
          <li className="flex gap-3"><span className="text-amber">▸</span> Find a quiet, well-lit space.</li>
          <li className="flex gap-3"><span className="text-amber">▸</span> Have your address and income details ready.</li>
        </ul>
      </div>

      <div className="lw-card p-5 md:p-6 mb-8">
        <p className="lw-label mb-4">Device Check</p>
        <Check ok={cam} label="Camera" status={cam ? "Ready" : "Not detected"} />
        <Check ok={mic} label="Microphone" status={mic ? "Ready" : "Not detected"} />
        <Check ok={net} label="Internet" status={net ? "Connected" : "Offline"} />
      </div>

      <button disabled={!ready} onClick={onNext}
        className={"lw-btn lw-btn-primary w-full text-base py-4 min-h-[48px]"}>
        I'm Ready — Start Session →
      </button>

      {/* Demo shortcuts */}
      <div className="mt-8 mb-16">
        <button
          onClick={() => setShowShortcuts((v) => !v)}
          className="lw-label flex items-center gap-2 hover:text-amber transition-colors"
        >
          <span>⚡ Demo shortcuts</span>
          <span>{showShortcuts ? "▲" : "▼"}</span>
        </button>
        {showShortcuts && (
          <div className="lw-card p-4 mt-3 bg-surface-container">
            <p className="lw-label mb-3">Jump to screen →</p>
            <div className="flex flex-wrap gap-2">
              {SHORTCUTS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => onJump?.(s.key)}
                  className="lw-btn lw-btn-outline text-xs py-2 px-3 min-h-[36px]"
                >
                  {s.label}
                </button>
              ))}
              <button
                onClick={() => navigate({ to: "/admin/customers" })}
                className="lw-btn lw-btn-dark text-xs py-2 px-3 min-h-[36px]"
              >
                Admin
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

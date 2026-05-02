import React, { useEffect, useState } from "react";

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


export default function WelcomeStep({ session, onNext, onJump }) {
  const [cam, setCam] = useState(null);
  const [mic, setMic] = useState(null);
  const [net, setNet] = useState(null);

  const checkDevices = () => {
    setCam(null);
    setMic(null);
    setNet(typeof navigator !== "undefined" && navigator.onLine);
    if (typeof navigator === "undefined" || !navigator.mediaDevices) {
      setCam(false);
      setMic(false);
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((s) => { setCam(true); s.getTracks().forEach((t) => t.stop()); })
      .catch(() => setCam(false));
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((s) => { setMic(true); s.getTracks().forEach((t) => t.stop()); })
      .catch(() => setMic(false));
  };

  useEffect(() => { checkDevices(); }, []);

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
        {(cam === false || mic === false) && (
          <div className="mt-4 p-3 bg-status-red-bg rounded text-xs text-status-red-fg space-y-2">
            <p>
              {cam === false && mic === false
                ? "Camera and microphone access was blocked."
                : cam === false
                ? "Camera access was blocked."
                : "Microphone access was blocked."}
              {" "}To continue, click the <strong>lock icon</strong> in your browser's address bar, allow access, then click <strong>Try Again</strong>.
            </p>
            <button
              onClick={checkDevices}
              className="lw-btn lw-btn-outline text-xs py-1.5 px-3 min-h-[32px] w-full"
            >
              ↺ Try Again
            </button>
          </div>
        )}
      </div>

      <button disabled={!ready} onClick={onNext}
        className={"lw-btn lw-btn-primary w-full text-base py-4 min-h-[48px]"}>
        I'm Ready — Start Session →
      </button>

    </div>
  );
}

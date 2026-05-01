import React, { useEffect, useState } from "react";
import { pollOffer } from "@/lib/apiClient";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

const MESSAGES = [
  "Reading your answers...",
  "Verifying your identity...",
  "Filling your application form...",
  "Checking eligibility rules...",
  "Calculating your offer...",
  "Almost there...",
];

export default function ProcessingStep({ session, onResult }) {
  const [progress, setProgress] = useState(0);
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    const DURATION = 6;
    const start = Date.now();

    // Progress bar animation
    const t1 = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      setProgress(Math.min(100, (elapsed / DURATION) * 100));
      if (elapsed >= DURATION) clearInterval(t1);
    }, 100);

    // Rotating messages
    const t2 = setInterval(() => setMsgIdx((i) => (i + 1) % MESSAGES.length), 1500);

    let pollTimer = null;

    if (USE_MOCK) {
      // Mock mode: fetch offer after animation completes
      const t3 = setTimeout(async () => {
        const res = await pollOffer(session.session_id);
        if (res.eligible) onResult("offer", res);
        else onResult("declined", res);
      }, DURATION * 1000 + 200);

      return () => { clearInterval(t1); clearInterval(t2); clearTimeout(t3); };
    }

    // Real mode: poll GET /session/{session_id}/offer every 3 seconds
    // Wait for animation to finish before starting to poll
    const MAX_POLL_MS = 3 * 60 * 1000; // 3 minutes
    const pollStart = Date.now();
    const startPolling = setTimeout(() => {
      pollTimer = setInterval(async () => {
        if (Date.now() - pollStart > MAX_POLL_MS) {
          clearInterval(pollTimer);
          onResult("declined", { eligible: false, decline_reason: "Processing timed out. Our team will contact you shortly." });
          return;
        }
        try {
          const res = await pollOffer(session.session_id);
          if (res.processing) return; // 202 — still processing, keep polling
          clearInterval(pollTimer);
          if (res.eligible) onResult("offer", res);
          else onResult("declined", res);
        } catch (err) {
          // 400 or other error — stop polling, show declined
          clearInterval(pollTimer);
          onResult("declined", { eligible: false, decline_reason: err.detail || "An error occurred." });
        }
      }, 3000);
    }, DURATION * 1000);

    return () => {
      clearInterval(t1);
      clearInterval(t2);
      clearTimeout(startPolling);
      if (pollTimer) clearInterval(pollTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-xl mx-auto px-6 py-20 text-center">
      <p className="lw-wordmark text-lg mb-8">LOAN WIZARD</p>
      <div className="h-2 bg-surface-container-high w-full mb-6">
        <div className="h-full lw-progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <p className="text-lg font-medium min-h-[2rem]">{MESSAGES[msgIdx]}</p>
      <p className="text-xs text-on-surface-variant mt-3">A few more seconds…</p>
    </div>
  );
}

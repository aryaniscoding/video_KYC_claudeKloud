import React, { useEffect, useRef, useState } from "react";
import { MockWebSocket } from "@/mock/websocket";
import { startFrameCapture } from "@/lib/frameCapture";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

export default function LivenessStep({ session, cameraStream, setCameraStream, onComplete }) {
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const stopCaptureRef = useRef(null);
  const [state, setState] = useState("scanning");
  const [frame, setFrame] = useState(0);
  const [challenge, setChallenge] = useState(null);
  const [challengeProgress, setChallengeProgress] = useState(null);
  const [error, setError] = useState(null);

  // Acquire/reuse stream
  useEffect(() => {
    let cancelled = false;
    const attach = (s) => {
      if (videoRef.current) {
        videoRef.current.srcObject = s;
        videoRef.current.play().catch(() => {});
      }
    };
    if (cameraStream) {
      attach(cameraStream);
    } else if (typeof navigator !== "undefined" && navigator.mediaDevices) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        setCameraStream(s);
        attach(s);
      }).catch(() => {});
    }
    return () => { cancelled = true; };
  }, [cameraStream, setCameraStream]);

  useEffect(() => {
    const ws = new MockWebSocket(`ws://localhost:8000/ws/liveness/${session.session_id}`);
    wsRef.current = ws;

    ws.onopen = () => {
      // In real mode, start sending JPEG frames to the server
      if (!USE_MOCK && videoRef.current) {
        stopCaptureRef.current = startFrameCapture(videoRef.current, ws, 15);
      }
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "frame_result") {
        setState("detecting");
        setFrame(msg.frame_index + 1);
      } else if (msg.type === "challenge") {
        setState("challenge");
        setChallenge(msg.instruction);
        // Continue sending frames during challenge (already running in real mode)
      } else if (msg.type === "challenge_frame") {
        setChallengeProgress({ received: msg.frames_received, needed: msg.frames_needed });
      } else if (msg.type === "liveness_result") {
        // Stop sending frames
        stopCaptureRef.current?.();
        if (msg.is_live) {
          setState("passed");
          setTimeout(() => onComplete(), 1500);
        } else if (msg.hitl_required) {
          setState("hitl");
        } else {
          setState("failed");
        }
      } else if (msg.type === "error") {
        stopCaptureRef.current?.();
        setError(msg.detail);
        setState("error");
      }
    };

    return () => {
      stopCaptureRef.current?.();
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-xl mx-auto px-6 py-10">
      <div className="flex justify-between items-end mb-6">
        <h2 className="text-2xl font-semibold">Face Verification</h2>
        <span className="lw-label">Step 2 of 6</span>
      </div>

      <div className="relative bg-ink aspect-[4/3] overflow-hidden">
        <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div style={{ width: "60%", height: "80%", border: "3px solid var(--amber)", borderRadius: "50%" }} />
        </div>
      </div>

      <div className="mt-6 text-center min-h-[80px]">
        {state === "scanning" && (
          <p className="flex items-center justify-center gap-2 text-sm">
            <span className="lw-pulse-dot" /> Keep your face inside the oval — scanning...
          </p>
        )}
        {state === "detecting" && (
          <div>
            <p className="text-sm">Face detected — analyzing...</p>
            <p className="lw-label mt-2">Frame {frame} of 15</p>
          </div>
        )}
        {state === "challenge" && (
          <div>
            <p className="text-lg font-semibold text-amber">{challenge}</p>
            {challengeProgress && (
              <div className="mt-3">
                <div className="h-2 bg-surface-container-high w-full max-w-xs mx-auto">
                  <div
                    className="h-full bg-amber transition-all"
                    style={{ width: `${(challengeProgress.received / challengeProgress.needed) * 100}%` }}
                  />
                </div>
                <p className="lw-label mt-2">{challengeProgress.received} / {challengeProgress.needed} frames</p>
              </div>
            )}
          </div>
        )}
        {state === "passed" && (
          <div className="flex flex-col items-center gap-3">
            <div className="lw-checkmark-circle">
              <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="3">
                <path d="M5 12l5 5L20 7" />
              </svg>
            </div>
            <p className="text-status-green-fg font-semibold">Identity Verified ✓</p>
          </div>
        )}
        {state === "hitl" && (
          <p className="text-status-orange-fg">Our team will verify this manually. You'll hear back within 2 hours.</p>
        )}
        {state === "failed" && (
          <p className="text-destructive">Verification failed. Please contact support.</p>
        )}
        {state === "error" && (
          <p className="text-destructive">Error: {error || "Something went wrong. Please try again."}</p>
        )}
      </div>
    </div>
  );
}

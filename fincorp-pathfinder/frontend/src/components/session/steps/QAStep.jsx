import React, { useEffect, useRef, useState } from "react";
import { MockWebSocket } from "@/mock/websocket";
import { AudioCapture } from "@/lib/audioCapture";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

export default function QAStep({ session, cameraStream, setCameraStream, onComplete }) {
  const wsRef = useRef(null);
  const tickRef = useRef(null);
  const videoRef = useRef(null);
  const audioCaptureRef = useRef(null);
  const retryTimerRef = useRef(null);

  const [qIdx, setQIdx] = useState(0);
  const [qText, setQText] = useState("");
  const [phase, setPhase] = useState("display");
  const [timer, setTimer] = useState(8);
  const [maxTimer, setMaxTimer] = useState(8);
  const [chunks, setChunks] = useState([]);
  const [flash, setFlash] = useState(null);
  const [retryOffer, setRetryOffer] = useState(null);
  const [error, setError] = useState(null);

  // Camera stream attach (reuse from parent)
  useEffect(() => {
    let cancelled = false;
    const attach = (s) => {
      if (videoRef.current) {
        videoRef.current.srcObject = s;
        videoRef.current.play().catch(() => {});
      }
    };
    if (cameraStream) attach(cameraStream);
    else if (typeof navigator !== "undefined" && navigator.mediaDevices) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        setCameraStream(s); attach(s);
      }).catch(() => {});
    }
    return () => { cancelled = true; };
  }, [cameraStream, setCameraStream]);

  const startCountdown = (seconds) => {
    setTimer(seconds);
    setMaxTimer(seconds);
    if (tickRef.current) clearInterval(tickRef.current);
    const start = Date.now();
    tickRef.current = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      const left = Math.max(0, seconds - elapsed);
      setTimer(left);
      if (left <= 0) clearInterval(tickRef.current);
    }, 100);
  };

  // Start/stop PCM audio streaming based on phase (real mode only)
  const startAudioCapture = () => {
    if (USE_MOCK || !cameraStream) return;
    const capture = new AudioCapture();
    audioCaptureRef.current = capture;
    capture.onChunk = (buf) => {
      if (wsRef.current?.readyState === 1) {
        wsRef.current.send(buf);
      }
    };
    capture.onSilenceTimeout = () => {
      if (wsRef.current?.readyState === 1) {
        wsRef.current.send(JSON.stringify({ type: "silence_timeout" }));
      }
    };
    capture.start(cameraStream);
  };

  const stopAudioCapture = () => {
    audioCaptureRef.current?.stop();
    audioCaptureRef.current = null;
  };

  useEffect(() => {
    const ws = new MockWebSocket(`ws://localhost:8000/ws/qa/${session.session_id}`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);

      if (msg.type === "question") {
        setQIdx(msg.index);
        setQText(msg.text);
        setPhase(msg.phase);
        setRetryOffer(null);
        if (msg.phase === "display") {
          setChunks([]);
          startCountdown(msg.display_seconds || 8);
          stopAudioCapture(); // mic off during display
        } else {
          startCountdown(msg.timer_seconds || 10);
          startAudioCapture(); // mic on during answer
        }
      } else if (msg.type === "transcript_chunk") {
        setChunks((prev) => [...prev.slice(-2), msg.text]);
      } else if (msg.type === "auto_advance") {
        // Server detected 2.5s silence — stop recording, move to next question
        stopAudioCapture();
      } else if (msg.type === "extraction_result") {
        setFlash(msg.confidence_tier);
        setTimeout(() => setFlash(null), 1500);
      } else if (msg.type === "retry_offer") {
        // Low confidence — offer to retry this question
        stopAudioCapture();
        setRetryOffer(msg);
        // Auto-dismiss after 10 seconds
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
        retryTimerRef.current = setTimeout(() => setRetryOffer(null), 10000);
      } else if (msg.type === "pipeline_started" || msg.type === "processing") {
        stopAudioCapture();
        onComplete();
      } else if (msg.type === "error") {
        stopAudioCapture();
        setError(msg.detail);
      }
    };

    return () => {
      ws.close();
      stopAudioCapture();
      if (tickRef.current) clearInterval(tickRef.current);
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const manualAdvance = () => {
    stopAudioCapture();
    // Don't touch qIdx here — the server sends the next question message
    // which sets it. Optimistic front-end increments race with server state
    // and cause the counter to bounce back.
    setChunks([]);
    setRetryOffer(null);
    setPhase("waiting");
    wsRef.current?.send(JSON.stringify({ type: "manual_advance" }));
  };

  const acceptRetry = () => {
    setRetryOffer(null);
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    wsRef.current?.send(JSON.stringify({ type: "retry_accept" }));
    // Server will send a new question message with phase: "answer"
  };

  const skipDisplay = () => {
    wsRef.current?.send(JSON.stringify({ type: "skip_display" }));
    setPhase("waiting");
  };

  const fillPct = maxTimer > 0 ? (timer / maxTimer) * 100 : 0;
  const barColor = phase === "display" ? "var(--amber)" : "oklch(0.70 0.15 150)";

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 md:py-10">
      {/* Mobile: video on top */}
      <div className="md:hidden mb-4 relative bg-ink h-[200px] border-2 border-amber overflow-hidden">
        <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
        <span className="lw-cam-label"><span className="lw-pulse-dot-red" /> Recording</span>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* LEFT column */}
        <div className="md:w-3/5 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <span className="lw-label text-amber">Q{qIdx + 1} of 8</span>
            <span className="lw-label">Step 4 of 6</span>
          </div>

          <div className="flex-1 flex flex-col justify-center min-h-[200px]">
            <p className="text-xl md:text-3xl font-semibold text-center leading-snug min-h-[5rem]">
              {qText || "Loading..."}
            </p>

            <div className="mt-8">
              <div className="h-2 bg-surface-container-high w-full">
                <div className="h-full transition-all duration-100 linear"
                  style={{ width: `${fillPct}%`, background: barColor }} />
              </div>
              <p className="lw-label mt-3 text-center">
                {phase === "display" ? "Read the question — press Start Answering when ready" : "Speak your answer now"}
              </p>
            </div>

            {phase === "answer" && (
              <div className="mt-6 flex justify-center items-end h-10">
                {[0, 1, 2, 3, 4].map((i) => (
                  <span key={i} className="lw-mic-bar" style={{ animationDelay: `${i * 0.08}s` }} />
                ))}
              </div>
            )}
          </div>

          {/* Retry offer banner */}
          {retryOffer && (
            <div className="mt-4 lw-card p-4 bg-status-amber-bg border-amber flex items-center justify-between gap-4">
              <p className="text-sm">{retryOffer.message}</p>
              <button onClick={acceptRetry} className="lw-btn lw-btn-primary text-xs px-4 py-2 whitespace-nowrap min-h-[36px]">
                Answer Again
              </button>
            </div>
          )}

          <div className="mt-6 min-h-[80px] border-t border-border pt-4">
            <p className="lw-label mb-2">Transcript</p>
            <div className="text-sm text-on-surface-variant space-y-1 min-h-[3rem] max-h-[120px] overflow-y-auto">
              {chunks.map((c, i) => (
                <p key={i} className={i === chunks.length - 1 ? "text-on-surface" : ""}>{c}</p>
              ))}
            </div>
          </div>

          {phase === "waiting" ? (
            <div className="mt-4 w-full py-4 text-center text-on-surface-variant text-sm">
              <span className="inline-block w-4 h-4 border-2 border-on-surface-variant border-t-transparent rounded-full animate-spin mr-2 align-middle" />
              {qIdx >= 7 ? "Processing your answers…" : "Loading next question…"}
            </div>
          ) : phase === "display" ? (
            <div className="mt-4 flex gap-3">
              <button
                onClick={skipDisplay}
                className="lw-btn lw-btn-primary flex-1 py-4 min-h-[44px]"
              >
                Start Answering Now →
              </button>
              <button
                onClick={manualAdvance}
                className="lw-btn lw-btn-secondary px-5 py-4 min-h-[44px] text-sm"
              >
                Skip
              </button>
            </div>
          ) : (
            <button
              onClick={manualAdvance}
              className="lw-btn lw-btn-primary mt-4 w-full py-4 min-h-[44px]"
            >
              Stop & go to next question →
            </button>
          )}

          {error && (
            <p className="mt-4 text-sm text-destructive text-center">Error: {error}</p>
          )}
        </div>

        {/* RIGHT column — desktop only */}
        <div className="hidden md:block md:w-2/5">
          <div className="relative bg-ink border-2 border-amber overflow-hidden h-full min-h-[400px]">
            <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
            <span className="lw-cam-label"><span className="lw-pulse-dot-red" /> Recording</span>
          </div>
        </div>
      </div>

      {flash && (
        <div className={"fixed bottom-12 left-1/2 -translate-x-1/2 px-6 py-2 lw-badge " +
          (flash === "green" ? "bg-status-green-bg text-status-green-fg" : "bg-status-amber-bg text-status-amber-fg")}>
          ✓ Answer captured
        </div>
      )}
    </div>
  );
}

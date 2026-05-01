import React, { useEffect, useRef, useState } from "react";
import { MockWebSocket } from "@/mock/websocket";
import { AudioCapture } from "@/lib/audioCapture";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

export default function ConsentStep({ session, cameraStream, setCameraStream, onComplete }) {
  const wsRef = useRef(null);
  const videoRef = useRef(null);
  const audioCaptureRef = useRef(null);
  const [consentText, setConsentText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [result, setResult] = useState(null);
  const [helpline, setHelpline] = useState(false);
  const [error, setError] = useState(null);
  const [recording, setRecording] = useState(false);

  // Acquire stream if missing (e.g. jumped here via demo shortcut)
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

  const connectWs = () => {
    wsRef.current?.close();
    const ws = new MockWebSocket(`ws://localhost:8000/ws/consent/${session.session_id}`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);

      if (msg.type === "ready") {
        setConsentText(msg.consent_text);
      } else if (msg.type === "transcript") {
        setTranscript(msg.text);
      } else if (msg.type === "consent_result") {
        if (msg.helpline_required) {
          setHelpline(true); setResult(null);
        } else if (msg.replay_required) {
          setResult({ replay: true }); setTranscript("");
        } else if (msg.is_valid) {
          setResult({ ok: true });
          setTimeout(() => onComplete(), 1500);
        }
      } else if (msg.type === "replay_required") {
        setResult({ replay: true, reason: msg.reason });
        setTranscript(""); setRecording(false); setHelpline(false);
      } else if (msg.type === "helpline_required") {
        setHelpline(true); setResult(null); setRecording(false);
      } else if (msg.type === "error") {
        setError(msg.detail); setRecording(false);
      }
    };
  };

  useEffect(() => {
    connectWs();
    return () => {
      wsRef.current?.close();
      audioCaptureRef.current?.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Start recording consent audio (real mode only)
  const startRecording = async () => {
    if (USE_MOCK || !cameraStream) return;
    // Reconnect if WS is closed (e.g. after max attempts exhausted)
    if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
      connectWs();
      await new Promise((r) => setTimeout(r, 300)); // let WS handshake complete
    }
    setResult(null); setHelpline(false); setError(null); setRecording(true);
    const capture = new AudioCapture();
    audioCaptureRef.current = capture;

    const pcmBuffer = await capture.captureBlob(cameraStream, 5000);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(pcmBuffer);
    }
    setRecording(false);
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      {/* Camera PiP */}
      <div className="lw-cam-pip">
        <video ref={videoRef} muted playsInline />
        <span className="lw-cam-label"><span className="lw-pulse-dot-red" /> Recording</span>
      </div>
      <p className="fixed top-[170px] right-4 z-50 text-[10px] text-on-surface-variant flex items-center gap-1 w-[200px] justify-center">
        Recording in progress
      </p>

      <div className="flex justify-between items-end mb-6">
        <h2 className="text-2xl font-semibold">Consent</h2>
        <span className="lw-label">Step 3 of 6</span>
      </div>

      <div className="lw-card p-6 mb-6 bg-surface-container-high">
        {consentText ? (
          <p className="text-base leading-relaxed">{consentText}</p>
        ) : (
          <p className="text-on-surface-variant text-sm">Loading consent text…</p>
        )}
      </div>

      <p className="text-sm text-on-surface-variant text-center mb-6">
        Please say "I agree" or "Yes, I consent" clearly after the text is read.
      </p>

      <div className="flex flex-col items-center gap-4">
        {!result && !helpline && !error && (
          <>
            <div className="flex items-end h-10">
              <span className="lw-mic-bar" style={{ animationDelay: "0s" }} />
              <span className="lw-mic-bar" style={{ animationDelay: "0.1s" }} />
              <span className="lw-mic-bar" style={{ animationDelay: "0.2s" }} />
              <span className="lw-mic-bar" style={{ animationDelay: "0.15s" }} />
              <span className="lw-mic-bar" style={{ animationDelay: "0.05s" }} />
            </div>
            <p className="lw-label">{recording ? "Recording..." : "Listening"}</p>

            {/* In real mode, show a button to start recording if not auto-capturing */}
            {!USE_MOCK && consentText && !recording && (
              <button onClick={startRecording} className="lw-btn lw-btn-primary mt-2 min-h-[44px]">
                Tap to Speak
              </button>
            )}
          </>
        )}
        {transcript && !result?.ok && (
          <p className="text-sm text-on-surface-variant">We heard: <span className="italic">"{transcript}"</span></p>
        )}
        {result?.ok && <p className="text-status-green-fg font-semibold">✓ Consent recorded</p>}
        {result?.replay && (
          <div className="text-center">
            <p className="text-status-orange-fg">{result.reason || "Please try again."}</p>
            {!USE_MOCK && (
              <button onClick={startRecording} className="lw-btn lw-btn-primary mt-3 min-h-[44px]">
                Try Again
              </button>
            )}
          </div>
        )}
        {helpline && (
          <div className="text-center space-y-3">
            <p className="text-destructive">Please call our helpline: 1800-555-0000</p>
            {!USE_MOCK && (
              <button onClick={startRecording} className="lw-btn lw-btn-outline mt-2">
                Try Again
              </button>
            )}
          </div>
        )}
        {error && <p className="text-destructive">Error: {error}</p>}
      </div>
    </div>
  );
}

import React, { useEffect, useRef, useState } from "react";
import ProgressBar from "@/components/session/ProgressBar";
import WelcomeStep from "@/components/session/steps/WelcomeStep";
import LivenessStep from "@/components/session/steps/LivenessStep";
import ConsentStep from "@/components/session/steps/ConsentStep";
import PanStep from "@/components/session/steps/PanStep";
import QAStep from "@/components/session/steps/QAStep";
import ProcessingStep from "@/components/session/steps/ProcessingStep";
import OfferStep from "@/components/session/steps/OfferStep";
import DeclinedStep from "@/components/session/steps/DeclinedStep";
import ManualReviewStep from "@/components/session/steps/ManualReviewStep";
import ExpiredStep from "@/components/session/steps/ExpiredStep";
import DemoBadge from "@/components/DemoBadge";
import { getSession } from "@/lib/apiClient";

export default function SessionFlow({ token }) {
  const [step, setStep] = useState("loading");
  const [session, setSession] = useState(null);
  const [offer, setOffer] = useState(null);
  const [error, setError] = useState(null);
  const [cameraStream, setCameraStream] = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    let alive = true;

    // Attempt to get geolocation (non-blocking — used if available)
    let geo = {};
    const geoPromise = new Promise((resolve) => {
      if (typeof navigator === "undefined" || !navigator.geolocation) return resolve();
      navigator.geolocation.getCurrentPosition(
        (pos) => { geo = { latitude: pos.coords.latitude, longitude: pos.coords.longitude }; resolve(); },
        () => resolve(), // denied — continue without it
        { timeout: 3000, maximumAge: 60000 },
      );
    });

    geoPromise.then(() => {
      if (!alive) return;
      getSession(token, geo)
        .then((s) => { if (!alive) return; setSession(s); setStep("welcome"); })
        .catch((e) => {
          if (!alive) return;
          const status = e?.status;
          const detail = e?.detail;

          if (status === 410) {
            setStep("expired");
          } else if (status === 401) {
            setError("Invalid session link. Please request a new one.");
            setStep("error");
          } else if (status === 403) {
            if (detail === "velocity_fraud_pause") {
              setError("Too many recent applications. Our team will review and contact you.");
            } else if (detail === "prohibited_ip" || detail === "tor_exit_node") {
              setError("Access denied from your network. Please try from a different connection.");
            } else {
              setError("Access denied. Please contact support.");
            }
            setStep("error");
          } else if (status === 409) {
            setError("This session has already been completed.");
            setStep("error");
          } else {
            setError(e?.message || "Failed to load session");
            setStep("error");
          }
        });
    });

    return () => { alive = false; };
  }, [token]);

  // Keep ref synced
  useEffect(() => { streamRef.current = cameraStream; }, [cameraStream]);

  // Stop camera when entering processing/offer/declined/expired or unmount
  useEffect(() => {
    if (["processing", "offer", "declined", "review", "expired", "error"].includes(step)) {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        setCameraStream(null);
      }
    }
  }, [step]);

  useEffect(() => () => {
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
  }, []);

  // Demo emergency escape: Ctrl+Shift+O jumps directly to Offer with mock data
  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey && e.shiftKey && (e.key === "O" || e.key === "o")) {
        e.preventDefault();
        setOffer({
          eligible: true,
          approved_amount: 400000,
          interest_rate_pct: 12.5,
          recommended_tenure_months: 24,
          emi_options: [
            { tenure_months: 12, emi_amount: 35611, total_payable: 427332 },
            { tenure_months: 24, emi_amount: 18942, total_payable: 454608 },
            { tenure_months: 36, emi_amount: 13332, total_payable: 479952 },
          ],
          processing_fee_pct: 2.0,
          offer_ref_id: "OFR-DEMO-ESCAPE",
          offer_valid_until: "2026-05-30T10:15:00+00:00",
          approval_reasons: [
            "Strong credit history (score 742)",
            "Stable employment — 6 years at TCS",
            "Low existing EMI obligations (FOIR: 0.14)",
          ],
          risk_band: "MEDIUM_LOW",
        });
        setStep("offer");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const showProgress = !["expired", "error", "loading"].includes(step);

  return (
    <div className="min-h-screen bg-surface">
      {showProgress && <ProgressBar current={step} />}

      {step === "loading" && (
        <div className="max-w-md mx-auto p-12 text-center text-on-surface-variant">Loading your session...</div>
      )}
      {step === "welcome" && session && (
        <WelcomeStep session={session} onNext={() => setStep("liveness")} onJump={(s) => setStep(s)} />
      )}
      {step === "liveness" && session && (
        <LivenessStep
          session={session}
          cameraStream={cameraStream}
          setCameraStream={setCameraStream}
          onComplete={() => setStep("pan")}
        />
      )}
      {step === "pan" && session && (
        <PanStep session={session} onComplete={() => setStep("consent")} />
      )}
      {step === "consent" && session && (
        <ConsentStep
          session={session}
          cameraStream={cameraStream}
          setCameraStream={setCameraStream}
          onComplete={() => setStep("qa")}
        />
      )}
      {step === "qa" && session && (
        <QAStep
          session={session}
          cameraStream={cameraStream}
          setCameraStream={setCameraStream}
          onComplete={() => setStep("processing")}
        />
      )}
      {step === "processing" && session && (
        <ProcessingStep
          session={session}
          onResult={(kind, data) => { setOffer(data); setStep(kind); }}
        />
      )}
      {step === "offer" && offer && <OfferStep offer={offer} />}
      {step === "declined" && <DeclinedStep result={offer} />}
      {step === "review" && <ManualReviewStep />}
      {step === "expired" && <ExpiredStep />}
      {step === "error" && (
        <div className="max-w-md mx-auto p-12 text-center">
          <h1 className="text-xl font-semibold">Something went wrong</h1>
          <p className="text-sm text-on-surface-variant mt-2">{error}</p>
        </div>
      )}

      <DemoBadge />
    </div>
  );
}

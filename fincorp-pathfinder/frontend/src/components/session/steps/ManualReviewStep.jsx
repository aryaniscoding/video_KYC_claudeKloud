import React from "react";

export default function ManualReviewStep() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-12 text-center">
      <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center bg-status-blue-bg text-status-blue-fg">
        <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
        </svg>
      </div>

      <h1 className="text-2xl md:text-3xl font-semibold">Application Under Review</h1>
      <p className="text-on-surface-variant mt-3 max-w-md mx-auto">
        Your application has been submitted successfully and is being reviewed by our team.
        We'll contact you within <strong>24 hours</strong> with the outcome.
      </p>

      <div className="lw-card p-6 mt-8 text-left space-y-4">
        <p className="lw-label">What happens next?</p>
        <ul className="space-y-3 text-sm">
          {[
            "Our credit team will review your application details.",
            "You will receive a call or email with the final decision.",
            "If approved, you'll get a link to review and sign your offer letter.",
          ].map((step, i) => (
            <li key={i} className="flex gap-3 items-start">
              <span className="lw-badge bg-status-blue-bg text-status-blue-fg shrink-0 mt-0.5">{i + 1}</span>
              <span className="text-on-surface-variant">{step}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-8 text-sm">Questions? Call <span className="font-semibold">1800-555-0000</span></p>
    </div>
  );
}

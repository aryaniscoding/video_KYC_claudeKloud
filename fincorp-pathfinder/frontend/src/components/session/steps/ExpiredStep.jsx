import React from "react";

export default function ExpiredStep() {
  return (
    <div className="max-w-md mx-auto px-6 py-20 text-center">
      <div className="lw-card p-8">
        <h1 className="text-2xl font-semibold">This link has expired</h1>
        <p className="mt-3 text-sm text-on-surface-variant">
          Please contact your loan officer to receive a new KYC link.
        </p>
        <p className="mt-6 text-sm">Call <span className="font-semibold">1800-555-0000</span></p>
      </div>
    </div>
  );
}

import React from "react";

const STEPS = [
  { key: "welcome", label: "Welcome" },
  { key: "liveness", label: "Face Check" },
  { key: "pan", label: "PAN" },
  { key: "consent", label: "Consent" },
  { key: "qa", label: "Questions" },
  { key: "processing", label: "Processing" },
  { key: "result", label: "Result" },
];

export default function ProgressBar({ current }) {
  const resultSteps = ["offer", "declined"];
  const currentKey = resultSteps.includes(current) ? "result" : current;
  const idx = STEPS.findIndex((s) => s.key === currentKey);

  return (
    <div className="w-full px-4 md:px-6 py-5 border-b border-border bg-surface">
      <div className="max-w-3xl mx-auto flex items-start">
        {STEPS.map((s, i) => {
          const done = i < idx;
          const active = i === idx;
          const dotClass = active
            ? "w-3 h-3 bg-amber rounded-full lw-step-glow"
            : done
              ? "w-3 h-3 bg-amber rounded-full"
              : "w-3 h-3 border border-outline bg-transparent rounded-full";
          const labelClass = active
            ? "text-amber font-bold"
            : done
              ? "text-amber"
              : "text-on-surface-variant";
          return (
            <React.Fragment key={s.key}>
              <div className="flex flex-col items-center gap-2 flex-shrink-0">
                <div className={dotClass} />
                <span className={"text-[9px] md:text-[10px] uppercase tracking-wider text-center " + labelClass}>
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={"flex-1 h-px mt-[6px] mx-1 md:mx-2 " + (i < idx ? "bg-amber" : "bg-border")} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

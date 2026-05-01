import React from "react";

export default function StatusBadge({ status }) {
  const map = {
    "Link Sent": "bg-status-amber-bg text-status-amber-fg",
    "In Progress": "bg-status-blue-bg text-status-blue-fg",
    Approved: "bg-status-green-bg text-status-green-fg",
    Declined: "bg-status-red-bg text-status-red-fg",
    HITL: "bg-status-orange-bg text-status-orange-fg",
    Expired: "bg-status-gray-bg text-status-gray-fg",
    Dropped: "bg-status-gray-bg text-status-gray-fg",
    Processing: "bg-status-purple-bg text-status-purple-fg",
  };
  const cls = map[status] || "bg-status-gray-bg text-status-gray-fg";
  return (
    <span className={`lw-badge ${cls}`}>
      {status === "HITL" && <span aria-hidden>⚠</span>}
      {status}
    </span>
  );
}

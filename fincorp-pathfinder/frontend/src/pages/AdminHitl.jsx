import React, { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import NavBar from "@/components/admin/NavBar";
import DemoBadge from "@/components/DemoBadge";
import SessionStatusDrawer from "@/components/admin/SessionStatusDrawer";
import { getHitlQueue, submitHitlDecision } from "@/lib/apiClient";

function DeclineModal({ onConfirm, onCancel, submitting }) {
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 z-[60] bg-ink/60 flex items-center justify-center p-4" onClick={onCancel}>
      <div className="bg-surface rounded-xl shadow-2xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-1">Decline Application</h3>
        <p className="text-sm text-on-surface-variant mb-4">Provide a reason — this will be included in the rejection email sent to the customer.</p>
        <textarea
          autoFocus
          className="w-full rounded-lg border border-border bg-surface-container-low px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-destructive/40 mb-4"
          rows={3}
          placeholder="e.g. High debt-to-income ratio, insufficient employment tenure…"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          disabled={submitting}
        />
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="lw-btn lw-btn-outline text-sm px-4 py-2" disabled={submitting}>
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            disabled={submitting || !reason.trim()}
            className="lw-btn lw-btn-primary text-sm px-4 py-2 bg-destructive hover:bg-destructive/90 disabled:opacity-50"
          >
            {submitting ? "Declining…" : "Confirm Decline"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminHitl() {
  const navigate = useNavigate();
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawer, setDrawer] = useState(null);
  const [declineTarget, setDeclineTarget] = useState(null); // session_id being declined
  const [actionState, setActionState] = useState({}); // { [session_id]: "approving" | "declining" | "done_approve" | "done_decline" | "error" }
  const [submitting, setSubmitting] = useState(false);

  const reload = () => {
    getHitlQueue().then((q) => setQueue(q));
  };

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem("lw_admin_token")) {
      navigate({ to: "/admin/login" });
      return;
    }
    getHitlQueue().then((q) => { setQueue(q); setLoading(false); });
  }, [navigate]);

  const handleApprove = async (sessionId) => {
    setActionState((s) => ({ ...s, [sessionId]: "approving" }));
    try {
      await submitHitlDecision(sessionId, "approve", "");
      setActionState((s) => ({ ...s, [sessionId]: "done_approve" }));
      setTimeout(() => reload(), 1500);
    } catch {
      setActionState((s) => ({ ...s, [sessionId]: "error" }));
    }
  };

  const handleDeclineConfirm = async (reason) => {
    const sessionId = declineTarget;
    setSubmitting(true);
    setActionState((s) => ({ ...s, [sessionId]: "declining" }));
    try {
      await submitHitlDecision(sessionId, "decline", reason);
      setDeclineTarget(null);
      setActionState((s) => ({ ...s, [sessionId]: "done_decline" }));
      setTimeout(() => reload(), 1500);
    } catch {
      setActionState((s) => ({ ...s, [sessionId]: "error" }));
      setDeclineTarget(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="max-w-[1440px] mx-auto px-12 py-8">
        <h1 className="text-3xl font-semibold mb-6 tracking-tight">Manual Review</h1>
        {loading ? (
          <p className="text-on-surface-variant">Loading queue...</p>
        ) : queue.length === 0 ? (
          <div className="lw-card p-12 text-center text-on-surface-variant">No sessions pending review</div>
        ) : (
          <div className="lw-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-container border-b border-border">
                <tr>
                  {["Customer Name", "Session ID", "Flagged At", "Flag Reason", "Action"].map((h) => (
                    <th key={h} className="lw-label text-left px-4 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {queue.map((q) => {
                  const state = actionState[q.session_id];
                  const done = state === "done_approve" || state === "done_decline";
                  return (
                    <tr key={q.session_id} className="border-b border-border last:border-0">
                      <td className="px-4 py-3 font-medium">{q.customer_name}</td>
                      <td className="px-4 py-3 font-mono text-xs">{q.session_id}</td>
                      <td className="px-4 py-3 text-on-surface-variant">{new Date(q.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className="lw-badge bg-status-orange-bg text-status-orange-fg">{q.reason}</span>
                      </td>
                      <td className="px-4 py-3">
                        {done ? (
                          <span className={`text-sm font-semibold ${state === "done_approve" ? "text-status-green-fg" : "text-destructive"}`}>
                            {state === "done_approve" ? "✓ Approved" : "✕ Declined"}
                          </span>
                        ) : state === "error" ? (
                          <span className="text-sm text-destructive">Error — retry</span>
                        ) : (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleApprove(q.session_id)}
                              disabled={!!state}
                              className="rounded-lg bg-status-green-fg text-white font-semibold text-xs px-3 py-1.5 hover:opacity-90 disabled:opacity-50 transition-opacity"
                            >
                              {state === "approving" ? "…" : "✓ Approve"}
                            </button>
                            <button
                              onClick={() => setDeclineTarget(q.session_id)}
                              disabled={!!state}
                              className="rounded-lg bg-destructive text-white font-semibold text-xs px-3 py-1.5 hover:opacity-90 disabled:opacity-50 transition-opacity"
                            >
                              {state === "declining" ? "…" : "✕ Decline"}
                            </button>
                            <button
                              onClick={() => setDrawer(q)}
                              className="lw-btn lw-btn-outline text-xs px-3 py-1.5"
                            >
                              Review
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {declineTarget && (
        <DeclineModal
          onConfirm={handleDeclineConfirm}
          onCancel={() => setDeclineTarget(null)}
          submitting={submitting}
        />
      )}

      {drawer && (
        <SessionStatusDrawer
          customer={{ ...drawer, name: drawer.customer_name, status: "HITL" }}
          onClose={() => setDrawer(null)}
        />
      )}
      <DemoBadge />
    </div>
  );
}

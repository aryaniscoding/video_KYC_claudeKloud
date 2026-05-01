import React, { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import NavBar from "@/components/admin/NavBar";
import DemoBadge from "@/components/DemoBadge";
import SessionStatusDrawer from "@/components/admin/SessionStatusDrawer";
import { getHitlQueue } from "@/lib/apiClient";

export default function AdminHitl() {
  const navigate = useNavigate();
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawer, setDrawer] = useState(null);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem("lw_admin_token")) {
      navigate({ to: "/admin/login" });
      return;
    }
    getHitlQueue().then((q) => { setQueue(q); setLoading(false); });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="max-w-[1440px] mx-auto px-12 py-8">
        <h1 className="text-3xl font-semibold mb-6 tracking-tight">HITL Queue</h1>
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
                {queue.map((q) => (
                  <tr key={q.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 font-medium">{q.customer_name}</td>
                    <td className="px-4 py-3 font-mono text-xs">{q.session_id}</td>
                    <td className="px-4 py-3 text-on-surface-variant">{q.flagged_at}</td>
                    <td className="px-4 py-3">
                      <span className="lw-badge bg-status-orange-bg text-status-orange-fg">{q.flag_reason}</span>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => setDrawer(q)} className="lw-btn lw-btn-primary text-xs px-3 py-2">
                        Review Session
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

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

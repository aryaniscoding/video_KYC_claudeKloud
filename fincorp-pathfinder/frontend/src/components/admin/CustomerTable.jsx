import React, { useMemo, useState } from "react";
import StatusBadge from "./StatusBadge";
import SendLinkModal from "./SendLinkModal";
import SessionStatusDrawer from "./SessionStatusDrawer";
import { resendLink } from "@/lib/apiClient";

const STATUSES = ["All", "Link Sent", "In Progress", "Approved", "Declined", "Manual Review", "Expired", "Dropped", "Processing"];

export default function CustomerTable({ customers, onUpdate, onToast }) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [modalCustomer, setModalCustomer] = useState(null);
  const [drawerCustomer, setDrawerCustomer] = useState(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return customers.filter((c) => {
      const matchQ = !q || c.name.toLowerCase().includes(q) || c.phone.includes(q);
      const matchS = statusFilter === "All" || c.status === statusFilter;
      return matchQ && matchS;
    });
  }, [customers, search, statusFilter]);

  const handleResend = async (c) => {
    await resendLink(c.id);
    onUpdate && onUpdate(c.id, "Link Sent");
    onToast && onToast(`KYC link resent to ${c.name} ✓`);
  };

  return (
    <>
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          className="lw-input max-w-sm"
          placeholder="Search by name or phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="lw-input max-w-[180px]" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="lw-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-surface-container border-b border-border">
            <tr>
              {["Name", "Phone", "Product", "Date", "Status", "Actions"].map((h) => (
                <th key={h} className="lw-label text-left px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id} className="border-b border-border last:border-0 hover:bg-surface-container/50">
                <td className="px-4 py-3 font-medium">{c.name}</td>
                <td className="px-4 py-3 text-on-surface-variant">{c.phone}</td>
                <td className="px-4 py-3">{c.product}</td>
                <td className="px-4 py-3 text-on-surface-variant">{c.created_date}</td>
                <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex gap-2 flex-wrap">
                    {!["Approved", "Declined"].includes(c.status) && (
                      <button onClick={() => setModalCustomer(c)} className="lw-btn lw-btn-primary text-xs px-3 py-2 whitespace-nowrap">
                        Send KYC Link
                      </button>
                    )}
                    <button onClick={() => setDrawerCustomer(c)} className="lw-btn lw-btn-ghost text-xs px-3 py-2 underline">
                      View
                    </button>
                    {c.status === "Expired" && (
                      <button onClick={() => handleResend(c)} className="lw-btn lw-btn-outline text-xs px-3 py-2">
                        Resend
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-on-surface-variant">No customers match the filter.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {modalCustomer && (
        <SendLinkModal
          customer={modalCustomer}
          onClose={() => setModalCustomer(null)}
          onSent={(id) => { onUpdate && onUpdate(id, "Link Sent"); onToast && onToast(`KYC link sent to ${modalCustomer.name} ✓`); }}
        />
      )}
      {drawerCustomer && (
        <SessionStatusDrawer customer={drawerCustomer} onClose={() => setDrawerCustomer(null)} />
      )}
    </>
  );
}

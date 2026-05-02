import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import NavBar from "@/components/admin/NavBar";
import CustomerTable from "@/components/admin/CustomerTable";
import AddCustomerModal from "@/components/admin/AddCustomerModal";
import DemoBadge from "@/components/DemoBadge";
import { getCustomers } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 30_000;

export default function AdminCustomers() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const pollRef = useRef(null);

  const fetchCustomers = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const c = await getCustomers();
      setCustomers(c);
    } finally {
      setLoading(false);
      if (!silent) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem("lw_admin_token")) {
      navigate({ to: "/admin/login" });
      return;
    }
    fetchCustomers();
    pollRef.current = setInterval(() => fetchCustomers(true), POLL_INTERVAL_MS);
    return () => clearInterval(pollRef.current);
  }, [navigate, fetchCustomers]);

  const updateStatus = () => fetchCustomers(true);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="max-w-[1440px] mx-auto px-12 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-semibold tracking-tight">Customers</h1>
          <div className="flex gap-3">
            <button
              onClick={() => fetchCustomers()}
              disabled={refreshing}
              className="lw-btn lw-btn-outline px-4 text-sm"
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
            <button onClick={() => setShowAddModal(true)} className="lw-btn lw-btn-primary px-5">
              + Add Customer
            </button>
          </div>
        </div>
        {loading ? (
          <p className="text-on-surface-variant">Loading customers...</p>
        ) : (
          <CustomerTable customers={customers} onUpdate={updateStatus} onToast={showToast} />
        )}
      </main>

      {showAddModal && (
        <AddCustomerModal
          onClose={() => setShowAddModal(false)}
          onAdded={(c) => {
            setCustomers((prev) => {
              if (prev.some((x) => x.id === c.id)) return prev;
              const formatted = { ...c, status: "No Session", phone: `****${c.phone_last4}`, product: c.product_code, created_date: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) };
              return [formatted, ...prev];
            });
            showToast(`Customer ${c.name} added ✓`);
          }}
        />
      )}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 lw-card px-5 py-3 bg-ink text-white">
          {toast}
        </div>
      )}
      <DemoBadge />
    </div>
  );
}

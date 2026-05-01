import React from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";

export default function NavBar() {
  const navigate = useNavigate();
  const name = typeof window !== "undefined" ? localStorage.getItem("lw_admin_name") || "Admin" : "Admin";
  const path = useRouterState({ select: (s) => s.location.pathname });

  const signOut = () => {
    localStorage.removeItem("lw_admin_token");
    localStorage.removeItem("lw_admin_name");
    navigate({ to: "/admin/login" });
  };

  return (
    <>
      <header className="bg-ink text-white">
        <div className="max-w-[1440px] mx-auto px-12 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="lw-wordmark text-lg">LOAN WIZARD</span>
            <span className="lw-badge bg-white/10 text-white/80">Admin</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-white/80">{name}</span>
            <button onClick={signOut} className="lw-btn lw-btn-outline border-white/30 text-white hover:!text-amber hover:!border-amber">
              Sign Out
            </button>
          </div>
        </div>
      </header>
      <nav className="bg-surface border-b border-border">
        <div className="max-w-[1440px] mx-auto px-12 flex">
          {[
            { to: "/admin/customers", label: "All Customers" },
            { to: "/admin/hitl", label: "HITL Queue" },
          ].map((t) => {
            const active = path === t.to;
            return (
              <Link
                key={t.to}
                to={t.to}
                className={`lw-label px-4 py-4 border-b-2 ${active ? "border-amber text-amber" : "border-transparent hover:text-amber"}`}
              >
                {t.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}

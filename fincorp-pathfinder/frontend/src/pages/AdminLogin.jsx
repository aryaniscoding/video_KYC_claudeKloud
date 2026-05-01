import React, { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { adminLogin } from "@/lib/apiClient";
import DemoBadge from "@/components/DemoBadge";

export default function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@poonawalla.com");
  const [password, setPassword] = useState("admin123");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const r = await adminLogin(email, password);
      localStorage.setItem("lw_admin_token", r.token);
      localStorage.setItem("lw_admin_name", r.name);
      navigate({ to: "/admin/customers" });
    } catch {
      setError("Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink text-white flex flex-col items-center justify-center px-4 py-10">
      <div className="text-center mb-8">
        <h1 className="lw-wordmark text-4xl md:text-5xl">LOAN WIZARD</h1>
        <p className="text-sm text-white/60 mt-2 tracking-wider">Poonawalla Fincorp — Admin Portal</p>
      </div>

      <div className="lw-card w-full max-w-md p-8 text-on-surface">
        <h2 className="text-xl font-semibold mb-6">Sign In</h2>
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="lw-label block mb-2">Email</label>
            <input className="lw-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="lw-label block mb-2">Password</label>
            <div className="relative">
              <input className="lw-input pr-20" type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required />
              <button type="button" onClick={() => setShow(!show)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-on-surface-variant hover:text-amber px-2 py-1">
                {show ? "HIDE" : "SHOW"}
              </button>
            </div>
          </div>
          <button type="submit" disabled={loading} className="lw-btn lw-btn-primary w-full py-3">
            {loading ? "Signing in..." : "Sign In"}
          </button>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </form>
      </div>

      <DemoBadge />
    </div>
  );
}

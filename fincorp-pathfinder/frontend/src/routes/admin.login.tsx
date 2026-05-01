import { createFileRoute } from "@tanstack/react-router";
import AdminLogin from "@/pages/AdminLogin";

export const Route = createFileRoute("/admin/login")({
  head: () => ({
    meta: [
      { title: "Sign In — Loan Wizard Admin" },
      { name: "description", content: "Admin sign in for Poonawalla Fincorp Loan Wizard." },
    ],
  }),
  component: AdminLogin,
});

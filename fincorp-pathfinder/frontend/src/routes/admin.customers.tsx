import { createFileRoute } from "@tanstack/react-router";
import AdminCustomers from "@/pages/AdminCustomers";

export const Route = createFileRoute("/admin/customers")({
  head: () => ({
    meta: [
      { title: "Customers — Loan Wizard Admin" },
      { name: "description", content: "Manage KYC sessions and customer applications." },
    ],
  }),
  component: AdminCustomers,
});

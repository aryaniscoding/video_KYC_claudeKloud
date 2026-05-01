import { createFileRoute } from "@tanstack/react-router";
import AdminHitl from "@/pages/AdminHitl";

export const Route = createFileRoute("/admin/hitl")({
  head: () => ({
    meta: [
      { title: "HITL Queue — Loan Wizard Admin" },
      { name: "description", content: "Sessions flagged for manual review." },
    ],
  }),
  component: AdminHitl,
});

import { createFileRoute } from "@tanstack/react-router";
import SessionFlow from "@/pages/SessionFlow";

export const Route = createFileRoute("/session/$token")({
  head: () => ({
    meta: [
      { title: "KYC Session — Loan Wizard" },
      { name: "description", content: "Complete your video KYC session for your personal loan." },
    ],
  }),
  component: SessionRoute,
});

function SessionRoute() {
  const { token } = Route.useParams();
  return <SessionFlow token={token} />;
}

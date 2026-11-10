import type { Metadata } from "next";

import { RecruiterDashboard } from "@/components/dashboard/recruiter-dashboard";

export const metadata: Metadata = { title: "Overview" };

export default function DashboardPage() {
  return <RecruiterDashboard />;
}

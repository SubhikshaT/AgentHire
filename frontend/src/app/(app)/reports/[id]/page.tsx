import type { Metadata } from "next";

import { ReportDetail } from "@/components/reports/reports";

export const metadata: Metadata = { title: "Report" };

export default function Page() {
  return <ReportDetail />;
}

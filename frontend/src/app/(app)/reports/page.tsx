import type { Metadata } from "next";

import { ReportsList } from "@/components/reports/reports";

export const metadata: Metadata = { title: "Reports" };

export default function Page() {
  return <ReportsList />;
}

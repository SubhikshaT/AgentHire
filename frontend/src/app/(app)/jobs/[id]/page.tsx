import type { Metadata } from "next";

import { JobDetail } from "@/components/jobs/job-detail";

export const metadata: Metadata = { title: "Job" };

export default function JobPage() {
  return <JobDetail />;
}

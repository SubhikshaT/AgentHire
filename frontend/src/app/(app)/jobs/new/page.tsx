import type { Metadata } from "next";

import { JobForm } from "@/components/jobs/job-form";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "New job" };

export default function NewJobPage() {
  return (
    <>
      <PageHeader
        title="New job"
        description="Jobs are saved as drafts. Publish when the requirements look right."
      />
      <JobForm />
    </>
  );
}

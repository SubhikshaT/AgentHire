import type { Metadata } from "next";

import { EditJob } from "@/components/jobs/edit-job";

export const metadata: Metadata = { title: "Edit job" };

export default function EditJobPage() {
  return <EditJob />;
}

import type { Metadata } from "next";

import { RecruiterInterview } from "@/components/interviews/recruiter-interviews";

export const metadata: Metadata = { title: "Interview" };

export default function Page() {
  return <RecruiterInterview />;
}

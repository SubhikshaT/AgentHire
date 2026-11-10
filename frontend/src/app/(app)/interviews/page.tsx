import type { Metadata } from "next";

import { InterviewsList } from "@/components/interviews/recruiter-interviews";

export const metadata: Metadata = { title: "Interviews" };

export default function Page() {
  return <InterviewsList />;
}

import type { Metadata } from "next";

import { InterviewsList } from "@/components/interviews/recruiter-interviews";

export const metadata: Metadata = { title: "My interviews" };

export default function Page() {
  return <InterviewsList candidate />;
}

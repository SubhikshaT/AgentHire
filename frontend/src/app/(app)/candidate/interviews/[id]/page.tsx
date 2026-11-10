import type { Metadata } from "next";

import { CandidateInterview } from "@/components/interviews/take-interview";

export const metadata: Metadata = { title: "Interview" };

export default function Page() {
  return <CandidateInterview />;
}

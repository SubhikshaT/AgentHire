import type { Metadata } from "next";

import { CandidateExplorer } from "@/components/candidates/explorer";

export const metadata: Metadata = { title: "Candidates" };

export default function CandidatesPage() {
  return <CandidateExplorer />;
}

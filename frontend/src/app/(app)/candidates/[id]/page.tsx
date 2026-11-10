import type { Metadata } from "next";

import { CandidatePage } from "@/components/candidates/candidate-page";

export const metadata: Metadata = { title: "Candidate" };

export default function Page() {
  return <CandidatePage />;
}

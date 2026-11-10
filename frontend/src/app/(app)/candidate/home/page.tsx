import type { Metadata } from "next";

import { CandidateHome } from "@/components/candidate/candidate-pages";

export const metadata: Metadata = { title: "Home" };

export default function Page() {
  return <CandidateHome />;
}

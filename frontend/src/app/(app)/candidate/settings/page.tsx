import type { Metadata } from "next";

import { CandidateSettings } from "@/components/candidate/candidate-pages";

export const metadata: Metadata = { title: "Settings" };

export default function Page() {
  return <CandidateSettings />;
}

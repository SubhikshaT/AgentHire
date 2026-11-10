import type { Metadata } from "next";

import { CandidateProfilePage } from "@/components/candidate/candidate-pages";

export const metadata: Metadata = { title: "My profile" };

export default function Page() {
  return <CandidateProfilePage />;
}

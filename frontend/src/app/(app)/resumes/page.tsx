import type { Metadata } from "next";

import { Screening } from "@/components/resumes/screening";

export const metadata: Metadata = { title: "Resume screening" };

export default function ResumesPage() {
  return <Screening />;
}

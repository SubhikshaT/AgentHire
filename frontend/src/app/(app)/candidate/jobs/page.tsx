import type { Metadata } from "next";

import { BrowseJobs } from "@/components/candidate/candidate-pages";

export const metadata: Metadata = { title: "Browse jobs" };

export default function Page() {
  return <BrowseJobs />;
}

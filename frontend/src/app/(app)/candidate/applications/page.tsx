import type { Metadata } from "next";

import { MyApplications } from "@/components/candidate/candidate-pages";

export const metadata: Metadata = { title: "My applications" };

export default function Page() {
  return <MyApplications />;
}

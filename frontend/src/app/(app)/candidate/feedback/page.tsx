import type { Metadata } from "next";

import { MyFeedback } from "@/components/candidate/candidate-pages";

export const metadata: Metadata = { title: "My feedback" };

export default function Page() {
  return <MyFeedback />;
}

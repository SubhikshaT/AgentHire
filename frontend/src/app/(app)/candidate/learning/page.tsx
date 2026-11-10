import type { Metadata } from "next";
import { Suspense } from "react";

import { LearningPage } from "@/components/candidate/learning-page";
import { LoadingBlock } from "@/components/common/states";

export const metadata: Metadata = { title: "Learning" };

export default function Page() {
  return (
    <Suspense fallback={<LoadingBlock />}>
      <LearningPage />
    </Suspense>
  );
}

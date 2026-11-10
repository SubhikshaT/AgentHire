import type { Metadata } from "next";
import { Suspense } from "react";

import { CompareCandidates } from "@/components/candidates/compare";
import { LoadingBlock } from "@/components/common/states";

export const metadata: Metadata = { title: "Compare candidates" };

export default function ComparePage() {
  return (
    <Suspense fallback={<LoadingBlock rows={4} />}>
      <CompareCandidates />
    </Suspense>
  );
}

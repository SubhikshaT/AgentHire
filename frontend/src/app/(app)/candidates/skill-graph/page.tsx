import type { Metadata } from "next";
import { Suspense } from "react";

import { SkillGraph } from "@/components/candidates/skill-graph";
import { LoadingBlock } from "@/components/common/states";

export const metadata: Metadata = { title: "Skill graph" };

export default function SkillGraphPage() {
  return (
    <Suspense fallback={<LoadingBlock rows={5} />}>
      <SkillGraph />
    </Suspense>
  );
}

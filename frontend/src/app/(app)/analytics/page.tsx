import type { Metadata } from "next";

import { SkillAnalytics } from "@/components/analytics/skill-analytics";

export const metadata: Metadata = { title: "Skill analytics" };

export default function Page() {
  return <SkillAnalytics />;
}

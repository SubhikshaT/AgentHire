"use client";

import { useSearchParams } from "next/navigation";

import { Learning } from "@/components/candidate/candidate-pages";

export function LearningPage() {
  const sp = useSearchParams();
  return <Learning initialApplication={sp.get("application") ?? undefined} />;
}

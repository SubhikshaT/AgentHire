"use client";

import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";

import { api } from "@/lib/api";
import type { LlmStatus } from "@/types/api";

export function useLlmStatus() {
  return useQuery({
    queryKey: ["llm-status"],
    queryFn: () => api<LlmStatus>("/settings/llm-status"),
    staleTime: 60_000,
  });
}

/** Shown wherever AI features are used, when no LLM is reachable. */
export function LlmBanner({ context }: { context?: string }) {
  const { data } = useLlmStatus();
  if (!data || data.available) return null;
  return (
    <div
      role="status"
      className="mb-4 flex gap-2.5 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <Info className="mt-0.5 size-4 shrink-0" />
      <p>
        <span className="font-medium">AI model not available.</span>{" "}
        {data.message}
        {context ? ` ${context}` : ""}
      </p>
    </div>
  );
}

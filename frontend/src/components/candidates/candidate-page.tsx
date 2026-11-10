"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ProfileView } from "@/components/candidates/profile-view";
import { ErrorState, LoadingBlock } from "@/components/common/states";
import { api } from "@/lib/api";
import type { Candidate } from "@/types/api";

export function CandidatePage() {
  const { id } = useParams<{ id: string }>();
  const q = useQuery({
    queryKey: ["candidate", id],
    queryFn: () => api<Candidate>(`/candidates/${id}`),
  });
  return (
    <>
      <Link
        href="/candidates"
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> All candidates
      </Link>
      {q.isPending ? (
        <LoadingBlock rows={5} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <ProfileView c={q.data} mode="recruiter" />
      )}
    </>
  );
}

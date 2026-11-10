"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { ErrorState, LoadingBlock } from "@/components/common/states";
import { JobForm } from "@/components/jobs/job-form";
import { PageHeader } from "@/components/layout/page-header";
import { api } from "@/lib/api";
import type { Job } from "@/types/api";

export function EditJob() {
  const { id } = useParams<{ id: string }>();
  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => api<Job>(`/jobs/${id}`),
  });
  if (job.isPending) return <LoadingBlock rows={4} />;
  if (job.isError)
    return <ErrorState error={job.error} onRetry={job.refetch} />;
  return (
    <>
      <PageHeader
        title={`Edit ${job.data.title}`}
        description="Changes are marked as edited by a person. Run matching again afterwards."
      />
      <JobForm job={job.data} />
    </>
  );
}

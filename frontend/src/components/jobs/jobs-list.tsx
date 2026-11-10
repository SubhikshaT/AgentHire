"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Briefcase, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { NativeSelect, SyntheticTag } from "@/components/common/bits";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/labels";
import type { Job, Page } from "@/types/api";

const STATUS_TONE: Record<string, "default" | "secondary" | "outline"> = {
  published: "default",
  draft: "secondary",
  closed: "outline",
};

export function JobsList() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), page_size: "10" });
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["jobs", page, q, status],
    queryFn: () => api<Page<Job>>(`/jobs?${params}`),
    placeholderData: keepPreviousData,
  });
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader
        title="Jobs"
        description="Create jobs, review extracted requirements and publish them."
        actions={
          <Link href="/jobs/new" className={buttonVariants()}>
            <Plus /> New job
          </Link>
        }
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            aria-label="Search jobs"
            placeholder="Search title, department…"
            className="h-9 pl-8"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <NativeSelect
          aria-label="Filter by status"
          value={status}
          onChange={(e) => (setStatus(e.target.value), setPage(1))}
        >
          <option value="">All statuses</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
          <option value="closed">Closed</option>
        </NativeSelect>
      </div>

      {isPending ? (
        <LoadingBlock />
      ) : isError ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title={q || status ? "No jobs match your filters" : "No jobs yet"}
          text={
            q || status
              ? "Try a different search."
              : "Create your first job to start screening candidates."
          }
          action={
            !q && !status ? (
              <Link href="/jobs/new" className={buttonVariants()}>
                <Plus /> New job
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <ul className="bg-card divide-y rounded-xl border">
            {data.items.map((j) => (
              <li key={j.id}>
                <Link
                  href={`/jobs/${j.id}`}
                  className="hover:bg-muted/50 focus-visible:bg-muted/60 flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3.5 outline-none"
                >
                  <div className="min-w-0 flex-1 basis-full sm:basis-0">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium">{j.title}</p>
                      {j.is_synthetic && <SyntheticTag />}
                    </div>
                    <p className="text-muted-foreground truncate text-sm">
                      {[j.department, j.required_skills.slice(0, 4).join(", ")]
                        .filter(Boolean)
                        .join(" · ") || "No requirements yet"}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-muted-foreground tabular-nums">
                      {j.applicant_count} applicants
                    </span>
                    <span className="text-muted-foreground hidden sm:inline">
                      {fmtDate(j.created_at)}
                    </span>
                    <Badge
                      variant={STATUS_TONE[j.status]}
                      className="capitalize"
                    >
                      {j.status}
                    </Badge>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Page {page} of {pages} · {data.total} jobs
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= pages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

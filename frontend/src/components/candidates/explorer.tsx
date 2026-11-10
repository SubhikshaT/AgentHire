"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { GitCompareArrows, Search, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  NativeSelect,
  ScoreValue,
  SkillChip,
  StageBadge,
  SyntheticTag,
} from "@/components/common/bits";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { Button, buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { STAGES } from "@/lib/labels";
import type { CandidateListItem, Job, Page } from "@/types/api";

export function CandidateExplorer() {
  const [f, setF] = useState({
    q: "",
    job_id: "",
    stage: "",
    skill: "",
    min_experience: "",
    sort: "-created_at",
  });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string[]>([]);
  const set = (k: keyof typeof f, v: string) => {
    setF((s) => ({
      ...s,
      [k]: v,
      ...(k === "job_id" && !v && s.sort === "-score"
        ? { sort: "-created_at" }
        : {}),
    }));
    setPage(1);
    if (k === "job_id") setSelected([]);
  };
  const params = new URLSearchParams({
    page: String(page),
    page_size: "15",
    sort: f.sort,
  });
  for (const k of ["q", "job_id", "stage", "skill", "min_experience"] as const)
    if (f[k]) params.set(k, f[k]);

  const jobs = useQuery({
    queryKey: ["jobs-all"],
    queryFn: () => api<Page<Job>>("/jobs?page_size=100"),
  });
  const list = useQuery({
    queryKey: ["candidates", params.toString()],
    queryFn: () => api<Page<CandidateListItem>>(`/candidates?${params}`),
    placeholderData: keepPreviousData,
  });
  const pages = list.data
    ? Math.max(1, Math.ceil(list.data.total / list.data.page_size))
    : 1;
  const filtered = !!(
    f.q ||
    f.job_id ||
    f.stage ||
    f.skill ||
    f.min_experience
  );

  return (
    <>
      <PageHeader
        title="Candidates"
        description="Everyone who applied to or was uploaded for your jobs."
      />
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr_0.7fr_1fr]">
        <div className="relative">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            aria-label="Search candidates"
            placeholder="Name, email, summary…"
            className="h-9 pl-8"
            value={f.q}
            onChange={(e) => set("q", e.target.value)}
          />
        </div>
        <NativeSelect
          aria-label="Job"
          value={f.job_id}
          onChange={(e) => set("job_id", e.target.value)}
        >
          <option value="">All jobs</option>
          {jobs.data?.items.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title}
            </option>
          ))}
        </NativeSelect>
        <NativeSelect
          aria-label="Stage"
          value={f.stage}
          onChange={(e) => set("stage", e.target.value)}
        >
          <option value="">Any stage</option>
          {STAGES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </NativeSelect>
        <Input
          aria-label="Has skill"
          placeholder="Has skill, e.g. React"
          className="h-9"
          value={f.skill}
          onChange={(e) => set("skill", e.target.value)}
        />
        <Input
          aria-label="Minimum years"
          placeholder="Min yrs"
          inputMode="decimal"
          className="h-9"
          value={f.min_experience}
          onChange={(e) =>
            set("min_experience", e.target.value.replace(/[^\d.]/g, ""))
          }
        />
        <NativeSelect
          aria-label="Sort"
          value={f.sort}
          onChange={(e) => set("sort", e.target.value)}
        >
          <option value="-created_at">Newest</option>
          <option value="name">Name A–Z</option>
          <option value="-experience">Most experience</option>
          <option value="experience">Least experience</option>
          {f.job_id && <option value="-score">Best match (this job)</option>}
        </NativeSelect>
      </div>
      {f.job_id && (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">
            Select 2–4 candidates to compare for this job.
          </span>
          {selected.length >= 2 && (
            <Link
              href={`/candidates/compare?job=${f.job_id}&ids=${selected.join(",")}`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              <GitCompareArrows /> Compare {selected.length}
            </Link>
          )}
        </div>
      )}

      {list.isPending ? (
        <LoadingBlock rows={5} />
      ) : list.isError ? (
        <ErrorState error={list.error} onRetry={list.refetch} />
      ) : list.data.items.length === 0 ? (
        <EmptyState
          icon={Users}
          title={
            filtered ? "No candidates match these filters" : "No candidates yet"
          }
          text={
            filtered
              ? undefined
              : "Upload resumes for a job to see candidates here."
          }
        />
      ) : (
        <>
          <ul className="grid gap-3 md:grid-cols-2">
            {list.data.items.map((c) => {
              const app = f.job_id
                ? c.applications.find((a) => a.job_id === f.job_id)
                : c.applications[0];
              const checked = selected.includes(c.id);
              return (
                <li key={c.id} className="bg-card rounded-xl border p-4">
                  <div className="flex items-start gap-3">
                    {f.job_id && (
                      <Checkbox
                        className="mt-1"
                        aria-label={`Select ${c.full_name ?? "candidate"}`}
                        checked={checked}
                        disabled={!checked && selected.length >= 4}
                        onCheckedChange={(v) =>
                          setSelected((s) =>
                            v ? [...s, c.id] : s.filter((x) => x !== c.id),
                          )
                        }
                      />
                    )}
                    <div className="min-w-0 flex-1 basis-full sm:basis-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={`/candidates/${c.id}${f.job_id ? `?job=${f.job_id}` : ""}`}
                          className="truncate font-medium hover:underline"
                        >
                          {c.full_name ?? "Unnamed (still parsing?)"}
                        </Link>
                        {c.is_synthetic && <SyntheticTag />}
                      </div>
                      <p className="text-muted-foreground text-sm">
                        {c.total_experience_years != null
                          ? `${c.total_experience_years} yrs`
                          : "Experience not stated"}
                        {c.highest_education ? ` · ${c.highest_education}` : ""}
                      </p>
                    </div>
                    {app && <ScoreValue score={app.overall_score} />}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {c.top_skills.map((s) => (
                      <SkillChip key={s} name={s} />
                    ))}
                  </div>
                  <div className="text-muted-foreground mt-3 flex flex-wrap items-center gap-2 text-xs">
                    {c.applications.slice(0, 3).map((a) => (
                      <span
                        key={a.application_id}
                        className="inline-flex items-center gap-1.5"
                      >
                        {a.job_title}: <StageBadge stage={a.stage} />
                      </span>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {list.data.total} candidates
            </span>
            {pages > 1 && (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">
                  Page {page} of {pages}
                </span>
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
            )}
          </div>
        </>
      )}
    </>
  );
}

"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

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
import { AnswerCard } from "@/components/interviews/evaluation-view";
import { PageHeader } from "@/components/layout/page-header";
import {
  MatchExplanation,
  ScoreBreakdown,
} from "@/components/matching/match-explanation";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { fmtDate } from "@/lib/labels";
import type { Job, Page, Report, ReportListItem } from "@/types/api";

export function ReportsList() {
  const [q, setQ] = useState("");
  const [job, setJob] = useState("");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), page_size: "15" });
  if (q) params.set("q", q);
  if (job) params.set("job_id", job);
  const jobs = useQuery({
    queryKey: ["jobs-all"],
    queryFn: () => api<Page<Job>>("/jobs?page_size=100"),
  });
  const list = useQuery({
    queryKey: ["reports", params.toString()],
    queryFn: () => api<Page<ReportListItem>>(`/reports?${params}`),
    placeholderData: keepPreviousData,
  });
  const pages = list.data
    ? Math.max(1, Math.ceil(list.data.total / list.data.page_size))
    : 1;
  return (
    <>
      <PageHeader
        title="Reports"
        description="Evaluation reports built from stored match and interview results. Generate one from a candidate or an interview."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            aria-label="Search reports"
            placeholder="Candidate or job…"
            className="h-9 pl-8"
            value={q}
            onChange={(e) => (setQ(e.target.value), setPage(1))}
          />
        </div>
        <NativeSelect
          aria-label="Job"
          value={job}
          onChange={(e) => (setJob(e.target.value), setPage(1))}
        >
          <option value="">All jobs</option>
          {jobs.data?.items.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title}
            </option>
          ))}
        </NativeSelect>
      </div>
      {list.isPending ? (
        <LoadingBlock />
      ) : list.isError ? (
        <ErrorState error={list.error} onRetry={list.refetch} />
      ) : list.data.items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports yet"
          text="Open a candidate and choose “Generate report”, or generate one after an interview."
        />
      ) : (
        <>
          <ul className="bg-card divide-y rounded-xl border">
            {list.data.items.map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3"
              >
                <div className="min-w-0 flex-1 basis-full sm:basis-0">
                  <Link
                    href={`/reports/${r.id}`}
                    className="font-medium hover:underline"
                  >
                    {r.candidate_name ?? "Candidate"} · {r.job_title}
                  </Link>
                  {r.is_synthetic && (
                    <span className="ml-2">
                      <SyntheticTag />
                    </span>
                  )}
                  <p className="text-muted-foreground text-xs">
                    {fmtDate(r.generated_at, true)} ·{" "}
                    {r.has_interview ? "match + interview" : "match only"}
                  </p>
                </div>
                <span className="text-muted-foreground text-xs">Match</span>
                <ScoreValue score={r.overall_score} />
                <span className="text-muted-foreground text-xs">Interview</span>
                <ScoreValue score={r.interview_score} />
                <a
                  href={`/api/v1/reports/${r.id}/pdf`}
                  className={buttonVariants({ size: "sm", variant: "outline" })}
                >
                  <Download /> PDF
                </a>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="mt-4 flex justify-end gap-2">
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
        </>
      )}
    </>
  );
}

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const q = useQuery({
    queryKey: ["report", id],
    queryFn: () => api<Report>(`/reports/${id}`),
  });
  const add = useMutation({
    mutationFn: () =>
      api<Report>(`/reports/${id}/notes`, {
        method: "POST",
        body: { text: note },
      }),
    onSuccess: (r) => {
      qc.setQueryData(["report", id], r);
      setNote("");
      toast.success("Comment added");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (q.isPending) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;
  const r = q.data;
  const d = r.report_data;

  return (
    <>
      <Link
        href="/reports"
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> All reports
      </Link>
      <PageHeader
        title={`${d.candidate.name ?? "Candidate"} · ${d.job.title}`}
        description={`Generated ${fmtDate(r.generated_at, true)} by ${d.generated_by} · methodology ${r.methodology_version}`}
        actions={
          <a href={`/api/v1/reports/${r.id}/pdf`} className={buttonVariants()}>
            <Download /> Download PDF
          </a>
        }
      />
      {d.candidate.is_synthetic && (
        <p className="mb-4">
          <SyntheticTag /> This report is about a fictional demo candidate.
        </p>
      )}
      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <div className="space-y-5">
          {d.match ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  Job compatibility <ScoreValue score={d.match.overall_score} />
                </CardTitle>
                <CardDescription>
                  Rule-based match · calculated{" "}
                  {fmtDate(d.match.calculated_at, true)}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <ScoreBreakdown
                  ex={d.match.explanation}
                  overall={d.match.overall_score}
                />
                <MatchExplanation
                  ex={d.match.explanation}
                  overall={d.match.overall_score}
                  compact
                />
              </CardContent>
            </Card>
          ) : (
            <EmptyState
              title="No match result"
              text="Matching was not run for this application."
            />
          )}
          {d.interview && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  Interview assessment
                  {d.interview.total_score != null ? (
                    <ScoreValue score={d.interview.total_score} />
                  ) : (
                    <span className="text-muted-foreground text-sm font-normal">
                      Pending
                    </span>
                  )}
                </CardTitle>
                <CardDescription>
                  Rule-based assessment · {d.interview.summary.answered} answered ·{" "}
                  {d.interview.summary.evaluated} evaluated ·{" "}
                  {d.interview.summary.pending} pending · rubric{" "}
                  {d.interview.rubric_version}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ol className="space-y-3">
                  {d.interview.questions.map((x, i) => (
                    <AnswerCard key={x.id} q={x} index={i} />
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}
        </div>
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Candidate</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                Stage: <StageBadge stage={d.stage} />
              </p>
              <p>
                Experience:{" "}
                {d.candidate.total_experience_years != null
                  ? `${d.candidate.total_experience_years} years`
                  : "not stated"}
              </p>
              {d.candidate.education.slice(0, 2).map((e, i) => (
                <p key={i}>
                  {e.degree ?? e.level}{" "}
                  {e.institution ? `· ${e.institution}` : ""}
                </p>
              ))}
              <div className="flex flex-wrap gap-1 pt-1">
                {d.candidate.skills.map((s) => (
                  <SkillChip
                    key={s.name}
                    name={s.name}
                    tone={s.status === "manually_verified" ? "good" : "default"}
                  />
                ))}
              </div>
              <p className="text-muted-foreground text-xs">
                Green = confirmed by a person.
              </p>
              <Link
                href={`/candidates/${d.candidate.id}`}
                className="text-primary inline-flex items-center gap-1 text-sm font-medium hover:underline"
              >
                Open profile <ExternalLink className="size-3.5" />
              </Link>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Recruiter comments</CardTitle>
              <CardDescription>
                Written by people. Kept separate from AI-generated content.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {r.notes.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No comments yet.
                </p>
              ) : (
                <ul className="space-y-2">
                  {r.notes.map((n) => (
                    <li
                      key={n.id}
                      className="border-primary bg-muted/40 rounded-lg border-l-4 px-3 py-2 text-sm"
                    >
                      <p className="whitespace-pre-wrap">{n.text}</p>
                      <p className="text-muted-foreground mt-1 text-xs">
                        {n.label} · {n.author} · {fmtDate(n.created_at, true)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
              <form
                onSubmit={(e) => (
                  e.preventDefault(),
                  note.trim() && add.mutate()
                )}
                className="space-y-2"
              >
                <Textarea
                  aria-label="New comment"
                  rows={3}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Your assessment, next steps…"
                  maxLength={3000}
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={add.isPending || !note.trim()}
                >
                  {add.isPending && <Loader2 className="animate-spin" />} Add
                  comment
                </Button>
              </form>
            </CardContent>
          </Card>
          {d.learning_recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Learning recommendations</CardTitle>
                <CardDescription>
                  From a curated list of official docs and free courses.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {d.learning_recommendations.map((l) => (
                    <li key={l.key}>
                      <a
                        href={l.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary font-medium hover:underline"
                      >
                        {l.title}
                      </a>
                      <p className="text-muted-foreground text-xs">
                        {l.skill} ({l.priority}) · {l.difficulty} ·{" "}
                        {l.objective}
                      </p>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle>Limitations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-muted-foreground list-disc space-y-1 pl-4 text-xs">
                {d.limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

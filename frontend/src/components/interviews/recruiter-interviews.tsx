"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Loader2,
  MessageSquareText,
  Pencil,
  RefreshCw,
  ScrollText,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect, ScoreValue } from "@/components/common/bits";

import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import {
  AnswerCard,
  EvaluationSummary,
} from "@/components/interviews/evaluation-view";
import { QuestionEditor } from "@/components/interviews/question-editor";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api";
import { fmtDate } from "@/lib/labels";
import type { Interview, InterviewListItem } from "@/types/api";

const STATUS: Record<string, string> = {
  draft: "Draft",
  ready: "Ready for candidate",
  in_progress: "In progress",
  completed: "Completed",
};

export function InterviewsList({ candidate = false }: { candidate?: boolean }) {
  const [status, setStatus] = useState("");
  const q = useQuery({
    queryKey: ["interviews", status],
    queryFn: () =>
      api<InterviewListItem[]>(
        `/interviews${status ? `?status=${status}` : ""}`,
      ),
  });
  const base = candidate ? "/candidate/interviews" : "/interviews";
  return (
    <>
      <PageHeader
        title="Interviews"
        description={
          candidate
            ? "Interviews assigned to you and your practice interviews."
            : "Create interviews from a candidate's profile. Review questions, then let the candidate take it."
        }
        actions={
          <NativeSelect
            aria-label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All</option>
            {Object.entries(STATUS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </NativeSelect>
        }
      />
      {q.isPending ? (
        <LoadingBlock />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : q.data.length === 0 ? (
        <EmptyState
          icon={MessageSquareText}
          title="No interviews yet"
          text={
            candidate
              ? "When a recruiter assigns an interview it appears here. You can also start a practice interview from My Applications."
              : "Open a candidate profile and choose “Create interview”."
          }
          action={
            !candidate ? (
              <Link
                href="/candidates"
                className={buttonVariants({ variant: "outline" })}
              >
                Go to candidates
              </Link>
            ) : (
              <Link
                href="/candidate/applications"
                className={buttonVariants({ variant: "outline" })}
              >
                My applications
              </Link>
            )
          }
        />
      ) : (
        <ul className="bg-card divide-y rounded-xl border">
          {q.data.map((i) => (
            <li key={i.id}>
              <Link
                href={`${base}/${i.id}`}
                className="hover:bg-muted/50 flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3"
              >
                <div className="min-w-0 flex-1 basis-full sm:basis-0">
                  <p className="font-medium">
                    {candidate
                      ? i.job_title
                      : `${i.candidate_name ?? "Candidate"} · ${i.job_title}`}
                  </p>
                  <p className="text-muted-foreground text-xs">
                    {i.interview_type === "practice" ? "Practice" : "Assigned"}{" "}
                    · {i.difficulty} · {i.answered}/{i.question_count} answered
                    · created {fmtDate(i.created_at)}
                    {i.pending_evaluation
                      ? ` · ${i.pending_evaluation} awaiting evaluation`
                      : ""}
                  </p>
                </div>
                {i.total_score != null && <ScoreValue score={i.total_score} />}
                <Badge
                  variant={i.status === "completed" ? "default" : "secondary"}
                >
                  {STATUS[i.status]}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function RecruiterInterview() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const q = useQuery({
    queryKey: ["interview", id],
    queryFn: () => api<Interview>(`/interviews/${id}`),
    refetchInterval: (query) =>
      query.state.data?.status === "in_progress" ? 10_000 : false,
  });
  const regen = useMutation({
    mutationFn: () =>
      api<{ interview: Interview; notice: string | null }>(
        `/interviews/${id}/generate-questions`,
        { method: "POST" },
      ),
    onSuccess: (r) => {
      qc.setQueryData(["interview", id], r.interview);
      toast[r.notice ? "info" : "success"](
        r.notice ?? "New questions generated",
      );
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const evaluate = useMutation({
    mutationFn: () =>
      api<{
        evaluated: number;
        pending_llm: number;
        failed: number;
        llm_available: boolean;
      }>(`/interviews/${id}/evaluate`, { method: "POST" }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["interview", id] });
      if (!r.llm_available && r.pending_llm)
        toast.info(
          `${r.pending_llm} answer(s) still need an AI model to be scored.`,
        );
      else
        toast.success(
          `Evaluated ${r.evaluated} answer(s)${r.failed ? `, ${r.failed} failed` : ""}`,
        );
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const report = useMutation({
    mutationFn: () =>
      api<{ id: string }>("/reports/generate", {
        method: "POST",
        body: { application_id: q.data!.application_id, interview_id: id },
      }),
    onSuccess: (r) => router.push(`/reports/${r.id}`),
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (q.isPending) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;
  const iv = q.data;
  const pending = iv.questions.some(
    (x) => x.answer && x.answer.evaluation_status !== "evaluated",
  );
  const editable = iv.status === "draft" || iv.status === "ready";

  return (
    <>
      <Link
        href="/interviews"
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> All interviews
      </Link>
      <PageHeader
        title={`${iv.candidate_name ?? "Candidate"} · ${iv.job_title}`}
        description={`${iv.interview_type === "practice" ? "Practice" : "Assigned"} interview · ${iv.difficulty} · ${STATUS[iv.status]}${iv.completed_at ? ` · completed ${fmtDate(iv.completed_at, true)}` : ""}`}
        actions={
          <div className="flex flex-wrap gap-2">
            {editable && iv.can_manage && !editing && (
              <>
                <Button
                  variant="outline"
                  onClick={() => regen.mutate()}
                  disabled={regen.isPending}
                >
                  {regen.isPending ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <Sparkles />
                  )}{" "}
                  Regenerate
                </Button>
                <Button variant="outline" onClick={() => setEditing(true)}>
                  <Pencil /> Edit questions
                </Button>
              </>
            )}
            {iv.status === "completed" && pending && (
              <Button
                variant="outline"
                onClick={() => evaluate.mutate()}
                disabled={evaluate.isPending}
              >
                {evaluate.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <RefreshCw />
                )}{" "}
                Evaluate pending
              </Button>
            )}
            {iv.status === "completed" && (
              <Button
                onClick={() => report.mutate()}
                disabled={report.isPending}
              >
                {report.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <ScrollText />
                )}{" "}
                Generate report
              </Button>
            )}
          </div>
        }
      />
      
      {editable && (
        <div className="bg-secondary/40 mb-4 rounded-xl border px-4 py-3 text-sm">
          {iv.status === "ready"
            ? "Questions are ready. The candidate can start this interview from their Interviews page. You can still edit questions until they start."
            : "No questions yet. Use Regenerate to create them."}
        </div>
      )}
      {iv.status === "in_progress" && (
        <div className="mb-4 rounded-xl border px-4 py-3 text-sm">
          The candidate is taking this interview.{" "}
          {iv.questions.filter((x) => x.answer?.submitted_at).length}/
          {iv.questions.length} answered so far. This page refreshes every 10
          seconds.
        </div>
      )}
      {iv.status === "completed" && (
        <div className="mb-4">
          <EvaluationSummary iv={iv} />
        </div>
      )}
      {editing ? (
        <QuestionEditor iv={iv} onClose={() => setEditing(false)} />
      ) : iv.questions.length === 0 ? (
        <EmptyState title="No questions" />
      ) : iv.status === "completed" ? (
        <ol className="space-y-3">
          {iv.questions.map((x, i) => (
            <AnswerCard key={x.id} q={x} index={i} />
          ))}
        </ol>
      ) : (
        <ol className="space-y-2">
          {iv.questions.map((x, i) => (
            <li key={x.id} className="bg-card rounded-xl border p-4">
              <p className="font-medium">
                <span className="text-muted-foreground mr-2 tabular-nums">
                  Q{i + 1}
                </span>
                {x.question}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                {x.category_label} · {x.difficulty} ·{" "}
                {Math.round(x.time_limit_seconds / 60)} min ·{" "}
                {x.source.replace("_", " ")}
                {x.grounding ? ` · ${x.grounding}` : ""}
              </p>
              {!!x.expected_concepts?.length && (
                <p className="mt-2 text-xs">
                  <span className="font-medium">Expected concepts:</span>{" "}
                  {x.expected_concepts.join(", ")}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

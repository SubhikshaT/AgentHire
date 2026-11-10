"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Loader2,
  Play,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/common/confirm";
import { ErrorState, LoadingBlock } from "@/components/common/states";
import {
  AnswerCard,
  EvaluationSummary,
} from "@/components/interviews/evaluation-view";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { CATEGORIES } from "@/lib/labels";
import type { CurrentQuestion, Interview } from "@/types/api";

const AUTOSAVE_MS = 10_000;

function Runner({ iv, onFinished }: { iv: Interview; onFinished: () => void }) {
  const cur = useQuery({
    queryKey: ["current", iv.id],
    queryFn: () => api<CurrentQuestion>(`/interviews/${iv.id}/current`),
  });
  const finish = useMutation({
    mutationFn: () =>
      api<Interview>(`/interviews/${iv.id}/complete`, { method: "POST" }),
    onSuccess: () => {
      toast.success(
        "Interview submitted. Feedback appears here when it is ready.",
      );
      onFinished();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (cur.isPending) return <LoadingBlock rows={3} />;
  if (cur.isError)
    return <ErrorState error={cur.error} onRetry={cur.refetch} />;
  const d = cur.data;
  if (d.done) {
    return (
      <Card className="mx-auto max-w-xl text-center">
        <CardHeader>
          <CardTitle>All questions answered</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground text-sm">
            Submit the interview to get your evaluation.
          </p>
          <Button onClick={() => finish.mutate()} disabled={finish.isPending}>
            {finish.isPending && <Loader2 className="animate-spin" />} Submit
            interview
          </Button>
        </CardContent>
      </Card>
    );
  }
  return <QuestionPane key={d.question.id} iv={iv} d={d} finish={finish} />;
}

function QuestionPane({
  iv,
  d,
  finish,
}: {
  iv: Interview;
  d: Extract<CurrentQuestion, { done: false }>;
  finish: { mutate: () => void; isPending: boolean };
}) {
  const qc = useQueryClient();
  const q = d.question;
  const [text, setText] = useState(d.draft_text);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [remaining, setRemaining] = useState(d.seconds_remaining);
  const [confirmFinish, setConfirmFinish] = useState(false);
  const [confirmEmpty, setConfirmEmpty] = useState(false);
  const lastSaved = useRef(d.draft_text);

  useEffect(() => {
    const t = setInterval(() => setRemaining((r) => Math.max(0, r - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  const saveDraft = useCallback(async () => {
    if (text === lastSaved.current) return;
    try {
      await api(`/interviews/${iv.id}/answers/${q.id}/draft`, {
        method: "PUT",
        body: { text },
      });
      lastSaved.current = text;
      setSavedAt(new Date());
    } catch {
      /* next autosave will retry */
    }
  }, [iv.id, q.id, text]);

  useEffect(() => {
    const t = setInterval(saveDraft, AUTOSAVE_MS);
    return () => clearInterval(t);
  }, [saveDraft]);

  const submit = useMutation({
    mutationFn: () =>
      api<{ follow_up_question_id: string | null }>(
        `/interviews/${iv.id}/answers/${q.id}`,
        { method: "POST", body: { text } },
      ),
    onSuccess: (r) => {
      if (r.follow_up_question_id)
        toast.info("The interviewer has a follow-up question.");
      qc.invalidateQueries({ queryKey: ["current", iv.id] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const finishNow = async () => {
    setConfirmFinish(false);
    await saveDraft();
    finish.mutate();
  };

  const mm = Math.floor(remaining / 60);
  const ss = String(remaining % 60).padStart(2, "0");
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const pct = (d.answered / d.total) * 100;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center gap-3">
        <div
          className="bg-muted h-2 flex-1 rounded-full"
          role="progressbar"
          aria-valuenow={d.answered}
          aria-valuemin={0}
          aria-valuemax={d.total}
          aria-label="Progress"
        >
          <div
            className="bg-chart-1 h-2 rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-muted-foreground text-sm tabular-nums">
          {d.answered}/{d.total} done
        </span>
      </div>
      <Card>
        <CardHeader>
          <div className="text-muted-foreground flex flex-wrap items-center justify-between gap-2 text-xs">
            <span>
              Question {q.number} of {d.total} · {q.category_label} ·{" "}
              <span className="capitalize">{q.difficulty}</span>
              {q.is_follow_up ? " · follow-up" : ""}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium tabular-nums ${remaining === 0 ? "bg-destructive/10 text-destructive" : remaining <= 30 ? "bg-amber-100 text-amber-800" : "bg-muted"}`}
              aria-live={remaining <= 30 ? "polite" : "off"}
            >
              <Timer className="size-3.5" /> {mm}:{ss}
            </span>
          </div>
          <CardTitle className="mt-2 text-lg leading-snug">{q.text}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {remaining === 0 ? (
            <p
              role="alert"
              className="bg-destructive/10 text-destructive flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
            >
              <AlertTriangle className="size-4" /> Time is up for this question.
              Your answer was not submitted automatically — submit what you have
              when ready.
            </p>
          ) : remaining <= 30 ? (
            <p className="text-sm text-amber-800">
              30 seconds or less left. Nothing is submitted automatically.
            </p>
          ) : null}
          <Textarea
            aria-label="Your answer"
            rows={10}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your answer. Explain your reasoning and give examples where useful."
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-muted-foreground text-xs">
              {words} words ·{" "}
              {savedAt
                ? `draft saved ${savedAt.toLocaleTimeString()}`
                : "drafts save every 10 seconds"}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setConfirmFinish(true)}>
                Finish interview
              </Button>
              <Button
                onClick={() =>
                  text.trim() ? submit.mutate() : setConfirmEmpty(true)
                }
                disabled={submit.isPending}
              >
                {submit.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Check />
                )}{" "}
                Submit answer
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      <p className="text-muted-foreground mt-3 text-center text-xs">
        You can close this page and come back later — the interview resumes
        where you left off.
      </p>
      <ConfirmDialog
        open={confirmEmpty}
        onOpenChange={setConfirmEmpty}
        title="Submit an empty answer?"
        description="Empty answers are recorded as 'insufficient information'."
        confirmLabel="Submit empty answer"
        onConfirm={() => (setConfirmEmpty(false), submit.mutate())}
      />
      <ConfirmDialog
        open={confirmFinish}
        onOpenChange={setConfirmFinish}
        title="Finish the interview now?"
        description="Unanswered questions are submitted with whatever draft you have (or empty). You cannot change answers afterwards."
        confirmLabel="Finish interview"
        onConfirm={finishNow}
        pending={finish.isPending}
      />
    </div>
  );
}

export function CandidateInterview() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["interview", id],
    queryFn: () => api<Interview>(`/interviews/${id}`),
    refetchInterval: (query) => {
      const iv = query.state.data;
      return iv?.status === "completed" &&
        iv.questions.some((x) => x.answer?.evaluation_status === "pending_llm")
        ? 5000
        : false;
    },
  });
  const start = useMutation({
    mutationFn: () => api(`/interviews/${id}/start`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview", id] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (q.isPending) return <LoadingBlock rows={4} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;
  const iv = q.data;

  return (
    <>
      <Link
        href="/candidate/interviews"
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> My interviews
      </Link>
      {iv.status !== "in_progress" && (
        <PageHeader
          title={iv.job_title}
          description={`${iv.interview_type === "practice" ? "Practice" : "Interview"} · ${iv.difficulty} · ${iv.question_count} questions`}
        />
      )}
      {iv.status === "draft" && (
        <p className="text-muted-foreground text-sm">
          The recruiter is still preparing this interview.
        </p>
      )}
      {iv.status === "ready" && (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Before you start</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground space-y-3 text-sm">
            <ul className="list-disc space-y-1 pl-4">
              <li>
                Questions come one at a time. Each has a suggested time limit.
              </li>
              <li>
                Your answer is saved as a draft every 10 seconds. You can stop
                and resume later.
              </li>
              <li>Nothing is submitted automatically when time runs out.</li>
              <li>
                Answers are scored against a fixed rubric. Length alone does not
                earn points.
              </li>
              <li>
                Categories:{" "}
                {iv.categories
                  .map((c) => CATEGORIES.find((x) => x.value === c)?.label ?? c)
                  .join(", ")}
                .
              </li>
            </ul>
            <Button onClick={() => start.mutate()} disabled={start.isPending}>
              {start.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Play />
              )}{" "}
              Start interview
            </Button>
          </CardContent>
        </Card>
      )}
      {iv.status === "in_progress" && (
        <Runner
          iv={iv}
          onFinished={() =>
            qc.invalidateQueries({ queryKey: ["interview", id] })
          }
        />
      )}
      {iv.status === "completed" && (
        <div className="space-y-4">
          <EvaluationSummary iv={iv} />
          <ol className="space-y-3">
            {iv.questions.map((x, i) => (
              <AnswerCard key={x.id} q={x} index={i} />
            ))}
          </ol>
        </div>
      )}
    </>
  );
}

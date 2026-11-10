"use client";

import { CheckCircle2, CircleAlert, Clock, Quote } from "lucide-react";

import { ScoreValue, SkillChip } from "@/components/common/bits";
import { fmtScore, RUBRIC_LABELS, VERDICT_LABELS } from "@/lib/labels";
import type { Interview, InterviewQuestion } from "@/types/api";

function VerdictBadge({ v }: { v: string | null }) {
  if (!v) return null;
  const tone =
    v === "correct"
      ? "good"
      : v === "partially_correct"
        ? "warn"
        : v === "insufficient"
          ? "muted"
          : "bad";
  return <SkillChip name={VERDICT_LABELS[v] ?? v} tone={tone} />;
}

export function AnswerCard({
  q,
  index,
}: {
  q: InterviewQuestion;
  index: number;
}) {
  const a = q.answer;
  const fb = a?.feedback ?? {};
  return (
    <li className="bg-card rounded-xl border p-4">
      <div className="flex flex-wrap items-start gap-2">
        <span className="text-muted-foreground text-sm font-semibold tabular-nums">
          Q{index + 1}
        </span>
        <div className="min-w-0 flex-1 basis-full sm:basis-0">
          <p className="font-medium">{q.question}</p>
          <p className="text-muted-foreground mt-0.5 text-xs">
            {q.category_label} · {q.difficulty}
            {q.is_follow_up ? " · follow-up" : ""} · source:{" "}
            {q.source.replace("_", " ")}
            {q.grounding ? ` · ${q.grounding}` : ""}
          </p>
        </div>
        {a?.evaluation_status === "evaluated" && (
          <ScoreValue score={a.weighted_score} />
        )}
      </div>

      {!a ? (
        <p className="text-muted-foreground mt-3 text-sm">Not answered.</p>
      ) : (
        <div className="mt-3 space-y-3">
          <div className="bg-muted/60 rounded-lg p-3 text-sm whitespace-pre-wrap">
            {a.text || (
              <span className="text-muted-foreground italic">
                No answer was given.
              </span>
            )}
          </div>
          {a.evaluation_status === "evaluated" ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <VerdictBadge v={a.verdict} />
                <span className="text-muted-foreground text-xs">
                  Rule-based evaluation · {fb.method}
                </span>
              </div>
              {a.scores && (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-5">
                  {Object.entries(a.scores).map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-muted-foreground">
                        {RUBRIC_LABELS[k] ?? k}
                      </dt>
                      <dd className="font-medium tabular-nums">
                        {fmtScore(v, 0)}/10
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
              {fb.explanation && <p className="text-sm">{fb.explanation}</p>}
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                {!!fb.strengths?.length && (
                  <div>
                    <p className="mb-1 font-medium">Strengths</p>
                    <ul className="space-y-0.5">
                      {fb.strengths.map((s) => (
                        <li key={s} className="flex gap-1.5">
                          <CheckCircle2 className="text-success mt-0.5 size-3.5 shrink-0" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {!!fb.weaknesses?.length && (
                  <div>
                    <p className="mb-1 font-medium">Weaknesses</p>
                    <ul className="space-y-0.5">
                      {fb.weaknesses.map((s) => (
                        <li key={s} className="flex gap-1.5">
                          <CircleAlert className="text-destructive mt-0.5 size-3.5 shrink-0" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              {!!fb.missing_concepts?.length && (
                <p className="text-sm">
                  <span className="font-medium">Missing concepts:</span>{" "}
                  {fb.missing_concepts.join(", ")}
                </p>
              )}
              {fb.suggested_improvement && (
                <p className="text-sm">
                  <span className="font-medium">How to improve:</span>{" "}
                  {fb.suggested_improvement}
                </p>
              )}
              {!!fb.evidence_quotes?.length && (
                <ul className="text-muted-foreground space-y-1 text-xs">
                  {fb.evidence_quotes.map((qq) => (
                    <li key={qq} className="flex gap-1.5">
                      <Quote className="mt-0.5 size-3 shrink-0" />“{qq}”
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <div className="rounded-lg border border-dashed p-3 text-sm">
              <p className="flex items-center gap-1.5 font-medium">
                <Clock className="size-4" />
                {a.evaluation_status === "failed"
                  ? "Evaluation failed"
                  : "Evaluation pending"}
              </p>
              <p className="text-muted-foreground mt-1">
                {a.evaluation_status === "failed"
                  ? `The model's output could not be used (${fb.error ?? "invalid output"}). No score was given.`
                  : "No AI model is available, so this answer has not been scored. Nothing has been made up."}
              </p>
              {a.concept_coverage && (q.expected_concepts?.length ?? 0) > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium">
                    Basic concept coverage check (not a score)
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {a.concept_coverage.covered.map((c) => (
                      <SkillChip key={c} name={`✓ ${c}`} tone="good" />
                    ))}
                    {a.concept_coverage.missing.map((c) => (
                      <SkillChip key={c} name={c} tone="muted" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

export function EvaluationSummary({ iv }: { iv: Interview }) {
  const answers = iv.questions.map((q) => q.answer).filter(Boolean);
  const evaluated = answers.filter((a) => a!.evaluation_status === "evaluated");
  const verdicts = evaluated.reduce<Record<string, number>>(
    (m, a) => ((m[a!.verdict ?? "?"] = (m[a!.verdict ?? "?"] ?? 0) + 1), m),
    {},
  );
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="bg-card rounded-xl border p-4">
        <p className="text-muted-foreground text-xs">Overall interview score</p>
        <p className="mt-1 text-2xl font-semibold">
          {iv.total_score != null ? (
            <ScoreValue score={iv.total_score} />
          ) : (
            <span className="text-muted-foreground text-base">Pending</span>
          )}
        </p>
        <p className="text-muted-foreground text-xs">
          Average of answer scores · rubric {iv.rubric_version}
        </p>
      </div>
      <div className="bg-card rounded-xl border p-4">
        <p className="text-muted-foreground text-xs">Evaluated answers</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums">
          {evaluated.length}/{answers.length}
        </p>
      </div>
      <div className="bg-card rounded-xl border p-4">
        <p className="text-muted-foreground text-xs">Verdicts</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {Object.keys(verdicts).length ? (
            Object.entries(verdicts).map(([v, n]) => (
              <SkillChip key={v} name={`${VERDICT_LABELS[v] ?? v}: ${n}`} />
            ))
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

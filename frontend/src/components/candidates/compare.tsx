"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Link2, Minus } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { ScoreValue } from "@/components/common/bits";
import { ErrorState, LoadingBlock } from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { api } from "@/lib/api";
import { COMPONENT_LABELS, fmtScore } from "@/lib/labels";
import type { Match } from "@/types/api";

type CompareResult = {
  job_id: string;
  job_title: string;
  candidates: (
    | Match
    | {
        candidate_id: string;
        candidate_name: string | null;
        overall_score: null;
        explanation: null;
      }
  )[];
  skill_matrix: {
    skill: string;
    required: boolean;
    candidates: {
      candidate_id: string;
      status: string;
      evidence: string | null;
    }[];
  }[];
};

export function CompareCandidates() {
  const sp = useSearchParams();
  const job = sp.get("job") ?? "";
  const ids = (sp.get("ids") ?? "").split(",").filter(Boolean);
  const q = useQuery({
    queryKey: ["compare", job, ids.join(",")],
    queryFn: () =>
      api<CompareResult>("/matching/compare", {
        method: "POST",
        body: { job_id: job, candidate_ids: ids },
      }),
    enabled: !!job && ids.length >= 2,
  });
  if (!job || ids.length < 2)
    return (
      <ErrorState
        error={new Error("Choose a job and 2–4 candidates to compare.")}
      />
    );
  if (q.isPending) return <LoadingBlock rows={4} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;
  const d = q.data;
  const icon = (s: string) =>
    s === "matched" ? (
      <Check className="text-success mx-auto size-4" aria-label="matched" />
    ) : s === "related" ? (
      <Link2
        className="mx-auto size-4 text-amber-600"
        aria-label="related only"
      />
    ) : (
      <Minus
        className="text-muted-foreground mx-auto size-4"
        aria-label={s === "not_scored" ? "not scored" : "missing"}
      />
    );

  return (
    <>
      <Link
        href={`/jobs/${d.job_id}`}
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> {d.job_title}
      </Link>
      <PageHeader
        title="Compare candidates"
        description="Side by side, using the same evidence as the match explanation."
      />
      <div className="bg-card overflow-x-auto rounded-xl border">
        <table className="w-full min-w-[36rem] text-sm">
          <thead className="bg-muted/40 border-b">
            <tr>
              <th className="px-3 py-2.5 text-left font-medium">Criterion</th>
              {d.candidates.map((c) => (
                <th
                  key={c.candidate_id}
                  className="px-3 py-2.5 text-center font-medium"
                >
                  <Link
                    href={`/candidates/${c.candidate_id}?job=${d.job_id}`}
                    className="hover:underline"
                  >
                    {c.candidate_name ?? "Unnamed"}
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            <tr className="bg-secondary/30">
              <td className="px-3 py-2 font-medium">Overall match</td>
              {d.candidates.map((c) => (
                <td key={c.candidate_id} className="px-3 py-2 text-center">
                  <ScoreValue score={c.overall_score} />
                </td>
              ))}
            </tr>
            {Object.keys(COMPONENT_LABELS).map((k) => (
              <tr key={k}>
                <td className="text-muted-foreground px-3 py-2">
                  {COMPONENT_LABELS[k]}
                </td>
                {d.candidates.map((c) => (
                  <td
                    key={c.candidate_id}
                    className="px-3 py-2 text-center tabular-nums"
                  >
                    {"components" in c && c.components
                      ? `${fmtScore(c.components[k] * 100, 0)}%`
                      : "—"}
                  </td>
                ))}
              </tr>
            ))}
            {d.skill_matrix.map((row) => (
              <tr key={row.skill}>
                <td className="px-3 py-2">
                  {row.skill}{" "}
                  <span className="text-muted-foreground text-xs">
                    {row.required ? "required" : "preferred"}
                  </span>
                </td>
                {row.candidates.map((c) => (
                  <td
                    key={c.candidate_id}
                    className="px-3 py-2 text-center"
                    title={c.evidence ?? undefined}
                  >
                    {icon(c.status)}
                  </td>
                ))}
              </tr>
            ))}
            <tr>
              <td className="text-muted-foreground px-3 py-2">Experience</td>
              {d.candidates.map((c) => (
                <td
                  key={c.candidate_id}
                  className="px-3 py-2 text-center text-xs"
                >
                  {c.explanation?.experience.note ?? "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="text-muted-foreground mt-3 text-xs">
        Hover a tick to see the resume evidence. ✓ matched · link icon = related
        skill only · dash = no evidence.
      </p>
    </>
  );
}

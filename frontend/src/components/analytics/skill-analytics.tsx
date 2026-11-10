"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";

import { Bar } from "@/components/common/bits";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/labels";

type AuditRow = {
  id: string;
  agent: string;
  provider: string;
  model_id: string | null;
  prompt_version: string | null;
  rubric_version: string | null;
  input_refs: Record<string, string>;
  duration_ms: number | null;
  validation_passed: boolean;
  retry_count: number;
  error_message: string | null;
  human_edited: boolean;
  created_at: string;
};

function AuditTable() {
  const [page, setPage] = useState(1);
  const q = useQuery({
    queryKey: ["ai-audit", page],
    queryFn: () =>
      api<{ items: AuditRow[]; total: number; page_size: number }>(
        `/ai-audit?page=${page}`,
      ),
  });
  if (q.isPending) return <LoadingBlock />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;
  if (!q.data.items.length)
    return (
      <EmptyState
        title="No AI outputs yet"
        text="Question generation and answer evaluation are recorded here."
      />
    );
  const pages = Math.max(1, Math.ceil(q.data.total / q.data.page_size));
  return (
    <>
      <div className="bg-card overflow-x-auto rounded-xl border">
        <table className="w-full min-w-[48rem] text-sm">
          <thead className="bg-muted/40 text-muted-foreground border-b text-left text-xs">
            <tr>
              <th className="px-3 py-2">When</th>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Provider / model</th>
              <th className="px-3 py-2">Prompt / rubric</th>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Valid</th>
              <th className="px-3 py-2">Edited</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {q.data.items.map((r) => (
              <tr
                key={r.id}
                title={r.error_message ?? JSON.stringify(r.input_refs)}
              >
                <td className="px-3 py-2 whitespace-nowrap">
                  {fmtDate(r.created_at, true)}
                </td>
                <td className="px-3 py-2">{r.agent.replaceAll("_", " ")}</td>
                <td className="px-3 py-2">
                  {r.provider}
                  {r.model_id ? ` · ${r.model_id}` : ""}
                </td>
                <td className="px-3 py-2 text-xs">
                  {[r.prompt_version, r.rubric_version]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </td>
                <td className="px-3 py-2 tabular-nums">
                  {r.duration_ms != null ? `${r.duration_ms} ms` : "—"}
                  {r.retry_count ? ` (${r.retry_count} retries)` : ""}
                </td>
                <td className="px-3 py-2">
                  {r.validation_passed ? (
                    <CheckCircle2
                      className="text-success size-4"
                      aria-label="passed"
                    />
                  ) : (
                    <XCircle
                      className="text-destructive size-4"
                      aria-label="failed"
                    />
                  )}
                </td>
                <td className="px-3 py-2">{r.human_edited ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="mt-3 flex justify-end gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={page >= pages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      )}
      <p className="text-muted-foreground mt-2 text-xs">
        Hover a row to see input references or the error message.
      </p>
    </>
  );
}

export function SkillAnalytics() {
  const skills = useQuery({
    queryKey: ["an-skills"],
    queryFn: () =>
      api<{ skill: string; demand: number; candidates_with_skill: number }[]>(
        "/analytics/skills",
      ),
  });
  return (
    <>
      <PageHeader
        title="Skill analytics"
        description="Skill demand across your jobs and the AI audit log."
      />
      <Tabs defaultValue="skills">
        <TabsList className="mb-4">
          <TabsTrigger value="skills">Skill demand</TabsTrigger>
          <TabsTrigger value="audit">AI audit</TabsTrigger>
        </TabsList>
        <TabsContent value="skills">
          {skills.isPending ? (
            <LoadingBlock />
          ) : skills.isError ? (
            <ErrorState error={skills.error} />
          ) : !skills.data.length ? (
            <EmptyState title="No skill data yet" />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Most requested skills</CardTitle>
                <CardDescription>
                  Demand counts required skills as 1 and preferred as 0.5 per
                  job. Coverage = share of your applicants who have the skill.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {(() => {
                  const maxApplicants = Math.max(
                    1,
                    ...skills.data.map((s) => s.candidates_with_skill),
                  );
                  return (
                    <ul className="space-y-3">
                      {skills.data.map((s) => (
                        <li
                          key={s.skill}
                          className="grid grid-cols-[10rem_1fr_6rem] items-center gap-3 text-sm"
                        >
                          <span className="truncate font-medium">
                            {s.skill}
                          </span>
                          <Bar
                            value={s.candidates_with_skill / maxApplicants}
                          />
                          <span className="text-muted-foreground text-right text-xs tabular-nums">
                            {s.candidates_with_skill} have · {s.demand} jobs
                          </span>
                        </li>
                      ))}
                    </ul>
                  );
                })()}
              </CardContent>
            </Card>
          )}
        </TabsContent>
        <TabsContent value="audit">
          <AuditTable />
        </TabsContent>
      </Tabs>
    </>
  );
}

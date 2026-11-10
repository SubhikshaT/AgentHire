"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useLlmStatus } from "@/components/common/llm-banner";
import { ErrorState, LoadingBlock } from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useMe } from "@/hooks/use-auth";
import { api, errorMessage } from "@/lib/api";
import { COMPONENT_LABELS, fmtDate, RUBRIC_LABELS } from "@/lib/labels";

type Settings = {
  matching_weights: Record<string, number>;
  rubric_weights: Record<string, number>;
  default_matching_weights: Record<string, number>;
  default_rubric_weights: Record<string, number>;
  rubric_dimensions: Record<string, string>;
  rubric_version: string;
};

function WeightsEditor({
  title,
  description,
  labels,
  value,
  defaults,
  endpoint,
  hints,
}: {
  title: string;
  description: string;
  labels: Record<string, string>;
  value: Record<string, number>;
  defaults: Record<string, number>;
  endpoint: string;
  hints?: Record<string, string>;
}) {
  const qc = useQueryClient();
  const [w, setW] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(value).map(([k, v]) => [k, String(v)])),
  );
  const total = Object.values(w).reduce((s, v) => s + (Number(v) || 0), 0);
  const valid =
    Math.abs(total - 100) < 0.01 &&
    Object.values(w).every(
      (v) => v !== "" && Number(v) >= 0 && Number(v) <= 100,
    );
  const save = useMutation({
    mutationFn: () =>
      api(endpoint, {
        method: "PUT",
        body: {
          weights: Object.fromEntries(
            Object.entries(w).map(([k, v]) => [k, Number(v)]),
          ),
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      toast.success(
        "Weights saved. Re-run matching / evaluation to apply them.",
      );
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {Object.keys(labels).map((k) => (
          <div key={k} className="grid grid-cols-[1fr_6rem] items-center gap-3">
            <label htmlFor={`${endpoint}-${k}`} className="text-sm">
              {labels[k]}
              {hints?.[k] && (
                <span className="text-muted-foreground block text-xs">
                  {hints[k]}
                </span>
              )}
            </label>
            <Input
              id={`${endpoint}-${k}`}
              inputMode="decimal"
              value={w[k] ?? ""}
              onChange={(e) =>
                setW({ ...w, [k]: e.target.value.replace(/[^\d.]/g, "") })
              }
              className="text-right tabular-nums"
            />
          </div>
        ))}
        <p
          className={`text-sm tabular-nums ${valid ? "text-muted-foreground" : "text-destructive"}`}
          role="status"
        >
          Total: {total.toFixed(1)}{" "}
          {valid ? "✓" : "— must add up to exactly 100"}
        </p>
        <div className="flex gap-2">
          <Button
            onClick={() => save.mutate()}
            disabled={!valid || save.isPending}
          >
            {save.isPending && <Loader2 className="animate-spin" />} Save
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              setW(
                Object.fromEntries(
                  Object.entries(defaults).map(([k, v]) => [k, String(v)]),
                ),
              )
            }
          >
            Reset to defaults
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function AccountCard() {
  const { data: me } = useMe();
  if (!me) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[7rem_1fr] gap-y-2 text-sm">
          <dt className="text-muted-foreground">Name</dt>
          <dd>{me.name}</dd>
          <dt className="text-muted-foreground">Email</dt>
          <dd className="truncate">{me.email}</dd>
          <dt className="text-muted-foreground">Role</dt>
          <dd className="capitalize">{me.role}</dd>
          <dt className="text-muted-foreground">Joined</dt>
          <dd>{fmtDate(me.created_at)}</dd>
        </dl>
      </CardContent>
    </Card>
  );
}

export function LlmStatusCard() {
  const { data, isPending } = useLlmStatus();
  return (
    <Card>
      <CardHeader>
        <CardTitle>AI provider</CardTitle>
        <CardDescription>
          Configured in backend/.env. Keys are never sent to the browser.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {isPending || !data ? (
          <Loader2 className="animate-spin" />
        ) : (
          <>
            <p className="flex items-center gap-2">
              {data.available ? (
                <CheckCircle2 className="text-success size-4" />
              ) : (
                <XCircle className="text-destructive size-4" />
              )}
              <span className="font-medium capitalize">{data.provider}</span>
              {data.model && (
                <span className="text-muted-foreground">· {data.model}</span>
              )}
            </p>
            <p className="text-muted-foreground">{data.message}</p>
            {data.sends_data_externally && (
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
                Gemini is selected: question generation and answer evaluation
                send resume excerpts and answers to Google.
              </p>
            )}
            <p className="text-muted-foreground">
              Embeddings: {data.embedding_model} (local) · vector search:{" "}
              {data.vector_backend}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function RecruiterSettings() {
  const q = useQuery({
    queryKey: ["settings"],
    queryFn: () => api<Settings>("/settings"),
  });
  return (
    <>
      <PageHeader
        title="Settings"
        description="Account, AI provider status, scoring weights and privacy."
      />
      {q.isPending ? (
        <LoadingBlock rows={4} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-5">
            <AccountCard />
            <LlmStatusCard />
            <Card>
              <CardHeader>
                <CardTitle>Privacy and fairness</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground space-y-1.5 text-sm">
                <p>
                  • Names, emails, phone numbers and photos are never used in
                  scoring or sent in evaluation prompts.
                </p>
                <p>
                  • Candidates are never rejected automatically. Selected /
                  Rejected always need your confirmation.
                </p>
                <p>
                  • Imported candidates can be deleted from their profile page;
                  this removes their resume files too.
                </p>
                <p>
                  • Every AI output is recorded in the AI audit log (Skill
                  Analytics → AI audit).
                </p>
              </CardContent>
            </Card>
          </div>
          <div className="space-y-5">
            <WeightsEditor
              key={JSON.stringify(q.data.matching_weights)}
              title="Matching weights"
              description="How much each component counts in the 0–100 match score."
              labels={COMPONENT_LABELS}
              value={q.data.matching_weights}
              defaults={q.data.default_matching_weights}
              endpoint="/settings/weights"
            />
            <WeightsEditor
              key={JSON.stringify(q.data.rubric_weights)}
              title={`Answer rubric weights (${q.data.rubric_version})`}
              description="Each answer is scored 0–10 per dimension, then combined with these weights."
              labels={RUBRIC_LABELS}
              value={q.data.rubric_weights}
              defaults={q.data.default_rubric_weights}
              endpoint="/settings/rubric"
              hints={q.data.rubric_dimensions}
            />
          </div>
        </div>
      )}
    </>
  );
}

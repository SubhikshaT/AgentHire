"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  GitCompareArrows,
  Loader2,
  Pencil,
  Play,
  Trash2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { StageControl } from "@/components/applications/stage-control";
import {
  ScoreValue,
  SkillChip,
  StageBadge,
  SyntheticTag,
} from "@/components/common/bits";
import { ConfirmDialog } from "@/components/common/confirm";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import { MatchExplanation } from "@/components/matching/match-explanation";
import { ResumeUploader } from "@/components/resumes/resume-uploader";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, errorMessage } from "@/lib/api";
import { EDU_LEVELS, fmtDate } from "@/lib/labels";
import type { Application, Job, Match } from "@/types/api";

export function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [explain, setExplain] = useState<Match | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => api<Job>(`/jobs/${id}`),
  });
  const apps = useQuery({
    queryKey: ["job-apps", id],
    queryFn: () => api<Application[]>(`/jobs/${id}/applications`),
  });
  const results = useQuery({
    queryKey: ["match-results", id],
    queryFn: () => api<Match[]>(`/matching/jobs/${id}/results`),
  });

  const status = useMutation({
    mutationFn: (action: "publish" | "unpublish" | "close") =>
      api<Job>(`/jobs/${id}/${action}`, { method: "POST" }),
    onSuccess: (j) => {
      qc.setQueryData(["job", id], j);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      toast.success(`Job is now ${j.status}`);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const del = useMutation({
    mutationFn: () => api(`/jobs/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Job deleted");
      qc.invalidateQueries({ queryKey: ["jobs"] });
      router.replace("/jobs");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const run = useMutation({
    mutationFn: () =>
      api<{
        scored: number;
        skipped_no_parsed_resume: number;
        duration_ms: number;
      }>(`/matching/jobs/${id}/run`, { method: "POST" }),
    onSuccess: (r) => {
      toast.success(
        `Scored ${r.scored} candidate${r.scored === 1 ? "" : "s"} in ${(r.duration_ms / 1000).toFixed(1)} s` +
          (r.skipped_no_parsed_resume
            ? ` · ${r.skipped_no_parsed_resume} waiting for a parsed resume`
            : ""),
      );
      qc.invalidateQueries({ queryKey: ["match-results", id] });
      qc.invalidateQueries({ queryKey: ["job-apps", id] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (job.isPending) return <LoadingBlock rows={4} />;
  if (job.isError)
    return <ErrorState error={job.error} onRetry={job.refetch} />;
  const j = job.data;
  const edu = j.education_requirements[0];

  return (
    <>
      <Link
        href="/jobs"
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> All jobs
      </Link>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{j.title}</h1>
            <Badge
              variant={j.status === "published" ? "default" : "secondary"}
              className="capitalize"
            >
              {j.status}
            </Badge>
            {j.is_synthetic && <SyntheticTag />}
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            {[
              j.department,
              `${j.applicant_count} applicants`,
              `created ${fmtDate(j.created_at)}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {j.status !== "published" ? (
            <Button
              onClick={() => status.mutate("publish")}
              disabled={status.isPending}
            >
              Publish
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => status.mutate("unpublish")}
                disabled={status.isPending}
              >
                Unpublish
              </Button>
              <Button
                variant="outline"
                onClick={() => status.mutate("close")}
                disabled={status.isPending}
              >
                Close
              </Button>
            </>
          )}
          <Link
            href={`/jobs/${j.id}/edit`}
            className={buttonVariants({ variant: "outline" })}
          >
            <Pencil /> Edit
          </Link>
          <Button variant="destructive" onClick={() => setConfirmDelete(true)}>
            <Trash2 /> Delete
          </Button>
        </div>
      </div>

      <Tabs defaultValue="ranking">
        <TabsList className="mb-4">
          <TabsTrigger value="ranking">Ranking</TabsTrigger>
          <TabsTrigger value="applicants">Applicants</TabsTrigger>
          <TabsTrigger value="requirements">Requirements</TabsTrigger>
        </TabsList>

        <TabsContent value="ranking">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              {run.isPending ? <Loader2 className="animate-spin" /> : <Play />}{" "}
              Run matching
            </Button>
            <Button variant="outline" onClick={() => setUploadOpen(true)}>
              <Upload /> Upload resumes
            </Button>
            {selected.length >= 2 && (
              <Link
                href={`/candidates/compare?job=${j.id}&ids=${selected.join(",")}`}
                className={buttonVariants({ variant: "secondary" })}
              >
                <GitCompareArrows /> Compare {selected.length}
              </Link>
            )}
            <span className="text-muted-foreground text-xs">
              Tick 2–4 candidates to compare them side by side.
            </span>
          </div>
          {results.isPending ? (
            <LoadingBlock />
          ) : results.isError ? (
            <ErrorState error={results.error} onRetry={results.refetch} />
          ) : results.data.length === 0 ? (
            <EmptyState
              title="No ranking yet"
              text={
                j.applicant_count
                  ? "Run matching to score the applicants."
                  : "Upload resumes for this job, then run matching."
              }
            />
          ) : (
            <div className="bg-card overflow-x-auto rounded-xl border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-muted-foreground border-b text-left text-xs">
                  <tr>
                    <th className="w-10 px-3 py-2.5">
                      <span className="sr-only">Select</span>
                    </th>
                    <th className="px-3 py-2.5">#</th>
                    <th className="px-3 py-2.5">Candidate</th>
                    <th className="px-3 py-2.5">Score</th>
                    <th className="hidden px-3 py-2.5 md:table-cell">
                      Required skills
                    </th>
                    <th className="hidden px-3 py-2.5 lg:table-cell">Gaps</th>
                    <th className="px-3 py-2.5">Stage</th>
                    <th className="px-3 py-2.5">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {results.data.map((m) => {
                    const req = m.explanation.required_skills;
                    const checked = selected.includes(m.candidate_id);
                    return (
                      <tr key={m.id} className="hover:bg-muted/30">
                        <td className="px-3 py-2.5">
                          <Checkbox
                            aria-label={`Select ${m.candidate_name ?? "candidate"} for comparison`}
                            checked={checked}
                            disabled={!checked && selected.length >= 4}
                            onCheckedChange={(v) =>
                              setSelected((s) =>
                                v
                                  ? [...s, m.candidate_id]
                                  : s.filter((x) => x !== m.candidate_id),
                              )
                            }
                          />
                        </td>
                        <td className="text-muted-foreground px-3 py-2.5 tabular-nums">
                          {m.rank}
                        </td>
                        <td className="px-3 py-2.5">
                          <Link
                            href={`/candidates/${m.candidate_id}?job=${j.id}`}
                            className="font-medium hover:underline"
                          >
                            {m.candidate_name ?? "Unnamed candidate"}
                          </Link>
                          {m.is_synthetic && (
                            <span className="ml-2">
                              <SyntheticTag />
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <ScoreValue score={m.overall_score} />
                        </td>
                        <td className="hidden px-3 py-2.5 md:table-cell">
                          <span className="tabular-nums">
                            {req.matched.length}
                          </span>
                          <span className="text-muted-foreground">
                            {" "}
                            matched
                          </span>
                          {req.related.length > 0 && (
                            <span className="text-amber-700">
                              {" "}
                              · {req.related.length} related
                            </span>
                          )}
                        </td>
                        <td className="hidden max-w-56 px-3 py-2.5 lg:table-cell">
                          <div className="flex flex-wrap gap-1">
                            {req.missing.slice(0, 3).map((s) => (
                              <SkillChip key={s} name={s} tone="bad" />
                            ))}
                            {req.missing.length === 0 && (
                              <span className="text-muted-foreground text-xs">
                                none
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <StageBadge stage={m.stage} />
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setExplain(m)}
                          >
                            Why?
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        <TabsContent value="applicants">
          {apps.isPending ? (
            <LoadingBlock />
          ) : apps.isError ? (
            <ErrorState error={apps.error} onRetry={apps.refetch} />
          ) : apps.data.length === 0 ? (
            <EmptyState
              title="No applicants yet"
              text="Upload resumes or publish the job so candidates can apply."
              action={
                <Button onClick={() => setUploadOpen(true)}>
                  <Upload /> Upload resumes
                </Button>
              }
            />
          ) : (
            <ul className="bg-card divide-y rounded-xl border">
              {apps.data.map((a) => (
                <li
                  key={a.id}
                  className="flex flex-wrap items-center gap-3 px-4 py-3"
                >
                  <div className="min-w-0 flex-1 basis-full sm:basis-0">
                    <Link
                      href={`/candidates/${a.candidate_id}?job=${j.id}`}
                      className="font-medium hover:underline"
                    >
                      {a.candidate_name ?? "Parsing…"}
                    </Link>
                    <p className="text-muted-foreground text-xs">
                      {a.source === "candidate_applied"
                        ? "Applied"
                        : "Uploaded"}{" "}
                      {fmtDate(a.created_at)} · resume{" "}
                      {a.resume_status ?? "missing"}
                    </p>
                  </div>
                  <ScoreValue score={a.overall_score} />
                  <StageControl applicationId={a.id} stage={a.stage} />
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="requirements">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Requirements used for matching</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="mb-1 font-medium">Required skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {j.required_skills.map((s) => (
                      <SkillChip key={s} name={s} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-1 font-medium">Preferred skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {j.preferred_skills.length
                      ? j.preferred_skills.map((s) => (
                          <SkillChip key={s} name={s} tone="muted" />
                        ))
                      : "—"}
                  </div>
                </div>
                <p>
                  <span className="font-medium">Minimum experience:</span>{" "}
                  {j.minimum_experience != null
                    ? `${j.minimum_experience} years`
                    : "none"}
                </p>
                <p>
                  <span className="font-medium">Education:</span>{" "}
                  {edu
                    ? `${EDU_LEVELS.find((l) => l.value === edu.level)?.label ?? edu.level}${edu.fields.length ? ` in ${edu.fields.join(", ")}` : ""}`
                    : "none"}
                </p>
                <p>
                  <span className="font-medium">Certifications:</span>{" "}
                  {j.certifications.join("; ") || "none"}
                </p>
                <p>
                  <span className="font-medium">Soft skills (not scored):</span>{" "}
                  {j.soft_skills.join(", ") || "none"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm whitespace-pre-wrap">
                  {j.description || "No description."}
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this job?"
        description="This also removes its applications, match results, interviews and reports. Candidate profiles linked to other jobs are kept."
        confirmLabel="Delete job"
        destructive
        onConfirm={() => del.mutate()}
        pending={del.isPending}
      />
      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Upload resumes for {j.title}</DialogTitle>
          </DialogHeader>
          <ResumeUploader
            jobId={j.id}
            onDone={() => {
              setUploadOpen(false);
              qc.invalidateQueries({ queryKey: ["job-apps", id] });
              qc.invalidateQueries({ queryKey: ["job", id] });
            }}
          />
        </DialogContent>
      </Dialog>
      <Dialog open={!!explain} onOpenChange={(o) => !o && setExplain(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Why {explain?.candidate_name ?? "this candidate"} scored{" "}
              {explain?.overall_score.toFixed(1)}
            </DialogTitle>
          </DialogHeader>
          {explain && (
            <MatchExplanation
              ex={explain.explanation}
              overall={explain.overall_score}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

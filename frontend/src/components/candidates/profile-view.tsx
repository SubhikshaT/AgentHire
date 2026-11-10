"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  FileText,
  Loader2,
  Network,
  RefreshCw,
  ScrollText,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { EmptyState } from "@/components/common/states";
import {
  BasicsEditor,
  ListEditor,
  SkillsEditor,
  VerifiedTag,
} from "@/components/candidates/profile-editors";
import { CreateInterview } from "@/components/interviews/create-interview";
import { MatchExplanation } from "@/components/matching/match-explanation";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, errorMessage } from "@/lib/api";
import { fmtDate } from "@/lib/labels";
import type {
  AppSummary,
  Candidate,
  InterviewListItem,
  Match,
} from "@/types/api";

const SECTION_ORDER = [
  "skills",
  "experience",
  "projects",
  "certifications",
  "summary",
  "education",
  "manual",
];

function AppRow({
  a,
  recruiter,
  interviews,
  candidateId,
}: {
  a: AppSummary;
  recruiter: boolean;
  interviews: InterviewListItem[];
  candidateId: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const match = useQuery({
    queryKey: ["match", a.match_id],
    queryFn: () => api<Match>(`/matching/${a.match_id}`),
    enabled: open && !!a.match_id,
  });
  const report = useMutation({
    mutationFn: () =>
      api<{ id: string }>("/reports/generate", {
        method: "POST",
        body: { application_id: a.application_id },
      }),
    onSuccess: (r) => router.push(`/reports/${r.id}`),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const ivs = interviews.filter((i) => i.application_id === a.application_id);
  return (
    <li className="rounded-xl border p-3.5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1 basis-full sm:basis-0">
          {recruiter ? (
            <Link
              href={`/jobs/${a.job_id}`}
              className="font-medium hover:underline"
            >
              {a.job_title}
            </Link>
          ) : (
            <span className="font-medium">{a.job_title}</span>
          )}
          <p className="text-muted-foreground text-xs">
            Since {fmtDate(a.created_at)}
          </p>
        </div>
        <ScoreValue score={a.overall_score} />
        {recruiter ? (
          <StageControl applicationId={a.application_id} stage={a.stage} />
        ) : (
          <StageBadge stage={a.stage} />
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {a.match_id && (
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
            Match explanation
          </Button>
        )}
        {recruiter && (
          <>
            <CreateInterview
              applicationId={a.application_id}
              type="assigned"
              detailHref={(id) => `/interviews/${id}`}
            />
            <Link
              href={`/candidates/skill-graph?candidate=${candidateId}&job=${a.job_id}`}
              className={buttonVariants({ size: "sm", variant: "ghost" })}
            >
              <Network /> Skill graph
            </Link>
            <Button
              size="sm"
              variant="ghost"
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
          </>
        )}
      </div>
      {ivs.length > 0 && (
        <ul className="mt-3 space-y-1 border-t pt-2 text-sm">
          {ivs.map((i) => (
            <li key={i.id} className="flex flex-wrap items-center gap-2">
              <Link
                href={
                  recruiter
                    ? `/interviews/${i.id}`
                    : `/candidate/interviews/${i.id}`
                }
                className="hover:underline"
              >
                {i.interview_type === "practice" ? "Practice" : "Interview"} ·{" "}
                {i.difficulty}
              </Link>
              <span className="text-muted-foreground text-xs capitalize">
                {i.status.replace("_", " ")}
              </span>
              {i.total_score != null && (
                <ScoreValue score={i.total_score} className="text-xs" />
              )}
            </li>
          ))}
        </ul>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Match for {a.job_title}</DialogTitle>
          </DialogHeader>
          {match.data ? (
            <MatchExplanation
              ex={match.data.explanation}
              overall={match.data.overall_score}
            />
          ) : (
            <Loader2 className="mx-auto animate-spin" />
          )}
        </DialogContent>
      </Dialog>
    </li>
  );
}

export function ProfileView({
  c,
  mode,
}: {
  c: Candidate;
  mode: "recruiter" | "self";
}) {
  const qc = useQueryClient();
  const router = useRouter();
  const recruiter = mode === "recruiter";
  const [confirmDelete, setConfirmDelete] = useState(false);
  const interviews = useQuery({
    queryKey: ["interviews"],
    queryFn: () => api<InterviewListItem[]>("/interviews"),
  });
  const reprocess = useMutation({
    mutationFn: (rid: string) =>
      api(`/resumes/${rid}/reprocess`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Re-parsing started. Verified fields are kept.");
      setTimeout(() => qc.invalidateQueries({ queryKey: ["candidate"] }), 2500);
      setTimeout(
        () => qc.invalidateQueries({ queryKey: ["my-profile"] }),
        2500,
      );
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const del = useMutation({
    mutationFn: () => api(`/candidates/${c.id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Candidate and resume files deleted");
      qc.invalidateQueries();
      router.replace(recruiter ? "/candidates" : "/candidate/home");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const fv = c.field_verification ?? {};
  const skills = [...c.skills].sort(
    (a, b) =>
      SECTION_ORDER.indexOf(a.evidence_section ?? "") -
      SECTION_ORDER.indexOf(b.evidence_section ?? ""),
  );
  const latestPdf = c.resumes.find(
    (r) => r.parsing_status === "completed" && r.file_type === "pdf",
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {c.full_name ?? "Unnamed candidate"}
            </h1>
            {c.is_synthetic && <SyntheticTag />}
            <VerifiedTag status={fv.full_name} />
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            {[
              c.email,
              c.phone,
              c.total_experience_years != null
                ? `${c.total_experience_years} years experience`
                : "experience not stated",
            ]
              .filter(Boolean)
              .join(" · ")}
            {recruiter &&
              (c.has_account
                ? " · has an AgentHire account"
                : " · imported from resume")}
          </p>
        </div>
        <div className="flex gap-2">
          <BasicsEditor c={c} lockEmail={c.has_account} />
          {(!recruiter || !c.has_account) && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 /> {recruiter ? "Delete candidate" : "Delete my data"}
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
        <div className="space-y-5">
          {c.professional_summary && (
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">
                  {c.professional_summary}
                </p>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle>
                Skills{" "}
                <span className="text-muted-foreground ml-1 text-sm font-normal">
                  ({c.skills.length})
                </span>
              </CardTitle>
              <CardAction>
                <SkillsEditor c={c} />
              </CardAction>
            </CardHeader>
            <CardContent>
              {skills.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No skills extracted yet.
                </p>
              ) : (
                <ul className="divide-y text-sm">
                  {skills.map((s) => (
                    <li
                      key={s.id}
                      className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 py-2"
                    >
                      <span className="font-medium">{s.name}</span>
                      <SkillChip
                        name={s.evidence_section ?? "—"}
                        tone="muted"
                      />
                      {s.verification_status === "manually_verified" && (
                        <VerifiedTag status="manually_verified" />
                      )}
                      <span
                        className="text-muted-foreground w-full truncate text-xs"
                        title={s.evidence_text ?? undefined}
                      >
                        {s.evidence_text}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>
                Work experience <VerifiedTag status={fv.work_experience} />
              </CardTitle>
              <CardAction>
                <ListEditor c={c} field="work_experience" />
              </CardAction>
            </CardHeader>
            <CardContent>
              {c.work_experience.length === 0 ? (
                <p className="text-muted-foreground text-sm">None found.</p>
              ) : (
                <ol className="space-y-3 text-sm">
                  {c.work_experience.map((e, i) => (
                    <li key={i}>
                      <p className="font-medium">
                        {e.title ?? "Role"}
                        {e.company ? ` · ${e.company}` : ""}
                        {e.is_internship ? " (internship)" : ""}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        {e.start ?? "?"} → {e.end ?? "?"}
                        {e.months ? ` · ${e.months} months` : ""}
                      </p>
                      {e.description && (
                        <p className="text-muted-foreground mt-1">
                          {e.description}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>
                Projects <VerifiedTag status={fv.projects} />
              </CardTitle>
              <CardAction>
                <ListEditor c={c} field="projects" />
              </CardAction>
            </CardHeader>
            <CardContent>
              {c.projects.length === 0 ? (
                <p className="text-muted-foreground text-sm">None found.</p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {c.projects.map((p, i) => (
                    <li key={i}>
                      <p className="font-medium">{p.name}</p>
                      {p.description && (
                        <p className="text-muted-foreground">{p.description}</p>
                      )}
                      {!!p.skills?.length && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {p.skills.map((s) => (
                            <SkillChip key={s} name={s} tone="muted" />
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          {recruiter && (
            <Card>
              <CardHeader>
                <CardTitle>Applications</CardTitle>
              </CardHeader>
              <CardContent>
                {c.applications.length === 0 ? (
                  <p className="text-muted-foreground text-sm">
                    No applications to your jobs.
                  </p>
                ) : (
                  <ul className="space-y-3">
                    {c.applications.map((a) => (
                      <AppRow
                        key={a.application_id}
                        a={a}
                        recruiter
                        interviews={interviews.data ?? []}
                        candidateId={c.id}
                      />
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle>
                Education <VerifiedTag status={fv.education} />
              </CardTitle>
              <CardAction>
                <ListEditor c={c} field="education" />
              </CardAction>
            </CardHeader>
            <CardContent>
              {c.education.length === 0 ? (
                <p className="text-muted-foreground text-sm">None found.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {c.education.map((e, i) => (
                    <li key={i}>
                      <p className="font-medium">
                        {e.degree ?? e.level ?? "Degree"}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        {[e.institution, e.end_year, e.score]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>
                Certifications <VerifiedTag status={fv.certifications} />
              </CardTitle>
              <CardAction>
                <ListEditor c={c} field="certifications" />
              </CardAction>
            </CardHeader>
            <CardContent>
              {c.certifications.length === 0 ? (
                <p className="text-muted-foreground text-sm">None found.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {c.certifications.map((x, i) => (
                    <li key={i}>
                      {x.name}
                      {x.issuer ? ` · ${x.issuer}` : ""}
                      {x.year ? ` · ${x.year}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Resume files</CardTitle>
            </CardHeader>
            <CardContent>
              {c.resumes.length === 0 ? (
                <EmptyState icon={FileText} title="No resume uploaded" />
              ) : (
                <ul className="space-y-2 text-sm">
                  {c.resumes.map((r) => (
                    <li
                      key={r.id}
                      className="flex flex-wrap items-center gap-2"
                    >
                      <FileText className="text-muted-foreground size-4" />
                      <span className="min-w-0 flex-1 truncate">
                        {r.original_filename}
                      </span>
                      <span
                        className={
                          r.parsing_status === "failed"
                            ? "text-destructive text-xs"
                            : "text-muted-foreground text-xs"
                        }
                      >
                        {r.parsing_status}
                        {r.parsing_error ? `: ${r.parsing_error}` : ""}
                      </span>
                      <a
                        href={`/api/v1/resumes/${r.id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className={buttonVariants({
                          size: "icon-sm",
                          variant: "ghost",
                        })}
                        aria-label="Open original file"
                      >
                        <ExternalLink />
                      </a>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label="Parse again"
                        disabled={reprocess.isPending}
                        onClick={() => reprocess.mutate(r.id)}
                      >
                        <RefreshCw />
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
              {latestPdf && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm font-medium">
                    Preview original
                  </summary>
                  <iframe
                    title="Resume preview"
                    src={`/api/v1/resumes/${latestPdf.id}/file`}
                    className="mt-2 h-[28rem] w-full rounded-lg border"
                  />
                </details>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={
          recruiter ? "Delete this candidate?" : "Delete your profile data?"
        }
        description="The profile, extracted data, resume files, applications, interviews and reports are permanently deleted."
        confirmLabel="Delete permanently"
        destructive
        onConfirm={() => del.mutate()}
        pending={del.isPending}
      />
    </div>
  );
}

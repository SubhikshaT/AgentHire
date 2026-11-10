"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  BookOpen,
  Briefcase,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  FileUp,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { ProfileView } from "@/components/candidates/profile-view";
import {
  NativeSelect,
  ScoreValue,
  SkillChip,
  StageBadge,
  Stat,
} from "@/components/common/bits";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import { CreateInterview } from "@/components/interviews/create-interview";
import { PageHeader } from "@/components/layout/page-header";
import { MatchExplanation } from "@/components/matching/match-explanation";
import { ResumeUploader } from "@/components/resumes/resume-uploader";
import { AccountCard } from "@/components/settings/settings-page";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useMe } from "@/hooks/use-auth";
import { api, ApiError, errorMessage } from "@/lib/api";
import { EDU_LEVELS, fmtDate } from "@/lib/labels";
import type {
  Application,
  Candidate,
  InterviewListItem,
  Job,
  LearningItem,
  Match,
  Page,
} from "@/types/api";

function useMyProfile() {
  return useQuery({
    queryKey: ["my-profile"],
    queryFn: async () => {
      try {
        return await api<Candidate>("/candidates/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
    refetchInterval: (q) =>
      q.state.data?.resumes.some((r) =>
        ["pending", "processing"].includes(r.parsing_status),
      )
        ? 2000
        : false,
  });
}

function useMyApps() {
  return useQuery({
    queryKey: ["my-apps"],
    queryFn: () => api<Application[]>("/applications/me"),
  });
}

export function CandidateHome() {
  const { data: me } = useMe();
  const profile = useMyProfile();
  const apps = useMyApps();
  const ivs = useQuery({
    queryKey: ["interviews"],
    queryFn: () => api<InterviewListItem[]>("/interviews"),
  });
  const parsed = profile.data?.resumes.some(
    (r) => r.parsing_status === "completed",
  );
  const todo =
    ivs.data?.filter(
      (i) => i.status === "ready" || i.status === "in_progress",
    ) ?? [];
  return (
    <>
      <PageHeader
        title={`Hello, ${me?.name.split(" ")[0] ?? ""}`}
        description="Your applications, interviews and feedback in one place."
      />
      {profile.isPending ? (
        <LoadingBlock />
      ) : !parsed ? (
        <EmptyState
          icon={FileUp}
          title="Upload your resume to get started"
          text="AgentHire reads your resume, builds your profile and lets you apply to jobs."
          action={
            <Link href="/candidate/profile" className={buttonVariants()}>
              Upload resume
            </Link>
          }
        />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat
              label="Skills on profile"
              value={profile.data?.skills.length ?? 0}
            />
            <Stat label="Applications" value={apps.data?.length ?? 0} />
            <Stat label="Interviews to do" value={todo.length} />
            <Stat
              label="Completed interviews"
              value={
                ivs.data?.filter((i) => i.status === "completed").length ?? 0
              }
            />
          </div>
          {todo.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Interviews waiting for you</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y">
                  {todo.map((i) => (
                    <li
                      key={i.id}
                      className="flex items-center justify-between gap-3 py-2.5 text-sm"
                    >
                      <span>
                        {i.job_title} ·{" "}
                        {i.interview_type === "practice"
                          ? "practice"
                          : "interview"}{" "}
                        · {i.question_count} questions
                      </span>
                      <Link
                        href={`/candidate/interviews/${i.id}`}
                        className={buttonVariants({ size: "sm" })}
                      >
                        {i.status === "in_progress" ? "Resume" : "Start"}
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          <div className="flex flex-wrap gap-2">
            <Link
              href="/candidate/jobs"
              className={buttonVariants({ variant: "outline" })}
            >
              <Search /> Browse jobs
            </Link>
            <Link
              href="/candidate/applications"
              className={buttonVariants({ variant: "outline" })}
            >
              <ClipboardList /> My applications
            </Link>
            <Link
              href="/candidate/learning"
              className={buttonVariants({ variant: "outline" })}
            >
              <BookOpen /> Learning
            </Link>
          </div>
        </div>
      )}
    </>
  );
}

export function CandidateProfilePage() {
  const profile = useMyProfile();
  const qc = useQueryClient();
  return (
    <>
      {profile.isPending ? (
        <LoadingBlock rows={4} />
      ) : profile.isError ? (
        <ErrorState error={profile.error} onRetry={profile.refetch} />
      ) : (
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>
                {profile.data?.resumes.length
                  ? "Upload a new version of your resume"
                  : "Upload your resume"}
              </CardTitle>
              <CardDescription>
                Your profile is filled from the newest resume. Fields you
                corrected yourself are kept.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResumeUploader
                single
                onDone={() =>
                  qc.invalidateQueries({ queryKey: ["my-profile"] })
                }
              />
            </CardContent>
          </Card>
          {profile.data && profile.data.resumes.length > 0 && (
            <ProfileView c={profile.data} mode="self" />
          )}
        </div>
      )}
    </>
  );
}

export function BrowseJobs() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [view, setView] = useState<Job | null>(null);
  const params = new URLSearchParams({ page: String(page), page_size: "12" });
  if (q) params.set("q", q);
  const jobs = useQuery({
    queryKey: ["open-jobs", params.toString()],
    queryFn: () => api<Page<Job>>(`/jobs?${params}`),
    placeholderData: keepPreviousData,
  });
  const apps = useMyApps();
  const applied = new Set(apps.data?.map((a) => a.job_id));
  const apply = useMutation({
    mutationFn: (id: string) =>
      api<Application>(`/jobs/${id}/apply`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Application sent");
      qc.invalidateQueries({ queryKey: ["my-apps"] });
      setView(null);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const pages = jobs.data
    ? Math.max(1, Math.ceil(jobs.data.total / jobs.data.page_size))
    : 1;
  return (
    <>
      <PageHeader
        title="Browse jobs"
        description="Open roles you can apply to with your profile."
      />
      <div className="relative mb-4 max-w-md">
        <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
        <Input
          aria-label="Search jobs"
          placeholder="Search…"
          className="h-9 pl-8"
          value={q}
          onChange={(e) => (setQ(e.target.value), setPage(1))}
        />
      </div>
      {jobs.isPending ? (
        <LoadingBlock />
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={jobs.refetch} />
      ) : jobs.data.items.length === 0 ? (
        <EmptyState icon={Briefcase} title="No open jobs right now" />
      ) : (
        <>
          <ul className="grid gap-3 md:grid-cols-2">
            {jobs.data.items.map((j) => (
              <li
                key={j.id}
                className="bg-card flex flex-col rounded-xl border p-4"
              >
                <p className="font-medium">{j.title}</p>
                <p className="text-muted-foreground text-sm">
                  {[
                    j.department,
                    j.minimum_experience != null
                      ? `${j.minimum_experience}+ years`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                <div className="my-3 flex flex-wrap gap-1.5">
                  {j.required_skills.slice(0, 6).map((s) => (
                    <SkillChip key={s} name={s} />
                  ))}
                </div>
                <div className="mt-auto flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setView(j)}
                  >
                    Details
                  </Button>
                  {applied.has(j.id) ? (
                    <span className="text-success inline-flex items-center gap-1 text-sm">
                      <CheckCircle2 className="size-4" /> Applied
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => apply.mutate(j.id)}
                      disabled={apply.isPending}
                    >
                      Apply
                    </Button>
                  )}
                </div>
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
      <Dialog open={!!view} onOpenChange={(o) => !o && setView(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{view?.title}</DialogTitle>
          </DialogHeader>
          {view && (
            <div className="space-y-3 text-sm">
              <div>
                <p className="mb-1 font-medium">Required skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {view.required_skills.map((s) => (
                    <SkillChip key={s} name={s} />
                  ))}
                </div>
              </div>
              {view.preferred_skills.length > 0 && (
                <div>
                  <p className="mb-1 font-medium">Nice to have</p>
                  <div className="flex flex-wrap gap-1.5">
                    {view.preferred_skills.map((s) => (
                      <SkillChip key={s} name={s} tone="muted" />
                    ))}
                  </div>
                </div>
              )}
              {view.education_requirements[0] && (
                <p>
                  <span className="font-medium">Education:</span>{" "}
                  {
                    EDU_LEVELS.find(
                      (l) => l.value === view.education_requirements[0].level,
                    )?.label
                  }
                </p>
              )}
              <p className="text-muted-foreground whitespace-pre-wrap">
                {view.description}
              </p>
              {!applied.has(view.id) && (
                <Button
                  onClick={() => apply.mutate(view.id)}
                  disabled={apply.isPending}
                >
                  Apply to this job
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export function MyApplications() {
  const apps = useMyApps();
  const [open, setOpen] = useState<Application | null>(null);
  const match = useQuery({
    queryKey: ["match", open?.match_id],
    queryFn: () => api<Match>(`/matching/${open!.match_id}`),
    enabled: !!open?.match_id,
  });
  return (
    <>
      <PageHeader
        title="My applications"
        description="Your stage in each process. Match details show which skills the recruiter's job asks for."
      />
      {apps.isPending ? (
        <LoadingBlock />
      ) : apps.isError ? (
        <ErrorState error={apps.error} onRetry={apps.refetch} />
      ) : apps.data.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No applications yet"
          action={
            <Link href="/candidate/jobs" className={buttonVariants()}>
              Browse jobs
            </Link>
          }
        />
      ) : (
        <ul className="space-y-3">
          {apps.data.map((a) => (
            <li
              key={a.id}
              className="bg-card flex flex-wrap items-center gap-3 rounded-xl border p-4"
            >
              <div className="min-w-0 flex-1 basis-full sm:basis-0">
                <p className="font-medium">{a.job_title}</p>
                <p className="text-muted-foreground text-xs">
                  {a.source === "candidate_applied"
                    ? "Applied"
                    : "Added by recruiter"}{" "}
                  {fmtDate(a.created_at)}
                </p>
              </div>
              <StageBadge stage={a.stage} />
              {a.match_id ? (
                <Button size="sm" variant="outline" onClick={() => setOpen(a)}>
                  Skill gaps
                </Button>
              ) : (
                <span className="text-muted-foreground text-xs">
                  Not scored yet
                </span>
              )}
              <CreateInterview
                applicationId={a.id}
                type="practice"
                label="Practice interview"
                detailHref={(id) => `/candidate/interviews/${id}`}
              />
            </li>
          ))}
        </ul>
      )}
      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Your match for {open?.job_title}</DialogTitle>
          </DialogHeader>
          {match.data ? (
            <>
              <MatchExplanation
                ex={match.data.explanation}
                overall={match.data.overall_score}
              />
              <Link
                href={`/candidate/learning?application=${open?.id}`}
                className={buttonVariants({ variant: "secondary" })}
              >
                <BookOpen /> Learning resources for these gaps
              </Link>
            </>
          ) : (
            <LoadingBlock rows={3} />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export function Learning({
  initialApplication,
}: {
  initialApplication?: string;
}) {
  const qc = useQueryClient();
  const apps = useMyApps();
  const scored = apps.data?.filter((a) => a.match_id) ?? [];
  const [appId, setAppId] = useState(initialApplication ?? "");
  const current = appId || scored[0]?.id || "";
  const recs = useQuery({
    queryKey: ["learning", current],
    queryFn: () =>
      api<{ items: LearningItem[]; matched: boolean; job_title: string }>(
        `/learning/recommendations?application_id=${current}`,
      ),
    enabled: !!current,
  });
  const toggle = useMutation({
    mutationFn: ({ key, completed }: { key: string; completed: boolean }) =>
      api("/learning/progress", {
        method: "POST",
        body: { resource_key: key, completed },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["learning"] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <>
      <PageHeader
        title="Learning"
        description="Resources for the skills your target jobs ask for. All links come from a curated list of official docs and free courses."
      />
      {apps.isPending ? (
        <LoadingBlock />
      ) : scored.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No skill gaps yet"
          text="Recommendations appear after a recruiter has scored one of your applications."
        />
      ) : (
        <>
          <NativeSelect
            aria-label="Application"
            value={current}
            onChange={(e) => setAppId(e.target.value)}
            className="mb-4"
          >
            {scored.map((a) => (
              <option key={a.id} value={a.id}>
                {a.job_title}
              </option>
            ))}
          </NativeSelect>
          {recs.isPending ? (
            <LoadingBlock />
          ) : recs.isError ? (
            <ErrorState error={recs.error} />
          ) : recs.data.items.length === 0 ? (
            <EmptyState
              title="No gaps for this job"
              text="Your profile covers the listed requirements."
            />
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {recs.data.items.map((l) => (
                <li
                  key={l.key}
                  className="bg-card flex gap-3 rounded-xl border p-4"
                >
                  <Checkbox
                    className="mt-1"
                    aria-label={`Mark ${l.title} as completed`}
                    checked={!!l.completed}
                    onCheckedChange={(v) =>
                      toggle.mutate({ key: l.key, completed: !!v })
                    }
                  />
                  <div className="min-w-0">
                    <a
                      href={l.url}
                      target="_blank"
                      rel="noreferrer"
                      className={`inline-flex items-center gap-1 font-medium hover:underline ${l.completed ? "text-muted-foreground line-through" : "text-primary"}`}
                    >
                      {l.title} <ExternalLink className="size-3.5" />
                    </a>
                    <p className="text-muted-foreground text-sm">
                      {l.objective}
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      <SkillChip
                        name={l.skill}
                        tone={
                          l.priority === "required"
                            ? "bad"
                            : l.priority === "related"
                              ? "warn"
                              : "muted"
                        }
                      />
                      <SkillChip name={l.difficulty} tone="muted" />
                    </div>
                    {l.note && (
                      <p className="text-muted-foreground mt-1 text-xs">
                        {l.note}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}

export function MyFeedback() {
  const ivs = useQuery({
    queryKey: ["interviews", "completed"],
    queryFn: () => api<InterviewListItem[]>("/interviews?status=completed"),
  });
  return (
    <>
      <PageHeader
        title="My feedback"
        description="Evaluations of your completed interviews. AI feedback is decision support; recruiters make the final call."
      />
      {ivs.isPending ? (
        <LoadingBlock />
      ) : ivs.isError ? (
        <ErrorState error={ivs.error} />
      ) : ivs.data.length === 0 ? (
        <EmptyState
          title="No completed interviews yet"
          action={
            <Link
              href="/candidate/interviews"
              className={buttonVariants({ variant: "outline" })}
            >
              My interviews
            </Link>
          }
        />
      ) : (
        <ul className="bg-card divide-y rounded-xl border">
          {ivs.data.map((i) => (
            <li key={i.id}>
              <Link
                href={`/candidate/interviews/${i.id}`}
                className="hover:bg-muted/50 flex flex-wrap items-center gap-3 px-4 py-3"
              >
                <div className="min-w-0 flex-1 basis-full sm:basis-0">
                  <p className="font-medium">{i.job_title}</p>
                  <p className="text-muted-foreground text-xs">
                    {i.interview_type === "practice" ? "Practice" : "Interview"}{" "}
                    · completed {fmtDate(i.completed_at)}
                    {i.pending_evaluation
                      ? ` · ${i.pending_evaluation} answer(s) awaiting evaluation`
                      : ""}
                  </p>
                </div>
                <ScoreValue score={i.total_score} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function CandidateSettings() {
  return (
    <>
      <PageHeader title="Settings" description="Your account and data." />
      <div className="grid gap-5 lg:grid-cols-2">
        <AccountCard />
        <Card>
          <CardHeader>
            <CardTitle>Your data</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground space-y-2 text-sm">
            <p>
              Your name, email and phone are never used to score you. Only
              skills, experience, education, certifications and your written
              answers are evaluated.
            </p>
            <p>
              To delete your profile, resume files, applications and interviews,
              open{" "}
              <Link
                href="/candidate/profile"
                className="text-primary font-medium hover:underline"
              >
                My Profile
              </Link>{" "}
              and choose “Delete my data”.
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

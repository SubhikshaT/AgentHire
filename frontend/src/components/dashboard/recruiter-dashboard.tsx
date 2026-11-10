"use client";

import { useQuery } from "@tanstack/react-query";
import { Briefcase, Plus, Upload } from "lucide-react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Stat } from "@/components/common/bits";

import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMe } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { ACTION_LABELS, fmtDate, fmtScore, stageLabel } from "@/lib/labels";

type Overview = {
  total_jobs: number;
  active_jobs: number;
  total_candidates: number;
  resumes_processed: number;
  resumes_failed: number;
  resumes_pending: number;
  interviews_completed: number;
  interviews_open: number;
  average_match_score: number | null;
  average_interview_score: number | null;
  recent_activity: {
    action: string;
    created_at: string;
    meta: Record<string, unknown>;
  }[];
};

const tick = { fontSize: 11, fill: "#6b7280" };
// Concrete colors: SVG fills in charts do not reliably resolve CSS variables.
const C = {
  indigo: "#4f46e5",
  violet: "#8b5cf6",
  sky: "#0ea5e9",
  green: "#10b981",
  amber: "#f59e0b",
};

export function RecruiterDashboard() {
  const { data: me } = useMe();
  const o = useQuery({
    queryKey: ["an-overview"],
    queryFn: () => api<Overview>("/analytics/overview"),
  });
  const pipe = useQuery({
    queryKey: ["an-pipeline"],
    queryFn: () =>
      api<{ stage: string; count: number }[]>("/analytics/pipeline"),
  });
  const jobs = useQuery({
    queryKey: ["an-jobs"],
    queryFn: () =>
      api<
        {
          job_id: string;
          title: string;
          applicants: number;
          average_score: number | null;
        }[]
      >("/analytics/jobs"),
  });
  const skills = useQuery({
    queryKey: ["an-skills"],
    queryFn: () =>
      api<{ skill: string; demand: number; candidates_with_skill: number }[]>(
        "/analytics/skills",
      ),
  });
  const trend = useQuery({
    queryKey: ["an-trend"],
    queryFn: () =>
      api<
        {
          week_start: string;
          completed: number;
          average_score: number | null;
        }[]
      >("/analytics/interviews"),
  });

  if (o.isPending) return <LoadingBlock rows={4} />;
  if (o.isError) return <ErrorState error={o.error} onRetry={o.refetch} />;
  const d = o.data;

  return (
    <>
      <PageHeader
        title={`Hello, ${me?.name.split(" ")[0] ?? ""}`}
        description="Every number here is calculated from your own jobs and candidates."
        actions={
          <div className="flex gap-2">
            <Link
              href="/resumes"
              className={buttonVariants({ variant: "outline" })}
            >
              <Upload /> Upload resumes
            </Link>
            <Link href="/jobs/new" className={buttonVariants()}>
              <Plus /> New job
            </Link>
          </div>
        }
      />
      
      {d.total_jobs === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="Start by creating a job"
          text="Add a job, upload resumes for it, then run matching. Your dashboard fills in as you go."
          action={
            <Link href="/jobs/new" className={buttonVariants()}>
              <Plus /> New job
            </Link>
          }
        />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat
              label="Active jobs"
              value={d.active_jobs}
              hint={`${d.total_jobs} in total`}
            />
            <Stat
              label="Candidates"
              value={d.total_candidates}
              hint={`${d.resumes_processed} resumes parsed${d.resumes_failed ? `, ${d.resumes_failed} failed` : ""}`}
            />
            <Stat
              label="Interviews completed"
              value={d.interviews_completed}
              hint={`${d.interviews_open} open`}
            />
            <Stat
              label="Average match score"
              value={fmtScore(d.average_match_score)}
              hint={
                d.average_interview_score != null
                  ? `Avg interview ${fmtScore(d.average_interview_score)}`
                  : "across scored applicants"
              }
            />
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Candidate pipeline</CardTitle>
                <CardDescription>Applications in each stage</CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                {pipe.data && (
                  <ResponsiveContainer>
                    <BarChart
                      data={pipe.data.map((p) => ({
                        ...p,
                        label: stageLabel(p.stage),
                      }))}
                      layout="vertical"
                      margin={{ left: 24 }}
                    >
                      <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                      <XAxis type="number" allowDecimals={false} tick={tick} />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={130}
                        tick={tick}
                      />
                      <Tooltip />
                      <Bar
                        dataKey="count"
                        name="Applications"
                        fill={C.indigo}
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Applicants per job</CardTitle>
                <CardDescription>With average match score</CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                {jobs.data && (
                  <ResponsiveContainer>
                    <BarChart
                      data={jobs.data.slice(0, 8).map((j) => ({
                        ...j,
                        short:
                          j.title.length > 18
                            ? `${j.title.slice(0, 17)}…`
                            : j.title,
                      }))}
                    >
                      <CartesianGrid vertical={false} strokeDasharray="3 3" />
                      <XAxis
                        dataKey="short"
                        tick={tick}
                        interval={0}
                        angle={-20}
                        textAnchor="end"
                        height={56}
                      />
                      <YAxis yAxisId="a" allowDecimals={false} tick={tick} />
                      <YAxis
                        yAxisId="s"
                        orientation="right"
                        domain={[0, 100]}
                        tick={tick}
                      />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar
                        yAxisId="a"
                        dataKey="applicants"
                        name="Applicants"
                        fill={C.indigo}
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        yAxisId="s"
                        dataKey="average_score"
                        name="Avg score"
                        fill={C.violet}
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Skill demand vs. supply</CardTitle>
                <CardDescription>
                  Jobs asking for a skill vs. applicants who have it
                </CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                {skills.data && skills.data.length > 0 ? (
                  <ResponsiveContainer>
                    <BarChart data={skills.data.slice(0, 10)}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" />
                      <XAxis
                        dataKey="skill"
                        tick={tick}
                        interval={0}
                        angle={-30}
                        textAnchor="end"
                        height={64}
                      />
                      <YAxis allowDecimals={false} tick={tick} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar
                        dataKey="demand"
                        name="Jobs requiring (preferred = 0.5)"
                        fill={C.sky}
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="candidates_with_skill"
                        name="Candidates with skill"
                        fill={C.green}
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    Add required skills to your jobs to see demand.
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Interview trend</CardTitle>
                <CardDescription>
                  Completed per week and average score (last 8 weeks)
                </CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                {trend.data && trend.data.length > 0 ? (
                  <ResponsiveContainer>
                    <LineChart data={trend.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="week_start" tick={tick} />
                      <YAxis yAxisId="c" allowDecimals={false} tick={tick} />
                      <YAxis
                        yAxisId="s"
                        orientation="right"
                        domain={[0, 100]}
                        tick={tick}
                      />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Line
                        yAxisId="c"
                        dataKey="completed"
                        name="Completed"
                        stroke={C.indigo}
                        strokeWidth={2}
                      />
                      <Line
                        yAxisId="s"
                        dataKey="average_score"
                        name="Avg score"
                        stroke={C.violet}
                        strokeWidth={2}
                        connectNulls
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    No completed interviews in the last 8 weeks.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Recent activity</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y text-sm">
                {d.recent_activity.map((a, i) => (
                  <li key={i} className="flex justify-between gap-4 py-2">
                    <span>{ACTION_LABELS[a.action] ?? a.action}</span>
                    <span className="text-muted-foreground text-xs">
                      {fmtDate(a.created_at, true)}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}

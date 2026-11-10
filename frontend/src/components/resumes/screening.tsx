"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { NativeSelect } from "@/components/common/bits";
import { EmptyState, LoadingBlock } from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { ResumeUploader } from "@/components/resumes/resume-uploader";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Job, Page } from "@/types/api";

export function Screening() {
  const jobs = useQuery({
    queryKey: ["jobs-all"],
    queryFn: () => api<Page<Job>>("/jobs?page_size=100"),
  });
  const [jobId, setJobId] = useState("");
  const selected = jobs.data?.items.find((j) => j.id === jobId);

  return (
    <>
      <PageHeader
        title="Resume screening"
        description="Upload many resumes at once. Each file is checked, parsed in the background and linked to the job."
      />
      {jobs.isPending ? (
        <LoadingBlock rows={2} />
      ) : !jobs.data?.items.length ? (
        <EmptyState
          title="Create a job first"
          text="Resumes are always uploaded for a specific job."
          action={
            <Link href="/jobs/new" className={buttonVariants()}>
              New job
            </Link>
          }
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1fr_18rem]">
          <Card>
            <CardHeader>
              <CardTitle>1. Choose the job</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <NativeSelect
                aria-label="Job"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="w-full"
              >
                <option value="">Select a job…</option>
                {jobs.data.items.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title} ({j.status})
                  </option>
                ))}
              </NativeSelect>
              {selected ? (
                <div>
                  <p className="mb-3 text-sm font-medium">
                    2. Upload resumes for {selected.title}
                  </p>
                  <ResumeUploader key={selected.id} jobId={selected.id} />
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">
                  Pick a job to enable the upload area.
                </p>
              )}
            </CardContent>
          </Card>
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="text-base">What happens</CardTitle>
              <CardDescription>Same steps for every file</CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="text-muted-foreground list-decimal space-y-1.5 pl-4 text-sm">
                <li>Type and size are checked (PDF/DOCX, ≤ 10 MB).</li>
                <li>Exact duplicates are detected.</li>
                <li>Text is extracted and split into sections.</li>
                <li>
                  Skills, education, experience, projects and certifications are
                  extracted with evidence.
                </li>
                <li>Sections are embedded for semantic search.</li>
                <li>You review and correct the profile.</li>
              </ol>
              {selected && (
                <Link
                  href={`/jobs/${selected.id}`}
                  className={buttonVariants({
                    variant: "outline",
                    className: "mt-4 w-full",
                  })}
                >
                  Go to ranking
                </Link>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}

"use client";

import { useQueries, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ResumeStatus, UploadResult } from "@/types/api";

const MAX_MB = 10;

/** Drag-and-drop resume upload. Recruiters pass jobId (bulk); candidates upload one file for themselves. */
export function ResumeUploader({
  jobId,
  single = false,
  onDone,
}: {
  jobId?: string;
  single?: boolean;
  onDone?: () => void;
}) {
  const qc = useQueryClient();
  const [results, setResults] = useState<UploadResult[]>([]);
  const [uploading, setUploading] = useState(false);

  const upload = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    try {
      let res: UploadResult[];
      if (jobId && !single) {
        const fd = new FormData();
        files.forEach((f) => fd.append("files", f));
        res = await api<UploadResult[]>(`/jobs/${jobId}/resumes/bulk-upload`, {
          method: "POST",
          body: fd,
        });
      } else {
        const fd = new FormData();
        fd.append("file", files[0]);
        if (jobId) fd.append("job_id", jobId);
        try {
          res = [
            await api<UploadResult>("/resumes/upload", {
              method: "POST",
              body: fd,
            }),
          ];
        } catch (e) {
          res = [
            {
              filename: files[0].name,
              ok: false,
              resume_id: null,
              candidate_id: null,
              application_id: null,
              error_code: "error",
              error: errorMessage(e),
            },
          ];
        }
      }
      setResults((prev) => [...res, ...prev]);
      const ok = res.filter((r) => r.ok).length;
      if (ok)
        toast.success(
          `${ok} file${ok > 1 ? "s" : ""} uploaded. Parsing runs in the background.`,
        );
      if (res.length - ok)
        toast.error(
          `${res.length - ok} file${res.length - ok > 1 ? "s were" : " was"} not accepted.`,
        );
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop: upload,
      multiple: !single,
      maxSize: MAX_MB * 1024 * 1024,
      accept: {
        "application/pdf": [".pdf"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
          [".docx"],
      },
      disabled: uploading,
    });

  const tracked = results.filter((r) => r.ok && r.resume_id);
  const statuses = useQueries({
    queries: tracked.map((r) => ({
      queryKey: ["resume-status", r.resume_id],
      queryFn: () => api<ResumeStatus>(`/resumes/${r.resume_id}/status`),
      refetchInterval: (q: { state: { data?: ResumeStatus } }) =>
        q.state.data &&
        ["completed", "failed"].includes(q.state.data.parsing_status)
          ? false
          : 1500,
    })),
  });
  const allDone =
    statuses.length > 0 &&
    statuses.every(
      (s) => s.data && ["completed", "failed"].includes(s.data.parsing_status),
    );

  // Refresh profile / candidate lists as soon as parsing finishes.
  useEffect(() => {
    if (allDone) {
      qc.invalidateQueries({ queryKey: ["my-profile"] });
      qc.invalidateQueries({ queryKey: ["candidates"] });
      qc.invalidateQueries({ queryKey: ["job-apps"] });
    }
  }, [allDone, qc]);

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "focus-visible:ring-ring flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors outline-none focus-visible:ring-2",
          isDragActive ? "border-ring bg-secondary/60" : "hover:bg-muted/50",
          uploading && "opacity-60",
        )}
      >
        <input {...getInputProps()} aria-label="Resume files" />
        {uploading ? (
          <Loader2 className="text-muted-foreground size-7 animate-spin" />
        ) : (
          <FileUp className="text-muted-foreground size-7" />
        )}
        <p className="font-medium">
          {isDragActive
            ? "Drop the files here"
            : single
              ? "Drop your resume here, or click to choose"
              : "Drop resumes here, or click to choose"}
        </p>
        <p className="text-muted-foreground text-xs">
          PDF or DOCX, up to {MAX_MB} MB each
          {single ? "" : ", up to 50 files at once"}.
        </p>
      </div>
      {fileRejections.length > 0 && (
        <ul className="text-destructive space-y-1 text-sm" role="alert">
          {fileRejections.map((r) => (
            <li key={r.file.name}>
              {r.file.name}:{" "}
              {r.errors[0]?.code === "file-too-large"
                ? `larger than ${MAX_MB} MB`
                : "only PDF and DOCX files are allowed"}
            </li>
          ))}
        </ul>
      )}
      {results.length > 0 && (
        <div className="rounded-xl border">
          <div className="flex items-center justify-between border-b px-4 py-2.5">
            <p className="text-sm font-medium">Upload results</p>
            {allDone && onDone && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => (qc.invalidateQueries(), onDone())}
              >
                Done
              </Button>
            )}
          </div>
          <ul className="divide-y text-sm">
            {results.map((r, i) => {
              const s = r.ok ? statuses[tracked.indexOf(r)]?.data : undefined;
              const status = !r.ok
                ? "rejected"
                : (s?.parsing_status ?? "pending");
              const cid = s?.candidate_id ?? r.candidate_id;
              return (
                <li
                  key={`${r.filename}-${i}`}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5"
                >
                  {status === "completed" ? (
                    <CheckCircle2 className="text-success size-4" />
                  ) : status === "failed" || status === "rejected" ? (
                    <XCircle className="text-destructive size-4" />
                  ) : (
                    <Loader2 className="text-muted-foreground size-4 animate-spin" />
                  )}
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {r.filename}
                  </span>
                  <span className="text-muted-foreground">
                    {status === "rejected"
                      ? r.error
                      : status === "failed"
                        ? `Parsing failed: ${s?.parsing_error}`
                        : status === "completed"
                          ? `${s?.skills_found ?? 0} skills found${r.error_code === "duplicate_linked" ? " · existing candidate linked" : ""}`
                          : status === "processing"
                            ? "Parsing…"
                            : "Queued…"}
                  </span>
                  {status === "completed" && cid && !single && (
                    <Link
                      href={`/candidates/${cid}`}
                      className="text-primary text-sm font-medium underline-offset-4 hover:underline"
                    >
                      Review
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

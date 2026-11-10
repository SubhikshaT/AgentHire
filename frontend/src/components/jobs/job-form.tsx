"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/auth/form-field";
import { NativeSelect, TagInput } from "@/components/common/bits";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, errorMessage } from "@/lib/api";
import { EDU_LEVELS } from "@/lib/labels";
import type { Job, JobAnalysis } from "@/types/api";

type FormState = {
  title: string;
  department: string;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  soft_skills: string[];
  certifications: string[];
  responsibilities: string[];
  minimum_experience: string;
  edu_level: string;
  edu_fields: string[];
};

function fromJob(j?: Job): FormState {
  return {
    title: j?.title ?? "",
    department: j?.department ?? "",
    description: j?.description ?? "",
    required_skills: j?.required_skills ?? [],
    preferred_skills: j?.preferred_skills ?? [],
    soft_skills: j?.soft_skills ?? [],
    certifications: j?.certifications ?? [],
    responsibilities: j?.responsibilities ?? [],
    minimum_experience:
      j?.minimum_experience != null ? String(j.minimum_experience) : "",
    edu_level: j?.education_requirements?.[0]?.level ?? "",
    edu_fields: j?.education_requirements?.[0]?.fields ?? [],
  };
}

export function JobForm({ job }: { job?: Job }) {
  const router = useRouter();
  const [f, setF] = useState<FormState>(fromJob(job));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setF((s) => ({ ...s, [k]: v }));

  const analyze = useMutation({
    mutationFn: () =>
      api<JobAnalysis>("/jobs/analyze-text", {
        method: "POST",
        body: { description: f.description },
      }),
    onSuccess: (a) => {
      setF((s) => ({
        ...s,
        title: s.title || a.title || "",
        department: s.department || a.department || "",
        required_skills: a.required_skills.length
          ? a.required_skills
          : s.required_skills,
        preferred_skills: a.preferred_skills.length
          ? a.preferred_skills
          : s.preferred_skills,
        soft_skills: a.soft_skills.length ? a.soft_skills : s.soft_skills,
        certifications: a.certifications.length
          ? a.certifications
          : s.certifications,
        responsibilities: a.responsibilities.length
          ? a.responsibilities
          : s.responsibilities,
        minimum_experience:
          a.minimum_experience != null
            ? String(a.minimum_experience)
            : s.minimum_experience,
        edu_level: a.education_requirements[0]?.level ?? s.edu_level,
        edu_fields: a.education_requirements[0]?.fields ?? s.edu_fields,
      }));
      toast.success(
        `Found ${a.required_skills.length} required and ${a.preferred_skills.length} preferred skills. Please review them.`,
      );
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const save = useMutation({
    mutationFn: () => {
      const body = {
        title: f.title.trim(),
        department: f.department.trim() || null,
        description: f.description,
        required_skills: f.required_skills,
        preferred_skills: f.preferred_skills,
        soft_skills: f.soft_skills,
        certifications: f.certifications,
        responsibilities: f.responsibilities,
        minimum_experience:
          f.minimum_experience === "" ? null : Number(f.minimum_experience),
        education_requirements: f.edu_level
          ? [{ level: f.edu_level, fields: f.edu_fields }]
          : [],
      };
      return job
        ? api<Job>(`/jobs/${job.id}`, { method: "PUT", body })
        : api<Job>("/jobs", { method: "POST", body });
    },
    onSuccess: (saved) => {
      toast.success(job ? "Job updated" : "Job created as a draft");
      router.push(`/jobs/${saved.id}`);
    },
    onError: (e) => {
      if (e instanceof ApiError && e.details) {
        setErrors(
          Object.fromEntries(
            e.details.map((d) => [d.field.split(".")[0], d.message]),
          ),
        );
      }
      toast.error(errorMessage(e));
    },
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (f.title.trim().length < 2) errs.title = "Enter a job title";
    const exp =
      f.minimum_experience === "" ? null : Number(f.minimum_experience);
    if (exp !== null && (Number.isNaN(exp) || exp < 0 || exp > 40))
      errs.minimum_experience = "Use a number from 0 to 40";
    setErrors(errs);
    if (Object.keys(errs).length === 0) save.mutate();
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      className="grid gap-5 lg:grid-cols-[1.1fr_1fr]"
    >
      <Card>
        <CardHeader>
          <CardTitle>Job description</CardTitle>
          <CardDescription>
            Paste the full description, then let AgentHire pull out the
            requirements.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField id="title" label="Job title" error={errors.title}>
            <Input
              id="title"
              value={f.title}
              onChange={(e) => set("title", e.target.value)}
              aria-invalid={!!errors.title}
            />
          </FormField>
          <FormField id="department" label="Department (optional)">
            <Input
              id="department"
              value={f.department}
              onChange={(e) => set("department", e.target.value)}
            />
          </FormField>
          <FormField id="description" label="Full description">
            <Textarea
              id="description"
              rows={14}
              value={f.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder={
                "Backend Engineer\nRequirements:\n- 2+ years with Python, FastAPI, PostgreSQL\nNice to have:\n- Docker"
              }
            />
          </FormField>
          <Button
            type="button"
            variant="secondary"
            onClick={() => analyze.mutate()}
            disabled={analyze.isPending || f.description.trim().length < 20}
          >
            {analyze.isPending ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Sparkles />
            )}
            Extract requirements from description
          </Button>
          <p className="text-muted-foreground text-xs">
            Extraction uses the skill taxonomy and simple rules. Always review
            the result before publishing.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Structured requirements</CardTitle>
          <CardDescription>
            These fields drive matching. Press Enter or comma to add an item.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            id="req"
            label="Required skills"
            error={errors.required_skills}
          >
            <TagInput
              id="req"
              value={f.required_skills}
              onChange={(v) => set("required_skills", v)}
              placeholder="e.g. Python"
            />
          </FormField>
          <FormField id="pref" label="Preferred skills">
            <TagInput
              id="pref"
              value={f.preferred_skills}
              onChange={(v) => set("preferred_skills", v)}
              placeholder="e.g. Docker"
            />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="exp"
              label="Minimum experience (years)"
              error={errors.minimum_experience}
            >
              <Input
                id="exp"
                inputMode="decimal"
                value={f.minimum_experience}
                onChange={(e) => set("minimum_experience", e.target.value)}
                placeholder="e.g. 2"
              />
            </FormField>
            <FormField id="edu" label="Education level">
              <NativeSelect
                id="edu"
                value={f.edu_level}
                onChange={(e) => set("edu_level", e.target.value)}
                className="w-full"
              >
                <option value="">No requirement</option>
                {EDU_LEVELS.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </NativeSelect>
            </FormField>
          </div>
          {f.edu_level && (
            <FormField id="fields" label="Fields of study">
              <TagInput
                id="fields"
                value={f.edu_fields}
                onChange={(v) => set("edu_fields", v)}
                placeholder="e.g. computer science"
              />
            </FormField>
          )}
          <FormField id="certs" label="Certifications">
            <TagInput
              id="certs"
              value={f.certifications}
              onChange={(v) => set("certifications", v)}
            />
          </FormField>
          <FormField id="soft" label="Soft skills (shown, not scored)">
            <TagInput
              id="soft"
              value={f.soft_skills}
              onChange={(v) => set("soft_skills", v)}
            />
          </FormField>
          <FormField id="resp" label="Responsibilities">
            <TagInput
              id="resp"
              value={f.responsibilities}
              onChange={(v) => set("responsibilities", v)}
            />
          </FormField>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending && <Loader2 className="animate-spin" />}
              {job ? "Save changes" : "Create job"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import type { Candidate, CandidateSkill } from "@/types/api";

export function VerifiedTag({ status }: { status?: string }) {
  if (status === "manually_verified")
    return (
      <span className="bg-success/15 text-success rounded px-1.5 text-[10px] font-medium uppercase">
        verified
      </span>
    );
  return (
    <span className="bg-muted text-muted-foreground rounded px-1.5 text-[10px] font-medium uppercase">
      auto-extracted
    </span>
  );
}

function useSave(candidateId: string, onDone: () => void) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<Candidate>(`/candidates/${candidateId}`, { method: "PUT", body }),
    onSuccess: (c) => {
      qc.setQueryData(["candidate", candidateId], c);
      qc.invalidateQueries({ queryKey: ["candidate"] });
      qc.invalidateQueries({ queryKey: ["my-profile"] });
      toast.success("Saved and marked as verified");
      onDone();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function BasicsEditor({
  c,
  lockEmail,
}: {
  c: Candidate;
  lockEmail: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [v, setV] = useState({
    full_name: c.full_name ?? "",
    email: c.email ?? "",
    phone: c.phone ?? "",
    professional_summary: c.professional_summary ?? "",
    total_experience_years: c.total_experience_years?.toString() ?? "",
  });
  const save = useSave(c.id, () => setOpen(false));
  const submit = () => {
    const body: Record<string, unknown> = {};
    if (v.full_name !== (c.full_name ?? ""))
      body.full_name = v.full_name || null;
    if (!lockEmail && v.email !== (c.email ?? "")) body.email = v.email || null;
    if (v.phone !== (c.phone ?? "")) body.phone = v.phone || null;
    if (v.professional_summary !== (c.professional_summary ?? ""))
      body.professional_summary = v.professional_summary || null;
    const yrs =
      v.total_experience_years === "" ? null : Number(v.total_experience_years);
    if (yrs !== c.total_experience_years) {
      if (yrs !== null && (Number.isNaN(yrs) || yrs < 0 || yrs > 60))
        return toast.error("Experience must be 0–60 years");
      body.total_experience_years = yrs;
    }
    if (!Object.keys(body).length) return setOpen(false);
    save.mutate(body);
  };
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Pencil /> Correct details
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Correct profile details</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <FormField id="fn" label="Full name">
              <Input
                id="fn"
                value={v.full_name}
                onChange={(e) => setV({ ...v, full_name: e.target.value })}
              />
            </FormField>
            <FormField
              id="em"
              label="Email"
              hint={
                lockEmail
                  ? "This is the candidate's login email and cannot be changed here."
                  : undefined
              }
            >
              <Input
                id="em"
                type="email"
                disabled={lockEmail}
                value={v.email}
                onChange={(e) => setV({ ...v, email: e.target.value })}
              />
            </FormField>
            <FormField id="ph" label="Phone">
              <Input
                id="ph"
                value={v.phone}
                onChange={(e) => setV({ ...v, phone: e.target.value })}
              />
            </FormField>
            <FormField
              id="yrs"
              label="Total experience (years, internships excluded)"
            >
              <Input
                id="yrs"
                inputMode="decimal"
                value={v.total_experience_years}
                onChange={(e) =>
                  setV({ ...v, total_experience_years: e.target.value })
                }
              />
            </FormField>
            <FormField id="sum" label="Summary">
              <Textarea
                id="sum"
                rows={4}
                value={v.professional_summary}
                onChange={(e) =>
                  setV({ ...v, professional_summary: e.target.value })
                }
              />
            </FormField>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={save.isPending}>
              {save.isPending && <Loader2 className="animate-spin" />} Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

type FieldDef = {
  key: string;
  label: string;
  type?: "text" | "number" | "textarea" | "list";
};
export const LIST_FIELDS: Record<
  string,
  { title: string; fields: FieldDef[]; empty: Record<string, unknown> }
> = {
  education: {
    title: "Education",
    fields: [
      { key: "degree", label: "Degree" },
      { key: "field", label: "Field of study" },
      { key: "institution", label: "Institution" },
      { key: "end_year", label: "Year completed", type: "number" },
      { key: "score", label: "Score / CGPA" },
    ],
    empty: {
      degree: "",
      field: "",
      institution: "",
      end_year: null,
      score: "",
    },
  },
  work_experience: {
    title: "Work experience",
    fields: [
      { key: "title", label: "Title" },
      { key: "company", label: "Company" },
      { key: "start", label: "Start (YYYY-MM)" },
      { key: "end", label: "End (YYYY-MM or present)" },
      { key: "description", label: "Description", type: "textarea" },
    ],
    empty: { title: "", company: "", start: "", end: "", description: "" },
  },
  projects: {
    title: "Projects",
    fields: [
      { key: "name", label: "Name" },
      { key: "description", label: "Description", type: "textarea" },
      { key: "skills", label: "Skills used (comma separated)", type: "list" },
    ],
    empty: { name: "", description: "", skills: [] },
  },
  certifications: {
    title: "Certifications",
    fields: [
      { key: "name", label: "Name" },
      { key: "issuer", label: "Issuer" },
      { key: "year", label: "Year", type: "number" },
    ],
    empty: { name: "", issuer: "", year: null },
  },
};

export function ListEditor({
  c,
  field,
}: {
  c: Candidate;
  field: keyof typeof LIST_FIELDS;
}) {
  const cfg = LIST_FIELDS[field];
  const [open, setOpen] = useState(false);
  const initial = (
    (c as unknown as Record<string, Record<string, unknown>[]>)[field] ?? []
  ).map((x) => ({ ...x }));
  const [rows, setRows] = useState<Record<string, unknown>[]>(initial);
  const save = useSave(c.id, () => setOpen(false));
  const update = (i: number, k: string, val: unknown) =>
    setRows((r) => r.map((x, j) => (j === i ? { ...x, [k]: val } : x)));
  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => (setRows(initial), setOpen(true))}
        aria-label={`Edit ${cfg.title}`}
      >
        <Pencil /> Edit
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit {cfg.title.toLowerCase()}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {rows.map((row, i) => (
              <fieldset key={i} className="rounded-lg border p-3">
                <legend className="sr-only">
                  {cfg.title} {i + 1}
                </legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {cfg.fields.map((fd) => {
                    const id = `${field}-${i}-${fd.key}`;
                    const val = row[fd.key];
                    return (
                      <div
                        key={fd.key}
                        className={
                          fd.type === "textarea" ? "sm:col-span-2" : ""
                        }
                      >
                        <label htmlFor={id} className="text-xs font-medium">
                          {fd.label}
                        </label>
                        {fd.type === "textarea" ? (
                          <Textarea
                            id={id}
                            rows={3}
                            value={(val as string) ?? ""}
                            onChange={(e) => update(i, fd.key, e.target.value)}
                          />
                        ) : (
                          <Input
                            id={id}
                            inputMode={
                              fd.type === "number" ? "numeric" : undefined
                            }
                            value={
                              fd.type === "list"
                                ? ((val as string[]) ?? []).join(", ")
                                : (
                                    (val as string | number | null) ?? ""
                                  ).toString()
                            }
                            onChange={(e) =>
                              update(
                                i,
                                fd.key,
                                fd.type === "list"
                                  ? e.target.value
                                      .split(",")
                                      .map((s) => s.trim())
                                      .filter(Boolean)
                                  : fd.type === "number"
                                    ? e.target.value === ""
                                      ? null
                                      : Number(
                                          e.target.value.replace(/\D/g, ""),
                                        )
                                    : e.target.value,
                              )
                            }
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive mt-2"
                  onClick={() => setRows((r) => r.filter((_, j) => j !== i))}
                >
                  <Trash2 /> Remove
                </Button>
              </fieldset>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRows((r) => [...r, { ...cfg.empty }])}
            >
              <Plus /> Add {cfg.title.toLowerCase().replace(/s$/, "")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => save.mutate({ [field]: rows })}
              disabled={save.isPending}
            >
              {save.isPending && <Loader2 className="animate-spin" />} Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function SkillsEditor({ c }: { c: Candidate }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<
    { name: string; evidence_text: string | null }[]
  >([]);
  const [draft, setDraft] = useState("");
  const save = useMutation({
    mutationFn: () =>
      api<CandidateSkill[]>(`/candidates/${c.id}/skills`, {
        method: "PUT",
        body: { skills: rows },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["candidate", c.id] });
      qc.invalidateQueries({ queryKey: ["my-profile"] });
      toast.success("Skills saved");
      setOpen(false);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => (
          setRows(
            c.skills.map((s) => ({
              name: s.name,
              evidence_text: s.evidence_text,
            })),
          ),
          setOpen(true)
        )}
      >
        <Pencil /> Edit skills
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit skills</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground text-sm">
            Remove wrong skills, add missing ones. Added or changed skills are
            marked as verified by a person.
          </p>
          <ul className="max-h-80 space-y-1.5 overflow-y-auto">
            {rows.map((r, i) => (
              <li
                key={r.name}
                className="flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-sm"
              >
                <span className="font-medium">{r.name}</span>
                <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs">
                  {r.evidence_text}
                </span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Remove ${r.name}`}
                  onClick={() => setRows(rows.filter((_, j) => j !== i))}
                >
                  <Trash2 />
                </Button>
              </li>
            ))}
          </ul>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              const n = draft.trim();
              if (
                n &&
                !rows.some((r) => r.name.toLowerCase() === n.toLowerCase())
              )
                setRows([
                  ...rows,
                  { name: n, evidence_text: "Added by a person" },
                ]);
              setDraft("");
            }}
          >
            <Input
              aria-label="New skill"
              placeholder="Add a skill, e.g. Kubernetes"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <Button type="submit" variant="outline">
              <Plus /> Add
            </Button>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending && <Loader2 className="animate-spin" />} Save
              skills
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

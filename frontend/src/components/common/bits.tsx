"use client";

import { FlaskConical, X } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { fmtScore, scoreTone, stageLabel, stageTone } from "@/lib/labels";
import { cn } from "@/lib/utils";

export function StageBadge({ stage }: { stage: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        stageTone(stage),
      )}
    >
      {stageLabel(stage)}
    </span>
  );
}

export function ScoreValue({
  score,
  className,
}: {
  score: number | null | undefined;
  className?: string;
}) {
  return (
    <span
      className={cn("font-semibold tabular-nums", scoreTone(score), className)}
    >
      {fmtScore(score)}
      {score !== null && score !== undefined && (
        <span className="text-muted-foreground text-xs font-normal">/100</span>
      )}
    </span>
  );
}

export function SyntheticTag() {
  return (
    <span
      title="Synthetic demo data (fictional person)"
      className="text-muted-foreground inline-flex items-center gap-1 rounded border border-dashed px-1.5 text-[10px] font-medium uppercase"
    >
      <FlaskConical className="size-3" /> synthetic
    </span>
  );
}

export function SkillChip({
  name,
  tone = "default",
  title,
}: {
  name: string;
  tone?: "default" | "good" | "warn" | "bad" | "muted";
  title?: string;
}) {
  const tones = {
    default: "bg-secondary text-secondary-foreground",
    good: "bg-success/15 text-success",
    warn: "bg-amber-100 text-amber-800",
    bad: "bg-destructive/10 text-destructive",
    muted: "bg-muted text-muted-foreground",
  };
  return (
    <span
      title={title}
      className={cn(
        "inline-flex rounded-md px-2 py-0.5 text-xs font-medium",
        tones[tone],
      )}
    >
      {name}
    </span>
  );
}

/** Editable list of short strings (skills, certifications...). Enter or comma adds. */
export function TagInput({
  id,
  value,
  onChange,
  placeholder,
}: {
  id?: string;
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const add = (raw: string) => {
    const parts = raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const next = [...value];
    for (const p of parts)
      if (!next.some((x) => x.toLowerCase() === p.toLowerCase())) next.push(p);
    onChange(next);
    setDraft("");
  };
  return (
    <div className="border-input focus-within:ring-ring/40 rounded-lg border p-1.5 focus-within:ring-2">
      <div className="flex flex-wrap gap-1.5">
        {value.map((v) => (
          <Badge key={v} variant="secondary" className="gap-1 pr-1">
            {v}
            <button
              type="button"
              onClick={() => onChange(value.filter((x) => x !== v))}
              className="focus-visible:ring-ring rounded-sm opacity-70 hover:opacity-100 focus-visible:ring-2 focus-visible:outline-none"
              aria-label={`Remove ${v}`}
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        <Input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              if (draft.trim()) add(draft);
            } else if (e.key === "Backspace" && !draft && value.length) {
              onChange(value.slice(0, -1));
            }
          }}
          onBlur={() => draft.trim() && add(draft)}
          placeholder={value.length ? "" : placeholder}
          className="h-7 min-w-32 flex-1 border-0 px-1 shadow-none focus-visible:ring-0"
        />
      </div>
    </div>
  );
}

export function NativeSelect({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "border-input bg-background focus-visible:border-ring focus-visible:ring-ring/40 h-9 rounded-lg border px-2.5 text-sm outline-none focus-visible:ring-3 disabled:opacity-50",
        className,
      )}
    >
      {children}
    </select>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="bg-card rounded-xl border p-4">
      <p className="text-muted-foreground text-xs font-medium">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">
        {value}
      </p>
      {hint && <p className="text-muted-foreground mt-0.5 text-xs">{hint}</p>}
    </div>
  );
}

export function Bar({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  return (
    <div className="bg-muted h-1.5 w-full rounded-full" role="presentation">
      <div
        className={cn("bg-chart-1 h-1.5 rounded-full", className)}
        style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
      />
    </div>
  );
}

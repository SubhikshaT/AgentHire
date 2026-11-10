"use client";

import {
  CheckCircle2,
  CircleAlert,
  CircleDashed,
  Link2,
  Quote,
} from "lucide-react";

import { Bar, SkillChip } from "@/components/common/bits";
import { COMPONENT_LABELS, fmtScore } from "@/lib/labels";
import type { Explanation, SkillMatch } from "@/types/api";

function SkillRow({ m, kind }: { m: SkillMatch; kind: "matched" | "related" }) {
  return (
    <li className="rounded-lg border p-2.5 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {kind === "matched" ? (
          <CheckCircle2 className="text-success size-4" />
        ) : (
          <Link2 className="size-4 text-amber-600" />
        )}
        <span className="font-medium">{m.skill}</span>
        {kind === "related" && (
          <span className="text-muted-foreground">
            via {m.candidate_skill} (half credit)
          </span>
        )}
        {m.evidence_section && (
          <SkillChip name={m.evidence_section} tone="muted" />
        )}
        {kind === "matched" && !m.verified && (
          <span
            className="text-muted-foreground text-xs"
            title="Extracted automatically, not yet confirmed by a person"
          >
            unverified
          </span>
        )}
      </div>
      {m.evidence_text && (
        <p className="text-muted-foreground mt-1.5 flex gap-1.5 text-xs">
          <Quote className="mt-0.5 size-3 shrink-0" />
          <span className="line-clamp-2">{m.evidence_text}</span>
        </p>
      )}
      {kind === "related" && m.note && (
        <p className="text-muted-foreground mt-1 text-xs">{m.note}</p>
      )}
    </li>
  );
}

export function ScoreBreakdown({
  ex,
  overall,
}: {
  ex: Explanation;
  overall: number;
}) {
  return (
    <div>
      <div className="space-y-2.5">
        {ex.breakdown.map((b) => (
          <div key={b.component}>
            <div className="mb-1 flex justify-between gap-2 text-sm">
              <span>{COMPONENT_LABELS[b.component] ?? b.component}</span>
              <span className="text-muted-foreground tabular-nums">
                {fmtScore(b.raw_value * 100, 0)}% × weight {b.weight} ={" "}
                <span className="text-foreground font-medium">
                  {fmtScore(b.contribution)}
                </span>
              </span>
            </div>
            <Bar value={b.raw_value} />
          </div>
        ))}
      </div>
      <p className="mt-3 flex justify-between border-t pt-2 text-sm font-medium">
        <span>Overall</span>
        <span className="tabular-nums">{fmtScore(overall)} / 100</span>
      </p>
      <p className="text-muted-foreground mt-1 text-xs">
        Semantic cosine {ex.semantic.raw_cosine.toFixed(3)} mapped with{" "}
        {ex.semantic.mapping}. {ex.semantic.note} Keyword-only baseline for
        comparison: {fmtScore(ex.keyword_baseline)}.
      </p>
    </div>
  );
}

export function MatchExplanation({
  ex,
  overall,
  compact = false,
}: {
  ex: Explanation;
  overall: number;
  compact?: boolean;
}) {
  const req = ex.required_skills;
  const pref = ex.preferred_skills;
  return (
    <div className="space-y-5">
      {!compact && <ScoreBreakdown ex={ex} overall={overall} />}

      <section>
        <h4 className="mb-2 text-sm font-semibold">Required skills</h4>
        <ul className="space-y-1.5">
          {req.matched.map((m) => (
            <SkillRow key={m.skill} m={m} kind="matched" />
          ))}
          {req.related.map((m) => (
            <SkillRow key={m.skill} m={m} kind="related" />
          ))}
          {req.missing.map((s) => (
            <li
              key={s}
              className="flex items-center gap-2 rounded-lg border border-dashed p-2.5 text-sm"
            >
              <CircleAlert className="text-destructive size-4" />
              <span className="font-medium">{s}</span>
              <span className="text-muted-foreground">no evidence found</span>
            </li>
          ))}
        </ul>
        {!!req.closest_evidence?.length && (
          <details className="text-muted-foreground mt-2 text-xs">
            <summary className="cursor-pointer">
              Closest resume text for gaps (retrieved by semantic search)
            </summary>
            <ul className="mt-2 space-y-1.5">
              {req.closest_evidence.map((c) => (
                <li key={c.skill} className="bg-muted rounded-md p-2">
                  <span className="text-foreground font-medium">{c.skill}</span>{" "}
                  · {c.section} · similarity {c.similarity.toFixed(2)}
                  <p className="mt-0.5 line-clamp-3">{c.text}</p>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      {(pref.matched.length > 0 ||
        pref.related.length > 0 ||
        pref.missing.length > 0) && (
        <section>
          <h4 className="mb-2 text-sm font-semibold">Preferred skills</h4>
          <div className="flex flex-wrap gap-1.5">
            {pref.matched.map((m) => (
              <SkillChip
                key={m.skill}
                name={m.skill}
                tone="good"
                title={m.evidence_text ?? undefined}
              />
            ))}
            {pref.related.map((m) => (
              <SkillChip
                key={m.skill}
                name={`${m.skill} ≈ ${m.candidate_skill}`}
                tone="warn"
                title={m.note}
              />
            ))}
            {pref.missing.map((s) => (
              <SkillChip key={s} name={s} tone="muted" title="Not found" />
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-3 sm:grid-cols-2">
        <div>
          <h4 className="mb-1.5 text-sm font-semibold">Strengths</h4>
          <ul className="space-y-1 text-sm">
            {ex.strengths.length ? (
              ex.strengths.map((s) => (
                <li key={s} className="flex gap-2">
                  <CheckCircle2 className="text-success mt-0.5 size-3.5 shrink-0" />
                  {s}
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">None recorded.</li>
            )}
          </ul>
        </div>
        <div>
          <h4 className="mb-1.5 text-sm font-semibold">Gaps</h4>
          <ul className="space-y-1 text-sm">
            {ex.gaps.length ? (
              ex.gaps.map((s) => (
                <li key={s} className="flex gap-2">
                  <CircleDashed className="text-destructive mt-0.5 size-3.5 shrink-0" />
                  {s}
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">
                No gaps against the listed requirements.
              </li>
            )}
          </ul>
        </div>
      </section>
      <p className="bg-muted text-muted-foreground rounded-lg px-3 py-2 text-xs">
        {ex.disclaimer}
      </p>
    </div>
  );
}

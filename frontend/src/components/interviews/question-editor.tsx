"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Loader2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect, TagInput } from "@/components/common/bits";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { CATEGORIES } from "@/lib/labels";
import type {
  Difficulty,
  Interview,
  InterviewQuestion,
  QuestionCategory,
} from "@/types/api";

type Row = {
  id?: string;
  question: string;
  category: QuestionCategory;
  difficulty: Difficulty;
  expected_concepts: string[];
  source?: string;
};

export function QuestionEditor({
  iv,
  onClose,
}: {
  iv: Interview;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [rows, setRows] = useState<Row[]>(
    iv.questions
      .filter((q) => !q.is_follow_up)
      .map((q: InterviewQuestion) => ({
        id: q.id,
        question: q.question,
        category: q.category,
        difficulty: q.difficulty,
        expected_concepts: q.expected_concepts ?? [],
        source: q.source,
      })),
  );
  const save = useMutation({
    mutationFn: () =>
      api<Interview>(`/interviews/${iv.id}/questions`, {
        method: "PUT",
        body: { questions: rows },
      }),
    onSuccess: (d) => {
      qc.setQueryData(["interview", iv.id], d);
      toast.success("Questions saved");
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const upd = (i: number, patch: Partial<Row>) =>
    setRows((r) => r.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  const move = (i: number, d: number) =>
    setRows((r) => {
      const n = [...r];
      [n[i], n[i + d]] = [n[i + d], n[i]];
      return n;
    });
  const invalid = rows.some((r) => r.question.trim().length < 10);

  return (
    <div className="space-y-3">
      {rows.map((r, i) => (
        <div key={r.id ?? `new-${i}`} className="bg-card rounded-xl border p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold tabular-nums">Q{i + 1}</span>
            <NativeSelect
              aria-label="Category"
              value={r.category}
              onChange={(e) =>
                upd(i, { category: e.target.value as QuestionCategory })
              }
              className="h-8 text-xs"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </NativeSelect>
            <NativeSelect
              aria-label="Difficulty"
              value={r.difficulty}
              onChange={(e) =>
                upd(i, { difficulty: e.target.value as Difficulty })
              }
              className="h-8 text-xs"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </NativeSelect>
            <span className="text-muted-foreground text-xs">
              {r.source ? r.source.replace("_", " ") : "new"}
            </span>
            <div className="ml-auto flex">
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label="Move up"
                disabled={i === 0}
                onClick={() => move(i, -1)}
              >
                <ArrowUp />
              </Button>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label="Move down"
                disabled={i === rows.length - 1}
                onClick={() => move(i, 1)}
              >
                <ArrowDown />
              </Button>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label="Delete question"
                disabled={rows.length === 1}
                onClick={() => setRows(rows.filter((_, j) => j !== i))}
              >
                <Trash2 />
              </Button>
            </div>
          </div>
          <Textarea
            aria-label={`Question ${i + 1}`}
            rows={2}
            value={r.question}
            onChange={(e) => upd(i, { question: e.target.value })}
            aria-invalid={r.question.trim().length < 10}
          />
          <p className="mt-2 mb-1 text-xs font-medium">
            Expected concepts (used for the rubric)
          </p>
          <TagInput
            value={r.expected_concepts}
            onChange={(v) => upd(i, { expected_concepts: v })}
            placeholder="Add a concept"
          />
        </div>
      ))}
      <div className="flex flex-wrap justify-between gap-2">
        <Button
          variant="outline"
          disabled={rows.length >= 15}
          onClick={() =>
            setRows([
              ...rows,
              {
                question: "",
                category: iv.categories[0] ?? "programming",
                difficulty: iv.difficulty,
                expected_concepts: [],
              },
            ])
          }
        >
          <Plus /> Add question
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => save.mutate()}
            disabled={save.isPending || invalid}
          >
            {save.isPending && <Loader2 className="animate-spin" />} Save
            questions
          </Button>
        </div>
      </div>
      {invalid && (
        <p className="text-destructive text-sm">
          Each question needs at least 10 characters.
        </p>
      )}
    </div>
  );
}

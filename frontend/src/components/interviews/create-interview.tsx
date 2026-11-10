"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, MessageSquarePlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/common/bits";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";
import { CATEGORIES } from "@/lib/labels";
import type { Interview, QuestionCategory } from "@/types/api";

export function CreateInterview({
  applicationId,
  type,
  label = "Create interview",
  detailHref,
}: {
  applicationId: string;
  type: "assigned" | "practice";
  label?: string;
  detailHref: (id: string) => string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [cats, setCats] = useState<QuestionCategory[]>(
    type === "assigned"
      ? ["programming", "dbms", "project"]
      : ["programming", "behavioral"],
  );
  const [difficulty, setDifficulty] = useState("intermediate");
  const [count, setCount] = useState(5);
  const create = useMutation({
    mutationFn: async () => {
      const iv = await api<Interview>("/interviews", {
        method: "POST",
        body: {
          application_id: applicationId,
          interview_type: type,
          question_count: count,
          difficulty,
          categories: cats,
        },
      });
      const g = await api<{ interview: Interview; notice: string | null }>(
        `/interviews/${iv.id}/generate-questions`,
        { method: "POST" },
      );
      return g;
    },
    onSuccess: (g) => {
      if (g.notice) toast.info(g.notice);
      else toast.success("Questions generated");
      router.push(detailHref(g.interview.id));
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <>
      <Button
        size="sm"
        variant={type === "assigned" ? "default" : "secondary"}
        onClick={() => setOpen(true)}
      >
        <MessageSquarePlus /> {label}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {type === "assigned" ? "New interview" : "New practice interview"}
            </DialogTitle>
            <DialogDescription>
              Questions are based on the job requirements, the resume and skill
              gaps.
              {type === "assigned"
                ? " You can review and edit them before the candidate starts."
                : ""}
            </DialogDescription>
          </DialogHeader>
          <fieldset>
            <legend className="mb-2 text-sm font-medium">Categories</legend>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((c) => (
                <Label
                  key={c.value}
                  className="flex items-center gap-2 font-normal"
                >
                  <Checkbox
                    checked={cats.includes(c.value)}
                    onCheckedChange={(v) =>
                      setCats((s) =>
                        v ? [...s, c.value] : s.filter((x) => x !== c.value),
                      )
                    }
                  />
                  {c.label}
                </Label>
              ))}
            </div>
          </fieldset>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="diff">Difficulty</Label>
              <NativeSelect
                id="diff"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </NativeSelect>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="count">Questions</Label>
              <NativeSelect
                id="count"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="w-full"
              >
                {[3, 4, 5, 6, 8, 10, 12, 15].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </NativeSelect>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => create.mutate()}
              disabled={create.isPending || cats.length === 0}
            >
              {create.isPending && <Loader2 className="animate-spin" />}{" "}
              Generate questions
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

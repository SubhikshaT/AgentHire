"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/common/bits";
import { ConfirmDialog } from "@/components/common/confirm";
import { LoadingBlock } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, errorMessage } from "@/lib/api";
import { fmtDate, STAGES, stageLabel } from "@/lib/labels";
import type { Stage, StageHistory } from "@/types/api";

export function StageControl({
  applicationId,
  stage,
  onChanged,
}: {
  applicationId: string;
  stage: Stage;
  onChanged?: () => void;
}) {
  const qc = useQueryClient();
  const [pending, setPending] = useState<Stage | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const change = useMutation({
    mutationFn: (to: Stage) =>
      api(`/applications/${applicationId}/stage`, {
        method: "PATCH",
        body: { stage: to },
      }),
    onSuccess: (_d, to) => {
      toast.success(`Moved to ${stageLabel(to)}`);
      qc.invalidateQueries();
      onChanged?.();
    },
    onError: (e) => toast.error(errorMessage(e)),
    onSettled: () => setPending(null),
  });
  const history = useQuery({
    queryKey: ["history", applicationId],
    queryFn: () =>
      api<StageHistory[]>(`/applications/${applicationId}/history`),
    enabled: historyOpen,
  });

  return (
    <div className="flex items-center gap-1">
      <NativeSelect
        aria-label="Recruitment stage"
        value={stage}
        disabled={change.isPending}
        onChange={(e) => {
          const to = e.target.value as Stage;
          if (to === "rejected" || to === "selected") setPending(to);
          else change.mutate(to);
        }}
        className="h-8 text-xs"
      >
        {STAGES.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </NativeSelect>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Stage history"
        onClick={() => setHistoryOpen(true)}
      >
        <History />
      </Button>
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(o) => !o && setPending(null)}
        title={`Mark as ${pending ? stageLabel(pending) : ""}?`}
        description="This is a hiring decision made by you. AI scores are only decision support. The change is recorded in the stage history."
        confirmLabel={`Mark as ${pending ? stageLabel(pending) : ""}`}
        destructive={pending === "rejected"}
        onConfirm={() => pending && change.mutate(pending)}
        pending={change.isPending}
      />
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Stage history</DialogTitle>
          </DialogHeader>
          {history.isPending ? (
            <LoadingBlock rows={2} />
          ) : (
            <ol className="space-y-2 text-sm">
              {history.data?.map((h) => (
                <li key={h.id} className="rounded-lg border p-2.5">
                  <p>
                    {h.from_stage ? `${stageLabel(h.from_stage)} → ` : ""}
                    <span className="font-medium">
                      {stageLabel(h.to_stage)}
                    </span>
                  </p>
                  <p className="text-muted-foreground text-xs">
                    {fmtDate(h.changed_at, true)} ·{" "}
                    {h.changed_by_name ?? "System"}
                    {h.note ? ` · ${h.note}` : ""}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

"use client";

import "@xyflow/react/dist/style.css";

import { useQuery } from "@tanstack/react-query";
import {
  Background,
  Controls,
  type Edge,
  type Node,
  ReactFlow,
} from "@xyflow/react";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo } from "react";

import { ErrorState, LoadingBlock } from "@/components/common/states";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

type GraphData = {
  job_title: string;
  nodes: {
    id: string;
    label: string;
    kind: "matched" | "related_only" | "missing" | "candidate" | "path";
    importance?: string;
  }[];
  edges: {
    source: string;
    target: string;
    kind: "related" | "transferable" | "path";
  }[];
  learning_paths: { target: string; path: string[] | null }[];
  note: string;
};

const STYLE: Record<
  string,
  { bg: string; border: string; col: number; label: string }
> = {
  candidate: {
    bg: "#eef0fb",
    border: "#6366f1",
    col: 0,
    label: "Candidate skill (not asked by job)",
  },
  path: {
    bg: "#f5f3ff",
    border: "#a78bfa",
    col: 1,
    label: "Learning-path step",
  },
  matched: {
    bg: "#e7f6ee",
    border: "#16a34a",
    col: 2,
    label: "Job skill — has it",
  },
  related_only: {
    bg: "#fff7e6",
    border: "#d97706",
    col: 3,
    label: "Job skill — related skill only",
  },
  missing: {
    bg: "#fdecec",
    border: "#dc2626",
    col: 4,
    label: "Job skill — missing",
  },
};

export function SkillGraph() {
  const sp = useSearchParams();
  const candidate = sp.get("candidate") ?? "";
  const job = sp.get("job") ?? "";
  const q = useQuery({
    queryKey: ["skill-graph", candidate, job],
    queryFn: () =>
      api<GraphData>(`/candidates/${candidate}/skill-graph?job_id=${job}`),
    enabled: !!candidate && !!job,
  });

  const { nodes, edges } = useMemo(() => {
    if (!q.data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const perCol: Record<number, number> = {};
    const nodes: Node[] = q.data.nodes.map((n) => {
      const st = STYLE[n.kind];
      const row = (perCol[st.col] = (perCol[st.col] ?? -1) + 1);
      return {
        id: n.id,
        position: { x: st.col * 210, y: row * 64 },
        data: {
          label: `${n.label}${n.importance === "preferred" ? " (pref.)" : ""}`,
        },
        style: {
          background: st.bg,
          border: `1.5px solid ${st.border}`,
          borderRadius: 10,
          fontSize: 12,
          width: 170,
          padding: 6,
        },
      };
    });
    const edges: Edge[] = q.data.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      animated: e.kind === "path",
      style: {
        stroke:
          e.kind === "path"
            ? "#8b5cf6"
            : e.kind === "transferable"
              ? "#d97706"
              : "#94a3b8",
        strokeWidth: e.kind === "related" ? 1 : 2,
      },
    }));
    return { nodes, edges };
  }, [q.data]);

  if (!candidate || !job)
    return (
      <ErrorState
        error={
          new Error("Open the skill graph from a candidate's application.")
        }
      />
    );
  if (q.isPending) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;

  return (
    <>
      <Link
        href={`/candidates/${candidate}?job=${job}`}
        className="text-muted-foreground hover:text-foreground mb-3 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> Back to candidate
      </Link>
      <PageHeader
        title="Skill graph"
        description={`Candidate skills vs. ${q.data.job_title}. ${q.data.note}`}
      />
      <div className="mb-3 flex flex-wrap gap-3 text-xs">
        {Object.entries(STYLE).map(([k, s]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-3 rounded"
              style={{ background: s.bg, border: `1.5px solid ${s.border}` }}
            />
            {s.label}
          </span>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_18rem]">
        <div
          className="bg-card h-[32rem] rounded-xl border"
          aria-label="Interactive skill graph"
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            nodesConnectable={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Learning paths</CardTitle>
          </CardHeader>
          <CardContent>
            {q.data.learning_paths.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No gaps for this job.
              </p>
            ) : (
              <ul className="space-y-2 text-sm">
                {q.data.learning_paths.map((p) => (
                  <li key={p.target}>
                    <p className="font-medium">{p.target}</p>
                    <p className="text-muted-foreground text-xs">
                      {p.path
                        ? p.path.join(" → ")
                        : "No known path from current skills — learn from basics."}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

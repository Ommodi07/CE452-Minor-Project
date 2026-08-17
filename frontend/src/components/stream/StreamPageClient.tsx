"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageCard } from "@/components/ui/page-card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { checkStream, getSession } from "@/lib/api";

interface StreamPageClientProps {
  sessionId: string;
}

export function StreamPageClient({ sessionId }: StreamPageClientProps) {
  const [streamAvailable, setStreamAvailable] = useState<boolean | null>(null);
  const [detail, setDetail] = useState<string>("");
  const [sessionStatus, setSessionStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function check() {
      setLoading(true);
      try {
        const streamResult = await checkStream(sessionId);
        setStreamAvailable(streamResult.available);
        setDetail(streamResult.detail ?? "");
      } catch {
        setStreamAvailable(false);
        setDetail("Failed to reach stream endpoint");
      }

      try {
        const session = await getSession(sessionId);
        setSessionStatus(session.state.status ?? "unknown");
      } catch {
        setSessionStatus("not found");
      }

      setLoading(false);
    }

    void check();
  }, [sessionId]);

  const graphNodes = ["Planner", "Researcher", "Critic", "Writer"];

  return (
    <div className="space-y-6">
      <PageCard
        title="Live Stream"
        subtitle={`GET /stream/${sessionId}`}
        badge={<Badge variant="warning">Preview</Badge>}
      >
        <p className="text-sm text-muted-foreground">
          Session: <span className="font-mono font-medium text-foreground">{sessionId}</span>
        </p>
        {sessionStatus && (
          <p className="mt-1 text-sm">
            Session status:{" "}
            <Badge variant={sessionStatus === "done" ? "success" : "info"}>{sessionStatus}</Badge>
          </p>
        )}
      </PageCard>

      <PageCard title="Stream Endpoint Status">
        {loading ? (
          <p className="font-head text-lg blink-cursor">Checking stream...</p>
        ) : streamAvailable ? (
          <p className="font-medium text-green-700">Stream endpoint is available.</p>
        ) : (
          <div className="space-y-4">
            <div className="alert-warning rounded p-4">
              <p className="font-head text-lg">501 — Not Yet Implemented</p>
              <p className="mt-2 text-sm">{detail}</p>
            </div>
            <p className="text-sm">
              The backend streaming endpoint is planned for Server-Sent Events (SSE) to show live
              LangGraph node progress. Until then, use the session viewer or run research synchronously.
            </p>
          </div>
        )}
      </PageCard>

      <PageCard title="Agent Pipeline Visualizer">
        <p className="mb-4 text-sm text-muted-foreground">
          Preview of the planned live graph visualizer — nodes will highlight as agents execute.
        </p>
        <div className="flex flex-col items-center gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
          {graphNodes.map((node, index) => (
            <div key={node} className="flex items-center gap-2">
              <div
                className={`graph-node min-w-[110px] ${
                  sessionStatus === "done"
                    ? "done"
                    : index === 0 && sessionStatus !== "not found"
                      ? "active"
                      : ""
                }`}
              >
                {node}
              </div>
              {index < graphNodes.length - 1 && (
                <span className="graph-arrow hidden sm:inline" aria-hidden="true">
                  →
                </span>
              )}
            </div>
          ))}
        </div>
      </PageCard>

      <div className="flex flex-wrap gap-2">
        <Link href={`/sessions/${sessionId}`} className={cn(buttonVariants({ variant: "default" }))}>
          View Session
        </Link>
        <Link href={`/report/${sessionId}`} className={cn(buttonVariants({ variant: "outline" }))}>
          View Report
        </Link>
        <Link href="/" className={cn(buttonVariants({ variant: "outline" }))}>
          New Research
        </Link>
      </div>
    </div>
  );
}

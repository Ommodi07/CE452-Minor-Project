"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroButton } from "@/components/ui/RetroButton";
import { RetroBadge } from "@/components/ui/RetroBadge";
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
      <RetroCard
        title="Live Stream"
        subtitle={`GET /stream/${sessionId}`}
        badge={<RetroBadge variant="warn">Preview</RetroBadge>}
      >
        <p className="text-sm text-retro-text-dim">
          Session: <span className="font-mono text-retro-cyan">{sessionId}</span>
        </p>
        {sessionStatus && (
          <p className="mt-1 text-sm">
            Session status:{" "}
            <RetroBadge variant={sessionStatus === "done" ? "ok" : "info"}>{sessionStatus}</RetroBadge>
          </p>
        )}
      </RetroCard>

      <RetroCard title="Stream Endpoint Status">
        {loading ? (
          <p className="font-terminal text-lg text-retro-amber blink-cursor">Checking stream...</p>
        ) : streamAvailable ? (
          <p className="text-retro-border-bright">Stream endpoint is available.</p>
        ) : (
          <div className="space-y-4">
            <div className="retro-panel-inset border-retro-amber p-4">
              <p className="font-terminal text-lg text-retro-amber">501 — Not Yet Implemented</p>
              <p className="mt-2 text-sm text-retro-text-dim">{detail}</p>
            </div>
            <p className="text-sm text-retro-text">
              The backend streaming endpoint is planned for Server-Sent Events (SSE) to show live
              LangGraph node progress. Until then, use the session viewer or run research synchronously.
            </p>
          </div>
        )}
      </RetroCard>

      <RetroCard title="Agent Pipeline Visualizer">
        <p className="mb-4 text-sm text-retro-text-dim">
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
      </RetroCard>

      <div className="flex flex-wrap gap-2">
        <Link href={`/sessions/${sessionId}`} className="retro-btn">
          View Session
        </Link>
        <Link href={`/report/${sessionId}`} className="retro-btn retro-btn-secondary">
          View Report
        </Link>
        <Link href="/" className="retro-btn retro-btn-secondary">
          New Research
        </Link>
      </div>
    </div>
  );
}

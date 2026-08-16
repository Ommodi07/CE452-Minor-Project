"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ReportViewer } from "@/components/research/ReportViewer";
import { RetroCard } from "@/components/ui/RetroCard";
import { ResearchProgress } from "@/components/research/ResearchProgress";
import { getSession, ApiClientError } from "@/lib/api";
import type { ResearchResponse } from "@/lib/types";

interface ReportPageClientProps {
  sessionId: string;
}

export function ReportPageClient({ sessionId }: ReportPageClientProps) {
  const [data, setData] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const session = await getSession(sessionId);
        const state = session.state;

        if (!state.report && state.status !== "done") {
          setError("Report not yet available for this session.");
          setData(null);
          return;
        }

        setData({
          session_id: sessionId,
          status: state.status ?? "done",
          report: state.report ?? null,
          open_questions: state.open_questions ?? [],
          errors: state.errors ?? [],
        });
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError(`[${err.status}] ${err.message}`);
        } else {
          setError(err instanceof Error ? err.message : "Failed to load report");
        }
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [sessionId]);

  if (loading) {
    return <ResearchProgress active={false} />;
  }

  if (error || !data) {
    return (
      <RetroCard title="Report Not Found">
        <p className="text-retro-red">{error ?? "No report data available."}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href={`/sessions/${sessionId}`} className="retro-btn">
            View Session
          </Link>
          <Link href="/" className="retro-btn retro-btn-secondary">
            Run New Research
          </Link>
        </div>
      </RetroCard>
    );
  }

  return <ReportViewer data={data} />;
}

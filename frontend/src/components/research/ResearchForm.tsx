"use client";

import { useState } from "react";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroButton } from "@/components/ui/RetroButton";
import { ResearchProgress } from "./ResearchProgress";
import { ReportViewer } from "./ReportViewer";
import { createSession, runResearch, ApiClientError } from "@/lib/api";
import { saveRecentSession } from "@/lib/endpoints";
import type { ResearchResponse } from "@/lib/types";

const EXAMPLE_QUERIES = [
  "Impact of remote work on urban housing markets",
  "Latest developments in fusion energy research",
  "Ethical implications of AI in healthcare diagnostics",
];

export function ResearchForm() {
  const [query, setQuery] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [maxIterations, setMaxIterations] = useState(2);
  const [loading, setLoading] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResearchResponse | null>(null);

  const handleCreateSession = async () => {
    setCreatingSession(true);
    setError(null);
    try {
      const session = await createSession();
      setSessionId(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setCreatingSession(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await runResearch({
        query: query.trim(),
        session_id: sessionId.trim() || null,
        max_iterations: maxIterations,
      });
      setResult(response);
      setSessionId(response.session_id);
      saveRecentSession(response.session_id);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`[${err.status}] ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Research failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <RetroCard
        title="New Research Query"
        subtitle="POST /research — Multi-agent LangGraph pipeline"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="query" className="mb-2 block font-terminal text-lg text-retro-text-bright">
              Research Question
            </label>
            <textarea
              id="query"
              className="retro-textarea"
              placeholder="Enter your research question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
              disabled={loading}
              rows={4}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="sessionId" className="mb-2 block text-sm text-retro-text-dim">
                Session ID (optional)
              </label>
              <div className="flex gap-2">
                <input
                  id="sessionId"
                  type="text"
                  className="retro-input"
                  placeholder="Auto-generated if empty"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  disabled={loading}
                />
                <RetroButton
                  type="button"
                  variant="secondary"
                  onClick={handleCreateSession}
                  disabled={loading || creatingSession}
                  className="shrink-0 whitespace-nowrap"
                >
                  {creatingSession ? "..." : "New"}
                </RetroButton>
              </div>
            </div>

            <div>
              <label htmlFor="maxIterations" className="mb-2 block text-sm text-retro-text-dim">
                Max Iterations
              </label>
              <select
                id="maxIterations"
                className="retro-select"
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                disabled={loading}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n} {n === 1 ? "iteration" : "iterations"}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs text-retro-text-dim">Quick examples:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setQuery(example)}
                  disabled={loading}
                  className="rounded border border-retro-border px-2 py-1 text-xs text-retro-text-dim transition-colors hover:border-retro-border-bright hover:text-retro-text"
                >
                  {example.slice(0, 40)}...
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="retro-panel-inset border-retro-red p-3 text-sm text-retro-red">
              ERROR: {error}
            </div>
          )}

          <RetroButton type="submit" disabled={loading || !query.trim()} className="w-full sm:w-auto">
            {loading ? "Running Research..." : "▶ Execute Research"}
          </RetroButton>
        </form>
      </RetroCard>

      {loading && <ResearchProgress active query={query} />}

      {result && !loading && <ReportViewer data={result} />}
    </div>
  );
}

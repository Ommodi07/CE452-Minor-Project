"use client";

import { useState } from "react";
import { Play, Plus } from "lucide-react";
import { PageCard } from "@/components/ui/page-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
      <PageCard title="New Research Query" subtitle="POST /research — Multi-agent LangGraph pipeline">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="query">Research Question</Label>
            <Textarea
              id="query"
              placeholder="Enter your research question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
              disabled={loading}
              rows={4}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="sessionId">Session ID (optional)</Label>
              <div className="flex gap-2">
                <Input
                  id="sessionId"
                  type="text"
                  placeholder="Auto-generated if empty"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  disabled={loading}
                />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCreateSession}
                  disabled={loading || creatingSession}
                  className="shrink-0"
                >
                  <Plus className="size-4" />
                  {creatingSession ? "..." : "New"}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxIterations">Max Iterations</Label>
              <select
                id="maxIterations"
                className="neo-select"
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
            <p className="mb-2 text-sm text-muted-foreground">Quick examples:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setQuery(example)}
                  disabled={loading}
                  className="rounded border-2 border-black bg-accent px-2 py-1 text-xs shadow-sm transition-transform hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-md"
                >
                  {example.slice(0, 40)}...
                </button>
              ))}
            </div>
          </div>

          {error && <div className="alert-error rounded p-3 text-sm">Error: {error}</div>}

          <Button type="submit" disabled={loading || !query.trim()} className="w-full sm:w-auto">
            <Play className="size-4" />
            {loading ? "Running Research..." : "Execute Research"}
          </Button>
        </form>
      </PageCard>

      {loading && <ResearchProgress active query={query} />}

      {result && !loading && <ReportViewer data={result} />}
    </div>
  );
}

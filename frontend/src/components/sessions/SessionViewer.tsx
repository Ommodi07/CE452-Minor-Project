"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Download, ExternalLink, Plus } from "lucide-react";
import { PageCard } from "@/components/ui/page-card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { createSession, getSession, downloadReport, ApiClientError } from "@/lib/api";
import { saveRecentSession } from "@/lib/endpoints";
import type { SessionResponse, SourceDoc } from "@/lib/types";

interface SessionViewerProps {
  initialSessionId?: string;
}

export function SessionViewer({ initialSessionId = "" }: SessionViewerProps) {
  const [sessionId, setSessionId] = useState(initialSessionId);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentIds, setRecentIds] = useState<string[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem("recentSessions");
    if (stored) {
      try {
        setRecentIds(JSON.parse(stored) as string[]);
      } catch {
        /* ignore */
      }
    }
  }, []);

  useEffect(() => {
    if (initialSessionId) {
      void fetchSession(initialSessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSessionId]);

  const saveRecent = (id: string) => {
    saveRecentSession(id);
    const updated = [id, ...recentIds.filter((r) => r !== id)].slice(0, 8);
    setRecentIds(updated);
  };

  const fetchSession = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSession(id);
      setSession(data);
      setSessionId(id);
      saveRecent(id);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`[${err.status}] ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load session");
      }
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const data = await createSession();
      setSessionId(data.session_id);
      await fetchSession(data.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setCreating(false);
    }
  };

  const state = session?.state;

  const statusBadge = (status?: string) => {
    if (status === "done") return "success" as const;
    if (status === "error") return "destructive" as const;
    return "info" as const;
  };

  return (
    <div className="space-y-6">
      <PageCard title="Session Manager" subtitle="POST /sessions · GET /sessions/{id}">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            type="text"
            className="flex-1"
            placeholder="Enter session ID..."
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && sessionId.trim()) {
                void fetchSession(sessionId.trim());
              }
            }}
          />
          <Button
            onClick={() => sessionId.trim() && fetchSession(sessionId.trim())}
            disabled={loading || !sessionId.trim()}
          >
            {loading ? "Loading..." : "Load Session"}
          </Button>
          <Button variant="secondary" onClick={handleCreate} disabled={creating}>
            <Plus className="size-4" />
            {creating ? "Creating..." : "Create New"}
          </Button>
        </div>

        {recentIds.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-sm text-muted-foreground">Recent sessions:</p>
            <div className="flex flex-wrap gap-2">
              {recentIds.map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => fetchSession(id)}
                  className="rounded border-2 border-black bg-accent px-2 py-1 font-mono text-xs shadow-sm hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-md"
                >
                  {id.slice(0, 8)}...
                </button>
              ))}
            </div>
          </div>
        )}

        {error && <div className="alert-error mt-4 rounded p-3 text-sm">Error: {error}</div>}
      </PageCard>

      {state && session && (
        <>
          <PageCard
            title={`Session: ${session.session_id}`}
            badge={<Badge variant={statusBadge(state.status)}>{state.status ?? "created"}</Badge>}
          >
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Sub-Questions" value={state.sub_questions?.length ?? 0} />
              <Stat label="Sources" value={state.source_docs?.length ?? 0} />
              <Stat label="Claims" value={state.claims?.length ?? 0} />
              <Stat label="Verified" value={state.verified_claims?.length ?? 0} />
            </div>

            {state.original_query && (
              <p className="mt-4 text-sm">
                <span className="text-muted-foreground">Query:</span>{" "}
                <span className="font-medium">{state.original_query}</span>
              </p>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              {state.report && (
                <Link
                  href={`/report/${session.session_id}`}
                  className={cn(buttonVariants({ variant: "default" }))}
                >
                  View Report
                </Link>
              )}
              <Link
                href={`/stream/${session.session_id}`}
                className={cn(buttonVariants({ variant: "outline" }))}
              >
                Stream Status
              </Link>
              {state.status === "done" && (
                <Button variant="secondary" onClick={() => downloadReport(session.session_id)}>
                  <Download className="size-4" />
                  Export DOCX
                </Button>
              )}
            </div>
          </PageCard>

          {state.sub_questions && state.sub_questions.length > 0 && (
            <PageCard title="Sub-Questions">
              <div className="space-y-3">
                {state.sub_questions.map((sq) => (
                  <div key={sq.id} className="inset-panel rounded p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{sq.angle}</Badge>
                      <Badge
                        variant={
                          sq.status === "answered"
                            ? "success"
                            : sq.status === "failed"
                              ? "destructive"
                              : "info"
                        }
                      >
                        {sq.status}
                      </Badge>
                      <Badge variant="outline">{sq.research_method}</Badge>
                    </div>
                    <p className="mt-2 text-sm">{sq.question_text}</p>
                    {sq.refined_query && (
                      <p className="mt-1 text-xs text-muted-foreground">Refined: {sq.refined_query}</p>
                    )}
                  </div>
                ))}
              </div>
            </PageCard>
          )}

          {state.source_docs && state.source_docs.length > 0 && (
            <PageCard title="Source Documents">
              <div className="space-y-3">
                {state.source_docs.map((source) => (
                  <SourceDocCard key={source.id} source={source} />
                ))}
              </div>
            </PageCard>
          )}

          {state.verified_claims && state.verified_claims.length > 0 && (
            <PageCard title="Verified Claims">
              <div className="space-y-3">
                {state.verified_claims.map((claim) => (
                  <div key={claim.id} className="inset-panel rounded p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant={
                          claim.verification_status === "corroborated"
                            ? "success"
                            : claim.verification_status === "disputed"
                              ? "warning"
                              : "outline"
                        }
                      >
                        {claim.verification_status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        Confidence: {(claim.adjusted_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="mt-2 text-sm">{claim.claim_text}</p>
                    {claim.critic_notes && (
                      <p className="mt-1 text-xs text-muted-foreground">{claim.critic_notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </PageCard>
          )}

          <PageCard title="Raw State JSON">
            <pre className="inset-panel max-h-96 overflow-auto rounded p-4 text-xs text-muted-foreground">
              {JSON.stringify(state, null, 2)}
            </pre>
          </PageCard>
        </>
      )}
    </div>
  );
}

function SourceDocCard({ source }: { source: SourceDoc }) {
  return (
    <article className="inset-panel rounded p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="font-head text-base">{source.title}</h4>
        <Badge variant="outline">{source.source_type}</Badge>
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{source.snippet}</p>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {source.credibility_score != null && (
          <span>Credibility: {(source.credibility_score * 100).toFixed(0)}%</span>
        )}
        {source.author && <span>Author: {source.author}</span>}
        {source.published_date && <span>Date: {source.published_date}</span>}
      </div>
      {source.quality_flags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {source.quality_flags.map((flag) => (
            <Badge key={flag} variant="warning">
              {flag}
            </Badge>
          ))}
        </div>
      )}
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-flex items-center gap-1 text-sm text-blue-700 hover:underline"
      >
        <ExternalLink className="size-3.5" />
        {source.url}
      </a>
    </article>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="inset-panel rounded p-3 text-center">
      <p className="font-head text-2xl">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

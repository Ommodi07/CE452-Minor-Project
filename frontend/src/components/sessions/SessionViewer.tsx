"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroButton } from "@/components/ui/RetroButton";
import { RetroBadge } from "@/components/ui/RetroBadge";
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

  return (
    <div className="space-y-6">
      <RetroCard title="Session Manager" subtitle="POST /sessions · GET /sessions/{id}">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            className="retro-input flex-1"
            placeholder="Enter session ID..."
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && sessionId.trim()) {
                void fetchSession(sessionId.trim());
              }
            }}
          />
          <RetroButton
            onClick={() => sessionId.trim() && fetchSession(sessionId.trim())}
            disabled={loading || !sessionId.trim()}
          >
            {loading ? "Loading..." : "Load Session"}
          </RetroButton>
          <RetroButton variant="secondary" onClick={handleCreate} disabled={creating}>
            {creating ? "Creating..." : "+ Create New"}
          </RetroButton>
        </div>

        {recentIds.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-xs text-retro-text-dim">Recent sessions:</p>
            <div className="flex flex-wrap gap-2">
              {recentIds.map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => fetchSession(id)}
                  className="rounded border border-retro-border px-2 py-1 font-mono text-xs text-retro-cyan hover:border-retro-border-bright"
                >
                  {id.slice(0, 8)}...
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 retro-panel-inset p-3 text-sm text-retro-red">ERROR: {error}</div>
        )}
      </RetroCard>

      {state && (
        <>
          <RetroCard
            title={`Session: ${session.session_id}`}
            badge={
              <RetroBadge variant={state.status === "done" ? "ok" : state.status === "error" ? "error" : "info"}>
                {state.status ?? "created"}
              </RetroBadge>
            }
          >
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Sub-Questions" value={state.sub_questions?.length ?? 0} />
              <Stat label="Sources" value={state.source_docs?.length ?? 0} />
              <Stat label="Claims" value={state.claims?.length ?? 0} />
              <Stat label="Verified" value={state.verified_claims?.length ?? 0} />
            </div>

            {state.original_query && (
              <p className="mt-4 text-sm">
                <span className="text-retro-text-dim">Query:</span>{" "}
                <span className="text-retro-text">{state.original_query}</span>
              </p>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              {state.report && (
                <Link href={`/report/${session.session_id}`} className="retro-btn">
                  View Report
                </Link>
              )}
              <Link href={`/stream/${session.session_id}`} className="retro-btn retro-btn-secondary">
                Stream Status
              </Link>
              {state.status === "done" && (
                <RetroButton
                  variant="secondary"
                  onClick={() => downloadReport(session.session_id)}
                >
                  Export DOCX
                </RetroButton>
              )}
            </div>
          </RetroCard>

          {state.sub_questions && state.sub_questions.length > 0 && (
            <RetroCard title="Sub-Questions">
              <div className="space-y-3">
                {state.sub_questions.map((sq) => (
                  <div key={sq.id} className="retro-panel-inset p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <RetroBadge variant="neutral">{sq.angle}</RetroBadge>
                      <RetroBadge
                        variant={
                          sq.status === "answered"
                            ? "ok"
                            : sq.status === "failed"
                              ? "error"
                              : "info"
                        }
                      >
                        {sq.status}
                      </RetroBadge>
                      <RetroBadge variant="neutral">{sq.research_method}</RetroBadge>
                    </div>
                    <p className="mt-2 text-sm text-retro-text">{sq.question_text}</p>
                    {sq.refined_query && (
                      <p className="mt-1 text-xs text-retro-amber">Refined: {sq.refined_query}</p>
                    )}
                  </div>
                ))}
              </div>
            </RetroCard>
          )}

          {state.source_docs && state.source_docs.length > 0 && (
            <RetroCard title="Source Documents">
              <div className="space-y-3">
                {state.source_docs.map((source) => (
                  <SourceDocCard key={source.id} source={source} />
                ))}
              </div>
            </RetroCard>
          )}

          {state.verified_claims && state.verified_claims.length > 0 && (
            <RetroCard title="Verified Claims">
              <div className="space-y-3">
                {state.verified_claims.map((claim) => (
                  <div key={claim.id} className="retro-panel-inset p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <RetroBadge
                        variant={
                          claim.verification_status === "corroborated"
                            ? "ok"
                            : claim.verification_status === "disputed"
                              ? "warn"
                              : "neutral"
                        }
                      >
                        {claim.verification_status}
                      </RetroBadge>
                      <span className="text-xs text-retro-text-dim">
                        Confidence: {(claim.adjusted_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="mt-2 text-sm">{claim.claim_text}</p>
                    {claim.critic_notes && (
                      <p className="mt-1 text-xs text-retro-text-dim">{claim.critic_notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </RetroCard>
          )}

          <RetroCard title="Raw State JSON">
            <pre className="retro-panel-inset max-h-96 overflow-auto p-4 text-xs text-retro-text-dim">
              {JSON.stringify(state, null, 2)}
            </pre>
          </RetroCard>
        </>
      )}
    </div>
  );
}

function SourceDocCard({ source }: { source: SourceDoc }) {
  return (
    <article className="retro-panel-inset p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="font-terminal text-base text-retro-text-bright">{source.title}</h4>
        <RetroBadge variant="neutral">{source.source_type}</RetroBadge>
      </div>
      <p className="mt-2 text-sm text-retro-text-dim line-clamp-2">{source.snippet}</p>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-retro-text-dim">
        {source.credibility_score != null && (
          <span>Credibility: {(source.credibility_score * 100).toFixed(0)}%</span>
        )}
        {source.author && <span>Author: {source.author}</span>}
        {source.published_date && <span>Date: {source.published_date}</span>}
      </div>
      {source.quality_flags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {source.quality_flags.map((flag) => (
            <RetroBadge key={flag} variant="warn">
              {flag}
            </RetroBadge>
          ))}
        </div>
      )}
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-block text-sm text-retro-cyan hover:text-retro-text-bright"
      >
        {source.url}
      </a>
    </article>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="retro-panel-inset p-3 text-center">
      <p className="font-terminal text-2xl text-retro-amber">{value}</p>
      <p className="text-xs text-retro-text-dim">{label}</p>
    </div>
  );
}

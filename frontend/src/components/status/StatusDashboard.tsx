"use client";

import { useCallback, useEffect, useState } from "react";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroButton } from "@/components/ui/RetroButton";
import { RetroBadge } from "@/components/ui/RetroBadge";
import Link from "next/link";
import { getHealth, getStatus, ApiClientError } from "@/lib/api";
import { getMappingForEndpoint } from "@/lib/endpoints";
import { ApiCoverageMap } from "@/components/status/ApiCoverageMap";
import type { ConnectionStatus, HealthResponse, StatusResponse } from "@/lib/types";

export function StatusDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, statusData] = await Promise.all([getHealth(), getStatus()]);
      setHealth(healthData);
      setStatus(statusData);
      setLastRefresh(new Date());
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`[${err.status}] ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Failed to fetch status");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-xs text-retro-text-bright sm:text-sm">SYSTEM STATUS</h1>
          <p className="font-terminal text-lg text-retro-text-dim">
            GET /health · GET /status
          </p>
        </div>
        <RetroButton onClick={refresh} disabled={loading}>
          {loading ? "Refreshing..." : "↻ Refresh"}
        </RetroButton>
      </div>

      {error && (
        <RetroCard title="Connection Error">
          <p className="text-retro-red">{error}</p>
          <p className="mt-2 text-sm text-retro-text-dim">
            Ensure the backend is running at the configured API URL.
          </p>
        </RetroCard>
      )}

      {health && (
        <RetroCard
          title="Health Check"
          badge={<RetroBadge variant="ok">{health.status}</RetroBadge>}
        >
          <p className="font-terminal text-xl text-retro-text-bright">{health.app}</p>
        </RetroCard>
      )}

      {status && (
        <>
          <RetroCard
            title={status.app_name}
            subtitle={`Environment: ${status.environment}`}
            badge={
              <RetroBadge variant={status.overall_ok ? "ok" : "error"}>
                {status.overall_ok ? "All Systems OK" : "Issues Detected"}
              </RetroBadge>
            }
          >
            {lastRefresh && (
              <p className="text-xs text-retro-text-dim">
                Last checked: {lastRefresh.toLocaleTimeString()}
              </p>
            )}
          </RetroCard>

          <RetroCard title="Connections">
            <div className="grid gap-3 sm:grid-cols-2">
              {status.connections.map((conn) => (
                <ConnectionCard key={conn.name} connection={conn} />
              ))}
            </div>
          </RetroCard>

          <RetroCard title="API Endpoints">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[500px] text-left text-sm">
                <thead>
                  <tr className="border-b border-retro-border text-retro-text-dim">
                    <th className="pb-2 pr-4 font-terminal text-base">Method</th>
                    <th className="pb-2 pr-4 font-terminal text-base">Path</th>
                    <th className="pb-2 pr-4 font-terminal text-base">Status</th>
                    <th className="pb-2 font-terminal text-base">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {status.endpoints.map((endpoint) => {
                    const mapping = getMappingForEndpoint(endpoint.method, endpoint.path);

                    return (
                      <tr
                        key={`${endpoint.method}-${endpoint.path}`}
                        className="border-b border-retro-border/50"
                      >
                        <td className="py-3 pr-4">
                          <RetroBadge
                            variant={
                              endpoint.method === "GET"
                                ? "info"
                                : endpoint.method === "POST"
                                  ? "ok"
                                  : "neutral"
                            }
                          >
                            {endpoint.method}
                          </RetroBadge>
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs text-retro-cyan">
                          {endpoint.path}
                        </td>
                        <td className="py-3 pr-4">
                          <RetroBadge variant={endpoint.active ? "ok" : "error"}>
                            {endpoint.active ? "Active" : "Inactive"}
                          </RetroBadge>
                        </td>
                        <td className="py-3 text-retro-text-dim">
                          {endpoint.description}
                          {mapping && (
                            <Link
                              href={mapping.frontendRoute.replace(/\[.*?\]/g, "")}
                              className="mt-1 block font-terminal text-sm text-retro-amber hover:text-retro-text-bright"
                            >
                              → {mapping.frontendLabel}
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </RetroCard>

          <ApiCoverageMap />
        </>
      )}
    </div>
  );
}

function ConnectionCard({ connection }: { connection: ConnectionStatus }) {
  const variant = connection.active ? "ok" : connection.configured ? "error" : "warn";

  return (
    <div className="retro-panel-inset p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-terminal text-lg text-retro-text-bright">{connection.name}</h3>
        <RetroBadge variant={variant}>
          {connection.active ? "Active" : connection.configured ? "Down" : "Not Configured"}
        </RetroBadge>
      </div>
      <p className="mt-2 text-xs text-retro-text-dim">{connection.details}</p>
    </div>
  );
}

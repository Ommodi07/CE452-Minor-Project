"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { PageCard } from "@/components/ui/page-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
          <h1 className="font-head text-2xl sm:text-3xl">System Status</h1>
          <p className="text-sm text-muted-foreground">GET /health · GET /status</p>
        </div>
        <Button onClick={refresh} disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {error && (
        <PageCard title="Connection Error">
          <p className="text-destructive">{error}</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Ensure the backend is running at the configured API URL.
          </p>
        </PageCard>
      )}

      {health && (
        <PageCard title="Health Check" badge={<Badge variant="success">{health.status}</Badge>}>
          <p className="font-head text-xl">{health.app}</p>
        </PageCard>
      )}

      {status && (
        <>
          <PageCard
            title={status.app_name}
            subtitle={`Environment: ${status.environment}`}
            badge={
              <Badge variant={status.overall_ok ? "success" : "destructive"}>
                {status.overall_ok ? "All Systems OK" : "Issues Detected"}
              </Badge>
            }
          >
            {lastRefresh && (
              <p className="text-xs text-muted-foreground">
                Last checked: {lastRefresh.toLocaleTimeString()}
              </p>
            )}
          </PageCard>

          <PageCard title="Connections">
            <div className="grid gap-3 sm:grid-cols-2">
              {status.connections.map((conn) => (
                <ConnectionCard key={conn.name} connection={conn} />
              ))}
            </div>
          </PageCard>

          <PageCard title="API Endpoints">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[500px] text-left text-sm">
                <thead>
                  <tr className="border-b-2 border-black text-muted-foreground">
                    <th className="pb-2 pr-4 font-head">Method</th>
                    <th className="pb-2 pr-4 font-head">Path</th>
                    <th className="pb-2 pr-4 font-head">Status</th>
                    <th className="pb-2 font-head">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {status.endpoints.map((endpoint) => {
                    const mapping = getMappingForEndpoint(endpoint.method, endpoint.path);

                    return (
                      <tr key={`${endpoint.method}-${endpoint.path}`} className="border-b border-black/20">
                        <td className="py-3 pr-4">
                          <Badge variant={endpoint.method === "GET" ? "info" : "warning"}>
                            {endpoint.method}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs">{endpoint.path}</td>
                        <td className="py-3 pr-4">
                          <Badge variant={endpoint.active ? "success" : "destructive"}>
                            {endpoint.active ? "Active" : "Inactive"}
                          </Badge>
                        </td>
                        <td className="py-3 text-muted-foreground">
                          {endpoint.description}
                          {mapping && (
                            <Link
                              href={mapping.frontendRoute.replace(/\[.*?\]/g, "")}
                              className="mt-1 block font-head text-sm text-foreground hover:underline"
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
          </PageCard>

          <ApiCoverageMap />
        </>
      )}
    </div>
  );
}

function ConnectionCard({ connection }: { connection: ConnectionStatus }) {
  const variant = connection.active
    ? "success"
    : connection.configured
      ? "destructive"
      : "warning";

  return (
    <div className="inset-panel rounded p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-head text-base">{connection.name}</h3>
        <Badge variant={variant}>
          {connection.active ? "Active" : connection.configured ? "Down" : "Not Configured"}
        </Badge>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{connection.details}</p>
    </div>
  );
}

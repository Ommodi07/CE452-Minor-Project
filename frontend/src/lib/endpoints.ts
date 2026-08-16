export interface EndpointMapping {
  method: string;
  path: string;
  frontendRoute: string;
  frontendLabel: string;
  description: string;
}

export const ENDPOINT_MAPPINGS: EndpointMapping[] = [
  {
    method: "GET",
    path: "/health",
    frontendRoute: "/status",
    frontendLabel: "Status Dashboard",
    description: "Basic service health check",
  },
  {
    method: "POST",
    path: "/research",
    frontendRoute: "/",
    frontendLabel: "Research",
    description: "Run the multi-agent research pipeline",
  },
  {
    method: "GET",
    path: "/research/{job_id}/export",
    frontendRoute: "/report/[sessionId]",
    frontendLabel: "Report Export",
    description: "Download completed report as DOCX",
  },
  {
    method: "POST",
    path: "/sessions",
    frontendRoute: "/sessions",
    frontendLabel: "Sessions",
    description: "Create a new research session",
  },
  {
    method: "GET",
    path: "/sessions/{session_id}",
    frontendRoute: "/sessions/[id]",
    frontendLabel: "Session Detail",
    description: "Fetch stored session graph state",
  },
  {
    method: "GET",
    path: "/stream/{session_id}",
    frontendRoute: "/stream/[sessionId]",
    frontendLabel: "Live Stream",
    description: "SSE progress stream (501 stub)",
  },
  {
    method: "GET",
    path: "/status",
    frontendRoute: "/status",
    frontendLabel: "Status Dashboard",
    description: "API routes and connection health",
  },
];

export function getMappingForEndpoint(method: string, path: string): EndpointMapping | undefined {
  return ENDPOINT_MAPPINGS.find((m) => m.method === method && m.path === path);
}

export function saveRecentSession(sessionId: string): void {
  if (typeof window === "undefined") return;
  try {
    const stored = localStorage.getItem("recentSessions");
    const recent: string[] = stored ? (JSON.parse(stored) as string[]) : [];
    const updated = [sessionId, ...recent.filter((id) => id !== sessionId)].slice(0, 8);
    localStorage.setItem("recentSessions", JSON.stringify(updated));
  } catch {
    /* ignore */
  }
}

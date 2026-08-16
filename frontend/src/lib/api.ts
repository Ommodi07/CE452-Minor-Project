import type {
  ApiError,
  HealthResponse,
  ResearchRequest,
  ResearchResponse,
  SessionCreateResponse,
  SessionResponse,
  StatusResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiClientError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as ApiError;
    return data.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const message = await parseError(response);
    throw new ApiClientError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function getStatus(): Promise<StatusResponse> {
  return request<StatusResponse>("/status");
}

export async function createSession(): Promise<SessionCreateResponse> {
  return request<SessionCreateResponse>("/sessions", { method: "POST" });
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return request<SessionResponse>(`/sessions/${sessionId}`);
}

export async function runResearch(body: ResearchRequest): Promise<ResearchResponse> {
  return request<ResearchResponse>("/research", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function checkStream(sessionId: string): Promise<{ available: boolean; detail?: string }> {
  const response = await fetch(`${API_URL}/stream/${sessionId}`);

  if (response.status === 501) {
    const data = (await response.json()) as ApiError;
    return { available: false, detail: data.detail };
  }

  if (!response.ok) {
    const message = await parseError(response);
    throw new ApiClientError(message, response.status);
  }

  return { available: true };
}

export function getExportUrl(sessionId: string): string {
  return `${API_URL}/research/${sessionId}/export`;
}

export async function downloadReport(sessionId: string): Promise<void> {
  const response = await fetch(getExportUrl(sessionId));

  if (!response.ok) {
    const message = await parseError(response);
    throw new ApiClientError(message, response.status);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `research-report-${sessionId}.docx`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export { ApiClientError, API_URL };

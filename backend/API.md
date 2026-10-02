# AI Research Analyst Backend API

Base URL:

```text
http://127.0.0.1:8000
```

Interactive documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Basic health check |
| POST | `/research` | Run a research query synchronously |
| GET | `/research/{job_id}/export` | Download a completed report as DOCX |
| POST | `/sessions` | Create a session |
| GET | `/sessions/{session_id}` | Retrieve a session |
| GET | `/status` | Check backend dependencies |
| GET | `/stream/{session_id}` | Server-sent progress and final report events |

## `GET /health`

Returns basic application health.

### Response `200`

```json
{
  "status": "ok",
  "app": "AI Research Analyst"
}
```

## `POST /research`

Runs the Planner -> Researcher -> Critic -> Writer graph synchronously and returns the completed report.

### Request body

```json
{
  "query": "Impact of remote work on urban housing markets",
  "session_id": "optional-existing-session-id",
  "max_iterations": 2
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `query` | string | Yes | Research question; minimum length is 1 |
| `session_id` | string or null | No | Client-supplied ID; generated automatically when omitted |
| `max_iterations` | integer or null | No | Maximum critic re-research loop count |

### Response `200`

```json
{
  "session_id": "abc123",
  "status": "completed",
  "report": {
    "id": "report-id",
    "session_id": "abc123",
    "title": "Research Report",
    "executive_summary": "Summary...",
    "sections": [
      {
        "heading": "Overview",
        "content": "Section content...",
        "cited_claim_ids": ["claim-id"]
      }
    ],
    "citations": {},
    "limitations": [],
    "generated_at": "2026-09-18T12:00:00",
    "markdown": "# Research Report..."
  },
  "open_questions": [],
  "errors": []
}
```

`report` is returned on every completed or fallback response. Use
`report_ready: true` as the frontend guard before rendering it. The graph's
internal `done` status is normalized to API status `completed`.

### `GET /stream/{session_id}`

Returns Server-Sent Events for a session. The frontend should listen for the
`complete` event and render `event.data.report.markdown` (or the structured
`report` fields) only when `report_ready` is `true`.

Events include:

```text
event: progress
data: {"session_id":"abc123","status":"completed","report_ready":true,"report":{...}}

event: complete
data: {"session_id":"abc123","status":"completed","report_ready":true,"report":{...}}
```

### Example

```powershell
curl.exe -X POST http://127.0.0.1:8000/research `
  -H "Content-Type: application/json" `
  -d '{"query":"Impact of remote work on urban housing markets"}'
```

### Status codes

- `200`: Research completed
- `422`: Invalid request body
- `500`: Research graph failed

## `GET /research/{job_id}/export`

Downloads a completed research report as a Microsoft Word `.docx` file.

### Path parameter

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | The `session_id` returned by `POST /research` |

### Response `200`

- Content type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- File name: `research-report-{job_id}.docx`

### Example

```powershell
curl.exe -OJ http://127.0.0.1:8000/research/abc123/export
```

### Status codes

- `200`: DOCX file returned
- `404`: Report not found
- `500`: DOCX generation failed

## `POST /sessions`

Creates an empty research session.

### Request body

None.

### Response `200`

```json
{
  "session_id": "abc123"
}
```

### Example

```powershell
curl.exe -X POST http://127.0.0.1:8000/sessions
```

## `GET /sessions/{session_id}`

Retrieves the saved state for a session.

### Response `200`

```json
{
  "session_id": "abc123",
  "state": {
    "session_id": "abc123",
    "status": "created"
  }
}
```

For a completed research run, `state` can contain the graph state, report, claims, sources, errors, and other run data.

### Example

```powershell
curl.exe http://127.0.0.1:8000/sessions/abc123
```

### Status codes

- `200`: Session found
- `404`: Session not found

## `GET /status`

Checks Gemini, PostgreSQL, Chroma, the report store, and the session store.

### Response `200`

```json
{
  "app_name": "AI Research Analyst",
  "environment": "development",
  "endpoints": [
    {
      "method": "GET",
      "path": "/health",
      "description": "Basic service health check.",
      "active": true
    }
  ],
  "connections": [
    {
      "name": "gemini_api",
      "active": true,
      "configured": true,
      "details": "Gemini API reachable."
    },
    {
      "name": "database",
      "active": true,
      "configured": true,
      "details": "Database connection is healthy."
    },
    {
      "name": "vector_store",
      "active": true,
      "configured": true,
      "details": "Vector store is ready."
    }
  ],
  "overall_ok": true
}
```

`overall_ok` is `false` if any dependency is unavailable or not configured.

### Example

```powershell
curl.exe http://127.0.0.1:8000/status
```

## `GET /stream/{session_id}`

This endpoint is currently a placeholder. Live graph streaming has not been implemented.

### Response `501`

```json
{
  "detail": "Streaming not yet implemented."
}
```

## Domain Objects

Research reports use these main objects:

- `Report`
- `ReportSection`
- `SourceDoc`
- `Claim`
- `VerifiedClaim`
- `citations`
- `limitations`
- `markdown`

The complete model definitions are in `app/models/schemas.py`.

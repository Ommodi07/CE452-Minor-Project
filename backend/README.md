# AI Research Analyst Backend

## 1. Problem Statement

Researching a topic manually is slow and difficult to verify. A researcher must
break a broad question into smaller questions, find information from multiple
sources, compare claims, identify missing evidence, and finally organize the
results into a readable report. Repeating these steps for every topic also makes
the process inconsistent and difficult to scale.

## 2. Proposed Solution

This project provides a FastAPI backend for an AI-assisted research analyst.
It uses a LangGraph workflow containing specialized agents:

1. **Planner** breaks the user's question into focused sub-questions.
2. **Researcher** searches the web, fetches relevant information, extracts
   sources and claims, and can store source embeddings in Chroma.
3. **Critic** reviews the collected evidence, identifies gaps, and requests
   targeted additional research when needed.
4. **Writer** combines the evidence into an executive summary, report sections,
   citations, and limitations.

The workflow is designed to improve research quality by using multiple research
tasks and a review loop instead of asking one model to produce an answer in a
single step. The loop has a configurable maximum iteration count so that a
request cannot run indefinitely.

## 3. Current Functionality

### Research workflow

- Runs the Planner -> Researcher(s) -> Critic -> Writer graph.
- Fans out research work across planned sub-questions and joins the results.
- Performs targeted re-research when the critic detects evidence gaps.
- Returns a structured report with a title, executive summary, sections,
  citations, limitations, and Markdown output.
- Uses Gemini as the primary LLM provider, with configuration for Groq.
- Uses DuckDuckGo search and web fetching tools for source collection.
- Supports Chroma source-document indexing and retrieval configuration.
- Returns a static fallback report when the live research providers fail.

### API and persistence

- `GET /health` provides a basic health check.
- `POST /research` runs a research request synchronously.
- `POST /sessions` creates a research session.
- `GET /sessions/{session_id}` retrieves saved session state.
- `GET /stream/{session_id}` sends Server-Sent Events while a saved result is
  being awaited.
- `GET /research/{job_id}/export` downloads a completed report as a DOCX file.
- `GET /status` checks the configuration and availability of major dependencies.
- Sessions and reports can be persisted through the configured stores.
- CORS is configured for a frontend running at `http://localhost:3000` by
  default.

### Workflow shape

```text
START -> planner -> researcher(s) -> critic -> writer -> END
                                      ^          |
                                      +----------+
                                  targeted retry
```

## 4. Setup and Usage

### Requirements

- Python 3.11 or newer
- A Gemini API key, or the configured alternative LLM provider
- PostgreSQL when database persistence is required
- Chroma storage when vector retrieval is required

### Installation

```bash
pip install -e ".[dev]"
```

Create a local environment file from `.env.example` and configure at least the
LLM credentials. Set `DATABASE_URL` and `CHROMA_PATH` when persistence and
vector storage are enabled.

Start the API with:

```bash
uvicorn app.main:app --reload
```

Useful documentation endpoints:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query":"Impact of remote work on urban housing markets"}'
```

The complete endpoint reference is available in [`API.md`](API.md).

## 5. Limitations of the Current Version

- The research endpoint waits for the complete graph run, so long-running
  requests can feel slow to clients.
- The streaming endpoint currently polls persisted session and report state. It
  does not yet expose true node-by-node LangGraph execution updates.
- LangGraph PostgreSQL checkpointing is not fully implemented, so interrupted
  runs cannot reliably resume from their previous graph state.
- Research quality depends on external LLM, search, and web-fetch providers.
  Provider outages, rate limits, blocked pages, and incomplete sources can
  reduce report quality.
- Source verification and claim comparison are still basic; the critic does
  not yet provide comprehensive cross-source fact checking.
- Chroma retrieval is available but is not yet used throughout the workflow as
  a strong evidence-retrieval layer.
- The fallback report informs the user that live research failed, but it is not
  a substitute for a research-backed report.
- There is no authentication, authorization, per-user quota, or tenant
  isolation in the current backend.
- Sessions and reports do not yet provide a complete lifecycle policy for
  cleanup, versioning, or multiple reports per session.
- Search results and generated content need human review before being used for
  academic, legal, medical, financial, or other high-impact decisions.

## 6. Planned Improvements

1. Implement a PostgreSQL-backed LangGraph checkpointer for resumable runs and
   reliable state inspection.
2. Replace synchronous research execution with background jobs and real
   `graph.astream()` progress events.
3. Improve critic behavior with cross-source claim verification, source
   credibility checks, contradiction detection, and stronger citation mapping.
4. Use Chroma retrieval more deeply to ground follow-up research and writing in
   the collected evidence.
5. Improve writer output with better section grouping, executive-summary
   synthesis, citation formatting, and duplicate-claim removal.
6. Add authentication, authorization, rate limiting, usage quotas, and
   per-user session isolation.
7. Add production observability, structured metrics, tracing, retry policies,
   and clearer provider error reporting.
8. Add report versioning, session cleanup, configurable retention, and support
   for multiple export formats such as PDF and Markdown files.
9. Expand automated tests for provider failures, persistence failures,
   concurrent sessions, streaming behavior, and end-to-end report quality.

## 7. Project Status

The current version is a functional backend prototype. The core graph executes
end to end and exposes research, persistence, status, streaming, and export
interfaces, but production hardening, stronger evidence verification, true
real-time progress, and secure multi-user operation remain future work.

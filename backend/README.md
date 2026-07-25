# AI Research Analyst — Backend Skeleton

FastAPI + LangGraph backend implementing the Planner → Researcher(s) → Critic → Writer
multi-agent flow described in the architecture doc.

## Status

This is a **wired-up backend**: the graph compiles, runs end-to-end, the
`/research` endpoint works, Gemini powers the agent LLM calls, PostgreSQL can
persist sessions/reports when configured, and Chroma can store source-doc
embeddings for retrieval.

## Run it

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in GEMINI_API_KEY, DATABASE_URL, and CHROMA_PATH
uvicorn app.main:app --reload
```

Then:

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "impact of remote work on urban housing markets"}'
```

## Graph shape

```
START -> planner -> (Send fan-out) -> researcher(s) -> critic
                                                           |
                                    (gaps? and iterations < max) --+--> writer -> END
                                             |
                                             +--> back to researcher (targeted retry)
```

Verify the compiled shape any time with:

```bash
python3 -c "from app.graph.graph import get_compiled_graph; print(get_compiled_graph().get_graph().draw_mermaid())"
```

## What's real vs. placeholder

| Piece | Status |
|---|---|
| `app/models/schemas.py` | Real — SubQuestion, SourceDoc, Claim, VerifiedClaim, Report |
| `app/graph/state.py` | Real — `GraphState` TypedDict with `operator.add` reducers on `source_docs`/`claims` |
| `app/graph/graph.py`, `routing.py` | Real — compiled graph, `Send` fan-out/fan-in, critic loop-back with iteration cap |
| `app/graph/nodes/*.py` | Real graph behavior, with fallback paths for missing config |
| `app/api/routes/research.py` | Real — synchronous `POST /research`, runs the graph to completion and persists results |
| `app/api/routes/stream.py` | Stub — 501, needs `graph.astream(..., stream_mode="updates")` + SSE |
| `app/api/routes/sessions.py` | Real basic session persistence |
| `app/tools/*`, `app/services/llm_client.py` | Gemini-backed LLM + DuckDuckGo search + Chroma indexing |
| `app/graph/checkpointer.py`, `app/db/*` | PostgreSQL-backed stores, with checkpointer still pending |

## Suggested next steps, in order

1. Add a Postgres-backed LangGraph checkpointer (`app/graph/checkpointer.py`) so runs are resumable by `session_id`.
2. Give `critic.py` real cross-source verification and richer Chroma retrieval usage.
3. Give `writer.py` real section grouping + executive summary synthesis.
4. Swap `/research` from synchronous `ainvoke` to `astream` + implement `stream.py`
   so the frontend graph-visualizer gets live node-by-node updates.

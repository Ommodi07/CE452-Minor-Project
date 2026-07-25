"""
Core domain models shared between the API layer and the LangGraph agent graph.

These are intentionally kept as plain Pydantic models (not tied to LangGraph
or FastAPI) so they can be imported anywhere: graph nodes, API responses,
DB repositories, and the frontend's generated TypeScript types.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class SubQuestionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ANSWERED = "answered"
    FAILED = "failed"


class ResearchAngle(str, Enum):
    """The analytical lens a sub-question approaches the parent query from.

    Used by the Planner to make sure the sub-question set covers genuinely
    different angles rather than 5 rephrasings of the same question.
    """

    FACTUAL = "factual"                     # core facts / definitions
    CURRENT_STATUS = "current_status"       # what's true right now / latest developments
    CAUSAL = "causal"                       # why did this happen / what's driving it
    COMPARATIVE = "comparative"             # how it compares to alternatives/precedents
    RISK_CONTROVERSY = "risk_controversy"   # what's disputed, risky, or criticized
    STAKEHOLDER = "stakeholder"             # who is affected / who holds which position
    FORECAST = "forecast"                   # what's likely to happen next


class ResearchMethod(str, Enum):
    """How the Researcher node should attempt to answer this sub-question."""

    WEB_SEARCH = "web_search"  # general web search is sufficient
    API = "api"                # a structured data source is more appropriate
    BOTH = "both"              # combine web search with a structured lookup


class SourceType(str, Enum):
    NEWS = "news"
    ACADEMIC = "academic"
    PRIMARY = "primary"
    BLOG = "blog"
    GOV = "gov"
    OTHER = "other"


class VerificationStatus(str, Enum):
    CORROBORATED = "corroborated"  # 2+ independent sources agree
    DISPUTED = "disputed"          # sources conflict
    UNVERIFIED = "unverified"      # single source only, or no LLM available to cross-check


class SubQuestion(BaseModel):
    id: str = Field(default_factory=_new_id)
    parent_query: str
    question_text: str
    rationale: str = ""
    angle: ResearchAngle = ResearchAngle.FACTUAL
    research_method: ResearchMethod = ResearchMethod.WEB_SEARCH
    priority: int = 1
    status: SubQuestionStatus = SubQuestionStatus.PENDING
    # Set by the Critic's reflection step when initial results were too thin
    # (too many Unverified/Disputed claims). When present, Researcher uses
    # this as the actual search query instead of `question_text` — the
    # sub-question's meaning/angle doesn't change, just the search phrasing.
    refined_query: Optional[str] = None
    # Set by the Critic's reflection loop when a follow-up Researcher pass is
    # triggered (too many Unverified/Disputed claims, or zero claims at all).
    # `question_text` stays stable (it's what the Critic's loop-back routing
    # matches on); this is what the Researcher actually searches for on retry.
    refined_query: Optional[str] = None


class SourceDoc(BaseModel):
    id: str = Field(default_factory=_new_id)
    sub_question_id: str
    url: str
    title: str
    snippet: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    source_type: SourceType = SourceType.OTHER
    credibility_score: Optional[float] = None
    # Pointer to full text in a vector store / blob store. Full content is
    # deliberately NOT inlined here to keep graph state (and checkpoints) small.
    content_ref: Optional[str] = None

    # --- source-quality metadata (populated by app/tools/quality.py) ---
    author: Optional[str] = None
    published_date: Optional[str] = None  # freeform (e.g. "April 30, 2025" or "6 days ago") — search
    # results don't return a normalized ISO date, so this is kept as-received rather than parsed.
    quality_flags: list[str] = Field(default_factory=list)  # e.g. "no_date", "content_farm_domain",
    # "author_unknown" — see app/tools/quality.py for what triggers each and why.


class Claim(BaseModel):
    id: str = Field(default_factory=_new_id)
    source_doc_id: str
    sub_question_id: str
    claim_text: str
    confidence: float = 0.5
    supporting_excerpt: str = ""


class VerifiedClaim(Claim):
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    corroborating_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    critic_notes: str = ""
    adjusted_confidence: float = 0.5


class ReportSection(BaseModel):
    heading: str
    content: str
    cited_claim_ids: list[str] = Field(default_factory=list)


class Report(BaseModel):
    id: str = Field(default_factory=_new_id)
    session_id: str
    title: str
    executive_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    citations: dict[str, SourceDoc] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    # Fully assembled markdown document (title, exec summary, sections with
    # inline [N] citation markers, limitations, and a References list) — see
    # app/graph/nodes/writer.py. `sections`/`citations` above stay structured
    # for consumers that want programmatic access (e.g. a citation hover
    # card in the frontend); `markdown` is the render-ready deliverable.
    markdown: str = ""

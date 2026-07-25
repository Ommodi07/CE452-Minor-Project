"""Basic source-quality flagging for a SourceDoc.

Honest about what's actually detectable today:
    - `no_date`             — real signal, derived from the search tool's
                                                        `page_age` field.
    - `content_farm_domain` — real signal, matched against a small illustrative
                                                        domain list (extend `CONTENT_FARM_DOMAINS` for
                                                        your use case — this is not a comprehensive list).
    - `author_unknown`      — search snippets often omit author metadata, so we
                                                        flag that gap explicitly rather than assuming it is present.
"""
from __future__ import annotations

from urllib.parse import urlparse

from app.models.schemas import SourceDoc, SourceType

# Illustrative only — not comprehensive. Add domains relevant to your domain/language.
CONTENT_FARM_DOMAINS = {
    "answers.com",
    "ask.com",
    "chacha.com",
    "ehow.com",
    "quora.com",  # crowd-sourced, no editorial vetting, effectively no fixed author
}

_NO_DATE_PENALTY = 0.15
_AUTHOR_UNKNOWN_PENALTY = 0.10
_CONTENT_FARM_PENALTY = 0.40
_HIGH_TRUST_SOURCE_BOOST = 0.10  # GOV / ACADEMIC

_MIN_SCORE = 0.05
_MAX_SCORE = 1.0


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


_domain_of = domain_of  # internal alias, kept for readability at call sites below


def assess_source_quality(doc: SourceDoc) -> tuple[list[str], float]:
    """
    Return (quality_flags, credibility_score) for `doc`. Does not mutate
    `doc` — caller applies the result (see researcher_node).
    """
    flags: list[str] = []
    domain = _domain_of(doc.url)

    if not doc.published_date:
        flags.append("no_date")

    # See module docstring: this always fires today, it's a tooling gap, not
    # a per-source finding.
    flags.append("author_unknown")

    if any(domain == d or domain.endswith(f".{d}") for d in CONTENT_FARM_DOMAINS):
        flags.append("content_farm_domain")

    score = _MAX_SCORE
    if "no_date" in flags:
        score -= _NO_DATE_PENALTY
    if "author_unknown" in flags:
        score -= _AUTHOR_UNKNOWN_PENALTY
    if "content_farm_domain" in flags:
        score -= _CONTENT_FARM_PENALTY
    if doc.source_type in (SourceType.GOV, SourceType.ACADEMIC):
        score += _HIGH_TRUST_SOURCE_BOOST

    score = round(max(_MIN_SCORE, min(_MAX_SCORE, score)), 2)
    return flags, score

"""
Deduplication for a single Researcher invocation's gathered SourceDocs.

Two passes:
  1. Exact-URL dedup after normalization (strip tracking params, www.,
     trailing slash, fragment, scheme case) — catches the same page
     appearing twice with cosmetically different URLs.
  2. Near-identical *content* dedup via snippet similarity — catches
     syndicated/mirrored content at genuinely different URLs (e.g. the same
     wire story republished by two outlets).

Scope note: this only dedupes within the docs a single Researcher
invocation gathered for one sub-question. Because Researcher runs fanned
out in parallel (one invocation per sub-question), it can't see what other
branches found — so the same source showing up under two different
sub-questions won't be caught here. That's a natural fit for a dedup pass
at Critic-time instead, once all branches have merged into shared state.
"""
from __future__ import annotations

import difflib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.models.schemas import SourceDoc

_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAMS = {
    "fbclid", "gclid", "gclsrc", "mc_cid", "mc_eid", "ref", "ref_src",
    "igshid", "spm", "cmpid", "icid",
}

CONTENT_SIMILARITY_THRESHOLD = 0.85
_MIN_SNIPPET_LEN_FOR_SIMILARITY_CHECK = 20


def normalize_url(url: str) -> str:
    """
    Normalize a URL for equality comparison: lowercase scheme/host, strip
    'www.', drop the fragment, drop tracking query params, sort remaining
    params, and strip a trailing slash from the path.
    """
    parsed = urlparse(url.strip())
    scheme = "https"  # treat http/https as equivalent for dedup purposes
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[len("www."):]

    path = parsed.path.rstrip("/") or "/"

    kept_params = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith(_TRACKING_PARAM_PREFIXES)
    ]
    kept_params.sort()
    query = urlencode(kept_params)

    return urlunparse((scheme, host, path, "", query, ""))


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def content_similarity(a: str, b: str) -> float:
    """Ratio in [0, 1]; 1.0 means identical (after whitespace/case normalization)."""
    return difflib.SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


def _richer(a: SourceDoc, b: SourceDoc) -> SourceDoc:
    """Pick whichever doc carries more usable signal, preferring a longer snippet."""
    return a if len(a.snippet) >= len(b.snippet) else b


def dedupe_source_docs(
    docs: list[SourceDoc], similarity_threshold: float = CONTENT_SIMILARITY_THRESHOLD
) -> list[SourceDoc]:
    """
    Return `docs` with exact-URL and near-identical-content duplicates
    removed, preferring to keep whichever duplicate has the richer snippet.
    Order of remaining docs follows first-occurrence order in the input.
    """
    # Pass 1: exact-URL dedup (after normalization).
    by_normalized_url: dict[str, SourceDoc] = {}
    order: list[str] = []
    for doc in docs:
        key = normalize_url(doc.url)
        if key in by_normalized_url:
            by_normalized_url[key] = _richer(by_normalized_url[key], doc)
        else:
            by_normalized_url[key] = doc
            order.append(key)
    url_deduped = [by_normalized_url[key] for key in order]

    # Pass 2: near-identical content dedup across the remaining distinct URLs.
    kept: list[SourceDoc] = []
    for doc in url_deduped:
        duplicate_of_index = None
        if len(doc.snippet) >= _MIN_SNIPPET_LEN_FOR_SIMILARITY_CHECK:
            for i, existing in enumerate(kept):
                if len(existing.snippet) < _MIN_SNIPPET_LEN_FOR_SIMILARITY_CHECK:
                    continue
                if content_similarity(doc.snippet, existing.snippet) >= similarity_threshold:
                    duplicate_of_index = i
                    break

        if duplicate_of_index is None:
            kept.append(doc)
        else:
            kept[duplicate_of_index] = _richer(kept[duplicate_of_index], doc)

    return kept

from app.models.schemas import SourceDoc
from app.tools.dedup import content_similarity, dedupe_source_docs, normalize_url


def _doc(url: str, snippet: str = "", sub_question_id: str = "sq1", title: str = "T") -> SourceDoc:
    return SourceDoc(sub_question_id=sub_question_id, url=url, title=title, snippet=snippet)


def test_normalize_url_treats_scheme_www_and_trailing_slash_as_equivalent():
    assert normalize_url("https://www.Example.com/page/") == normalize_url("http://example.com/page")


def test_normalize_url_strips_tracking_params_but_keeps_meaningful_ones():
    tracked = "https://example.com/article?utm_source=twitter&utm_campaign=x&fbclid=abc&id=42"
    clean = "https://example.com/article?id=42"
    assert normalize_url(tracked) == normalize_url(clean)


def test_normalize_url_strips_fragment():
    assert normalize_url("https://example.com/page#section-2") == normalize_url("https://example.com/page")


def test_normalize_url_distinguishes_genuinely_different_pages():
    assert normalize_url("https://example.com/page-a") != normalize_url("https://example.com/page-b")


def test_content_similarity_identical_text_is_1():
    assert content_similarity("The sky is blue today.", "the sky is blue today.") == 1.0


def test_content_similarity_unrelated_text_is_low():
    assert content_similarity("The sky is blue today.", "Interest rates rose in March.") < 0.4


def test_dedupe_removes_exact_url_duplicates_with_cosmetic_differences():
    docs = [
        _doc("https://example.com/story", snippet="Short."),
        _doc("https://www.example.com/story/?utm_source=newsletter", snippet="A longer, richer snippet here."),
    ]
    result = dedupe_source_docs(docs)
    assert len(result) == 1
    # richer (longer) snippet should be the one kept
    assert result[0].snippet == "A longer, richer snippet here."


def test_dedupe_removes_near_identical_content_at_different_urls():
    shared_text = (
        "The central bank raised interest rates by half a percentage point on Tuesday, "
        "citing persistent inflation pressures across the economy."
    )
    docs = [
        _doc("https://outlet-a.com/wire-story", snippet=shared_text),
        _doc("https://outlet-b.com/syndicated-copy", snippet=shared_text.upper()),
    ]
    result = dedupe_source_docs(docs)
    assert len(result) == 1


def test_dedupe_keeps_genuinely_distinct_sources():
    docs = [
        _doc("https://example.com/a", snippet="X increased by 10 percent in the first quarter of 2026."),
        _doc("https://example.org/b", snippet="Analysts expect further growth in the housing sector next year."),
    ]
    result = dedupe_source_docs(docs)
    assert len(result) == 2


def test_dedupe_skips_similarity_check_for_very_short_snippets():
    # Short snippets like "N/A" or "42%" shouldn't get flagged as duplicates
    # of each other just because they're short and share characters.
    docs = [
        _doc("https://example.com/a", snippet="42%"),
        _doc("https://example.com/b", snippet="43%"),
    ]
    result = dedupe_source_docs(docs)
    assert len(result) == 2

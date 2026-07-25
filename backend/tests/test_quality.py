from app.models.schemas import SourceDoc, SourceType
from app.tools.quality import assess_source_quality


def _doc(url: str, source_type: SourceType = SourceType.OTHER, published_date: str | None = None) -> SourceDoc:
    return SourceDoc(
        sub_question_id="sq1",
        url=url,
        title="T",
        snippet="some content",
        source_type=source_type,
        published_date=published_date,
    )


def test_missing_date_is_flagged():
    flags, _ = assess_source_quality(_doc("https://example.com/a", published_date=None))
    assert "no_date" in flags


def test_present_date_is_not_flagged():
    flags, _ = assess_source_quality(_doc("https://example.com/a", published_date="April 30, 2025"))
    assert "no_date" not in flags


def test_author_unknown_always_present_today():
    # See app/tools/quality.py docstring: this is a structural gap (no
    # byline data available from the search tool), not a per-source finding.
    flags, _ = assess_source_quality(_doc("https://example.com/a", published_date="today"))
    assert "author_unknown" in flags


def test_content_farm_domain_is_flagged():
    flags, _ = assess_source_quality(_doc("https://www.quora.com/some-question"))
    assert "content_farm_domain" in flags


def test_non_content_farm_domain_is_not_flagged():
    flags, _ = assess_source_quality(_doc("https://reuters.com/some-article"))
    assert "content_farm_domain" not in flags


def test_content_farm_score_is_lower_than_ordinary_source():
    _, farm_score = assess_source_quality(_doc("https://quora.com/x", published_date="today"))
    _, ordinary_score = assess_source_quality(_doc("https://example.com/x", published_date="today"))
    assert farm_score < ordinary_score


def test_gov_and_academic_sources_get_a_boost():
    _, other_score = assess_source_quality(
        _doc("https://example.com/x", source_type=SourceType.OTHER, published_date="today")
    )
    _, gov_score = assess_source_quality(
        _doc("https://example.gov/x", source_type=SourceType.GOV, published_date="today")
    )
    assert gov_score > other_score


def test_score_is_clamped_between_min_and_max():
    flags, score = assess_source_quality(_doc("https://quora.com/x"))  # no date + author_unknown + content farm
    assert 0.05 <= score <= 1.0


def test_worst_case_stacks_all_penalties_but_stays_above_floor():
    _, score = assess_source_quality(_doc("https://quora.com/x", published_date=None))
    assert score >= 0.05

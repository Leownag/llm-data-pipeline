import pytest

from conftest import FIXTURES
from pipeline import clean_text, heuristic_quality_filter, html_to_text


def test_drops_paragraphs_without_punctuation():
    assert clean_text("no punctuation here\nkeep this one.") == "keep this one."


def test_drops_paragraphs_with_very_long_alnum_runs():
    assert clean_text("keep this one.\n" + "a" * 101 + ".") == "keep this one."


def test_keeps_a_run_of_exactly_100():
    assert clean_text("a" * 100 + ".") == "a" * 100 + "."


@pytest.mark.parametrize("text,kept", [
    ("A normal, readable sentence.", True),
    ("No punctuation at all", False),
    ("   ", False),
    ("", False),
])
def test_document_level_filter(text, kept):
    assert heuristic_quality_filter(text) is kept


def test_rejects_single_word_bad_words():
    assert heuristic_quality_filter("This page is about anal sex.") is False


def test_bad_word_match_is_token_exact():
    # "anal" must not match inside "analysis", or the filter would eat ordinary prose.
    assert heuristic_quality_filter("A careful analysis of the data.") is True


def test_rejects_low_alphanumeric_ratio():
    assert heuristic_quality_filter("±≠≈∞§¶•ªº–≠œ∑´®†¥¨ˆøπ. ") is False


@pytest.mark.xfail(strict=True, reason="Known language bias: the punctuation tests are ASCII-only, "
                                       "so CJK text punctuated with full-width marks is rejected. "
                                       "Documented in docs/findings.md.")
def test_cjk_fullwidth_punctuation_survives():
    text = html_to_text((FIXTURES / "cjk_fullwidth.html").read_text())
    assert clean_text(text) != ""
    assert heuristic_quality_filter(clean_text(text)) is True


def test_pii_masks_collide_with_the_bad_word_list():
    """replace_pii emits XXX, and "xx"/"xxx" are both in bad_word_list.txt.

    Masking a document therefore makes it fail the quality filter, so running the stages
    in the order clean -> mask -> filter silently deletes every document containing a US
    phone number or an SSN. cli.py and mini_ccc.py filter before masking to avoid this.
    """
    from pipeline import replace_pii

    original = "Call +1 425 555 1234 to reach us, please."
    assert heuristic_quality_filter(original) is True
    assert heuristic_quality_filter(replace_pii(original)) is False

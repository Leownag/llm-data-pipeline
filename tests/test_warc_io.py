from conftest import FIXTURES
from pipeline import clean_text, heuristic_quality_filter, html_to_text, replace_pii
from warc_io import read_warc_file

MINI_WARC = str(FIXTURES / "mini.warc")


def test_only_exact_text_html_is_yielded():
    # The shard census hinges on this: read_warc_file compares Content-Type for string
    # equality, so "text/html; charset=utf-8" is skipped. See docs/findings.md.
    urls = [url for url, _ in read_warc_file(MINI_WARC)]
    assert urls == ["http://example.com/plain", "http://example.com/pii"]


def test_num_to_read_limits_the_stream():
    assert len(list(read_warc_file(MINI_WARC, 1))) == 1


def test_end_to_end_pipeline_over_a_shard():
    # Quality is judged before masking; see test_quality.py for why the order matters.
    results = {}
    for url, html in read_warc_file(MINI_WARC):
        cleaned = clean_text(html_to_text(html))
        results[url] = (replace_pii(cleaned), heuristic_quality_filter(cleaned))

    plain, plain_kept = results["http://example.com/plain"]
    # The <title> "Plain" is extracted but then dropped by clean_text, which deletes
    # punctuation-free paragraphs -- which is why most headings do not survive either.
    assert plain == "A short, readable sentence." and plain_kept is True

    pii, pii_kept = results["http://example.com/pii"]
    assert "123-45-6789" not in pii and "425 555 1234" not in pii
    assert "SSN XXX-XX-XXXX" in pii and pii_kept is True

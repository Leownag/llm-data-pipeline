from conftest import FIXTURES
from pipeline import html_to_text

SOURCE = (FIXTURES / "revenue_table.html").read_text()


def test_matches_golden_output():
    expected = (FIXTURES / "revenue_table.expected.txt").read_text().rstrip("\n")
    assert html_to_text(SOURCE) == expected


def test_title_is_prepended():
    assert html_to_text(SOURCE).startswith("Revenue\nQuarterly Revenue")


def test_script_style_and_comments_are_dropped():
    out = html_to_text(SOURCE)
    for noise in ("color:red", "var a=1", "internal note"):
        assert noise not in out


def test_image_alt_text_is_lost():
    # Documented limitation: alt text is a genuine natural-language description and we discard it.
    assert "Acme Corp logo" not in html_to_text(SOURCE)


def test_table_cells_are_tab_joined_per_row():
    assert "Region\tQ1\tQ2" in html_to_text(SOURCE)
    assert "EMEA\t1.2\t1.9" in html_to_text(SOURCE)


def test_headings_lose_their_level():
    out = html_to_text(SOURCE)
    assert "Quarterly Revenue" in out and "By region" in out
    assert "#" not in out


def test_pre_block_loses_indentation():
    # Whitespace-sensitive code no longer parses after extraction; this pins the known loss.
    assert "def total(rows):\ns = 0" in html_to_text(SOURCE)


def test_inline_tags_do_not_split_a_sentence():
    assert "Fetch it with requests.get(url)." in html_to_text(SOURCE)


def test_accepts_bytes_repr_from_warc_reader():
    assert html_to_text(str(b"<html><body><p>Hi there.</p></body></html>")) == "Hi there."


def test_empty_input():
    assert html_to_text("") == ""

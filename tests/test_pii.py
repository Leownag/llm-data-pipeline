import pytest

from pipeline import replace_pii


@pytest.mark.parametrize("text,expected", [
    ("SSN 123-45-6789 here", "SSN XXX-XX-XXXX here"),
    ("call +1 425 555 1234 now", "call +1 XXX XXX XXXX now"),
    ("call +1 (425) 555-1234 now", "call +1 (XXX) XXX-XXXX now"),
    ("call +1.425.555.1234 now", "call +1.XXX.XXX.XXXX now"),
])
def test_masks_pii(text, expected):
    assert replace_pii(text) == expected


@pytest.mark.parametrize("text", [
    "order 1234-56-7890 shipped",   # wrong digit grouping for an SSN
    "call 425 555 1234 now",        # no +1 country code
    "nothing sensitive at all",
])
def test_leaves_other_text_alone(text):
    assert replace_pii(text) == text


def test_separator_style_is_preserved():
    assert replace_pii("+1-425-555-1234") == "+1-XXX-XXX-XXXX"

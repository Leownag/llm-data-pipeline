import ast
import re
from pathlib import Path
from typing import Set, Dict
import string
from bs4 import BeautifulSoup

_BAD_WORD_PATH = Path(__file__).parent / 'data' / 'bad_word_list.txt'
_BAD_WORDS = None
_NON_ALNUM_SPLIT = re.compile(r"[^a-z0-9]+")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\+1[\s.\-()]*(?:\d[\s.\-()]*){10}")
_LONG_RUN_RE = re.compile(r"[A-Za-z0-9]{101,}")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_PUNCT = set(string.punctuation)
_SKIP_TAGS = ("script", "style", "noscript", "template", "svg", "head")
_BLOCK_TAGS = (
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "tbody", "thead", "tr", "ul",
)


def retrieve_bad_words() -> set[str]:
    """Helper function - that reads a list of bad words from a file and returns them as a set.
    Returns:
        Set[str]: A set containing lowercase bad words.
    """
    with open(_BAD_WORD_PATH, 'r') as file:
        records = file.read().strip().split('\n')
        bad_words = [record.lower() for record in records]
        return set(bad_words)


def html_to_text(html: str) -> str:
    """Converts HTML content to plain text..
    Args:
        html (bytes): HTML content as bytes.
    Returns:
        str: Plain text extracted from HTML.
    """
    if isinstance(html, str) and html[:2] in ("b'", 'b"'):
        # read_warc_file yields bytes; callers that wrap it in str() hand us a bytes repr.
        try:
            html = ast.literal_eval(html)
        except (ValueError, SyntaxError):
            pass
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(list(_SKIP_TAGS)):
        tag.decompose()

    # Break lines only at block-level boundaries; inline tags must not split a sentence.
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")
    for cell in soup.find_all(("td", "th")):
        cell.insert_after("\t")
    text = soup.get_text(separator="")

    lines = [
        "\t".join(" ".join(cell.split()) for cell in line.split("\t")).strip()
        for line in text.split("\n")
    ]
    body = _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()
    return f"{title}\n{body}".strip() if title else body


def replace_pii(text: str) -> str:
    """Masks personally identifiable information (PII) from text with the specified masking formats.
    Args:
        text (str): Candidate text.
    Returns:
        str: Text with PII obfuscated.
    """
    def mask_phone(match: re.Match) -> str:
        return "+1" + re.sub(r"\d", "X", match.group(0)[2:])

    text = _SSN_RE.sub("XXX-XX-XXXX", text)
    return _PHONE_RE.sub(mask_phone, text)

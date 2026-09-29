"""Measure the WARC shard: Content-Type breakdown, tag structure, and filter rates.

Writes results/shard-census.json. Reproduces every number quoted in docs/findings.md.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from warcio.archiveiterator import ArchiveIterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import clean_text, heuristic_quality_filter, html_to_text, replace_pii  # noqa: E402
from warc_io import read_warc_file  # noqa: E402

TAGS = {
    "table": re.compile(rb"<table[\s>]", re.I),
    "th": re.compile(rb"<th[\s>]", re.I),
    "pre": re.compile(rb"<pre[\s>]", re.I),
    "code": re.compile(rb"<code[\s>]", re.I),
    "select": re.compile(rb"<select[\s>]", re.I),
    "img_alt": re.compile(rb"<img[^>]+alt=", re.I),
    "h1": re.compile(rb"<h1[\s>]", re.I),
}


def content_type_census(path: str) -> dict:
    kinds, types = Counter(), Counter()
    with open(path, "rb") as stream:
        for record in ArchiveIterator(stream):
            kinds[record.rec_type] += 1
            if record.rec_type == "response":
                types[record.http_headers.get_header("Content-Type")] += 1
    html_star = sum(n for ct, n in types.items() if ct and ct.lower().startswith("text/html"))
    return {
        "record_types": dict(kinds),
        "response_records": kinds["response"],
        "no_content_type": types[None],
        "text_html_star": html_star,
        "exactly_text_html": types["text/html"],
        "distinct_content_types": len(types),
        "top_content_types": types.most_common(8),
    }


def pipeline_census(path: str, limit: int | None) -> dict:
    tags, seen = Counter(), 0
    kept_mask_first = kept_filter_first = 0
    started = time.monotonic()

    for _url, html in read_warc_file(path, limit):
        seen += 1
        for name, pattern in TAGS.items():
            if pattern.search(html):
                tags[name] += 1

        cleaned = clean_text(html_to_text(html))
        # Shipped order: mask, then filter. The mask emits "XXX", which is itself in the
        # bad-word list, so every document holding a phone number or SSN is thrown away.
        kept_mask_first += heuristic_quality_filter(replace_pii(cleaned))
        # Corrected order: judge quality on the unmasked text, then mask what survives.
        kept_filter_first += heuristic_quality_filter(cleaned)

    return {
        "records": seen,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "tag_frequency": {k: [tags[k], round(100 * tags[k] / seen, 1)] for k in TAGS},
        "mask_then_filter": {
            "kept": kept_mask_first,
            "deleted": seen - kept_mask_first,
            "deleted_pct": round(100 * (seen - kept_mask_first) / seen, 2),
        },
        "filter_then_mask": {
            "kept": kept_filter_first,
            "deleted": seen - kept_filter_first,
            "deleted_pct": round(100 * (seen - kept_filter_first) / seen, 2),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fname", required=True, help="Path to the WARC shard.")
    parser.add_argument("--num_records", type=int, default=None, help="Limit for a quick run.")
    parser.add_argument("--skip_content_types", action="store_true",
                        help="Skip the full-archive Content-Type pass.")
    parser.add_argument("--out", default="results/shard-census.json")
    args = parser.parse_args()

    census = {"shard": Path(args.fname).name}
    if not args.skip_content_types:
        census["content_types"] = content_type_census(args.fname)
    census["pipeline"] = pipeline_census(args.fname, args.num_records)

    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(census, indent=2) + "\n")
    print(json.dumps(census, indent=2))


if __name__ == "__main__":
    main()

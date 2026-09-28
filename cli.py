"""Command-line entry point for the CommonCrawl cleaning pipeline."""
import argparse
import json

from pipeline import (
    clean_text,
    deduplicate_texts,
    heuristic_quality_filter,
    html_to_text,
    replace_pii,
)
from warc_io import read_warc_file, read_wet_file


def run_warc(path: str, num_records: int, quiet: bool) -> None:
    seen = passes = 0
    for url, html in read_warc_file(path, num_records):
        seen += 1
        cleaned = clean_text(html_to_text(html))
        # Quality first: replace_pii emits "XXX", which is itself in the bad-word list.
        kept = heuristic_quality_filter(cleaned)
        text = replace_pii(cleaned)
        passes += kept
        if not quiet:
            print(url)
            print("Passes heuristic quality filter:", kept)
            if kept:
                print(text, end="\n\n\n")
    print(f"{passes} passed out of {seen} records processed.")
    if seen:
        print(f"{seen - passes} documents deleted ({100 * (seen - passes) / seen:.2f}%).")


def run_count(path: str) -> None:
    print(f"{sum(1 for _ in read_warc_file(path, None))} HTML pages in {path}")


def run_wet(path: str, num_records: int) -> None:
    for url, text in read_wet_file(path, num_records):
        print(url)
        print(text.decode("utf-8", errors="replace"), end="\n\n\n")


def run_dedup(path: str) -> None:
    with open(path) as f:
        texts = [item["text"] for item in json.load(f)["data"]]
    kept = deduplicate_texts(texts)
    print(f"{len(texts)} sentences in, {len(kept)} kept, {len(texts) - len(kept)} removed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fname", default="", help="Path to a WARC file.")
    parser.add_argument("--wet_name", default="", help="Path to a WET file.")
    parser.add_argument("--dfname", default="", help="Path to topic_dataset.json.")
    parser.add_argument("--num_records", type=int, default=30, help="Records to parse (debugging).")
    parser.add_argument("--count_only", action="store_true", help="Only count HTML pages in the shard.")
    parser.add_argument("--quiet", action="store_true", help="Print summary counts only.")
    args = parser.parse_args()

    if args.fname and args.count_only:
        run_count(args.fname)
    elif args.fname:
        run_warc(args.fname, args.num_records, args.quiet)
    if args.wet_name:
        run_wet(args.wet_name, args.num_records)
    if args.dfname:
        run_dedup(args.dfname)
    if not (args.fname or args.wet_name or args.dfname):
        parser.print_help()


if __name__ == "__main__":
    main()

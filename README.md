# llm-data-pipeline

A pre-training data pipeline for web text: take a raw Common Crawl WARC shard, turn HTML into
plain text, mask personal information, drop low-quality documents, remove near-duplicates, and
expose the result as a HuggingFace dataset.

Run end to end on one shard of `CC-MAIN-2018-17` — 3.7 GB, 48,572 records.

```
WARC shard ──▶ html_to_text ──▶ clean_text ──▶ heuristic_quality_filter ──▶ replace_pii ──▶ dataset
                                                          │
                              topic corpus ──▶ deduplicate_texts
```

## What came out of it

| | |
|---|---|
| Records in the shard | 48,572 responses, 6,368 reachable as exactly `text/html` |
| Dropped by the quality filter | see [`docs/findings.md`](docs/findings.md) |
| Near-duplicates removed | 31 of 219 (a naive exact-match baseline finds ~20) |
| Throughput | 0.058 s/document — ~5.5 years single-process for all of Common Crawl |
| Tests | 38 passing, 1 `xfail` that pins a known language bias |

Three findings worth more than the throughput number:

**The PII mask makes documents fail the quality filter.** `replace_pii` writes `XXX`, and both
`xx` and `xxx` are entries in the bad-word list. Mask before you filter and every document
containing a US phone number or an SSN is silently deleted — for containing a bad word it did
not contain a moment earlier. The pipeline filters first and masks second; there is a regression
test for it.

**The quality filter is biased in two directions at once.** The 80% character-class test is
Unicode-aware and treats kana and Cyrillic fairly, but the punctuation tests use ASCII-only
`string.punctuation`, so CJK text punctuated with full-width marks is rejected outright.
Meanwhile the bad-word list is English-only, so non-English adult content is *under*-filtered.
Same filter, opposite failures, depending on the language.

**84% of pages carry `alt` text and none of it survives.** Extraction keeps what is cheap to keep.
`docs/findings.md` has the full census of what gets lost — tables keep their reading order but
lose their structure, code loses its indentation, and 61.3% of pages have their `<h1>` deleted two
stages later because headings rarely contain punctuation.

## Try it

```bash
pip install -r requirements.txt
pytest tests -v                                    # no download needed
python cli.py --dfname data/topic_dataset.json     # 219 in, 188 kept, 31 removed
```

On the real shard:

```bash
bash scripts/download_data.sh                      # ~5.5 GB of WARC/WET/WAT
python cli.py --fname data.warc --count_only
python cli.py --fname data.warc --num_records 30
python scripts/census.py --fname data.warc         # writes results/shard-census.json
python mini_ccc.py                                 # builds the HuggingFace dataset
```

## Layout

```
pipeline.py        extraction, masking, filtering, deduplication
cli.py             command-line entry point
warc_io.py         WARC/WET readers (course-provided -- see NOTICE)
mini_ccc.py        HuggingFace GeneratorBasedBuilder over the cleaned shard
scripts/census.py  Content-Type and tag-structure census; measures both stage orders
tests/             pytest suite; fixtures/mini.warc is a 2 KB synthetic shard
docs/findings.md   what was measured, and what it means
docs/evidence.md   the fixtures and real pages behind each claim
```

The test suite never touches the 3.7 GB download. `tests/fixtures/mini.warc` is a synthetic
four-record shard — two `text/html`, one `text/html; charset=utf-8`, one `image/jpeg` — which is
enough to exercise the reader's strict Content-Type matching and run the whole pipeline end to
end in under a tenth of a second.

## Design notes

**Extraction breaks lines at block boundaries only.** Inline tags must not split a sentence, so
`<p>Fetch it with <code>requests.get(url)</code>.</p>` comes out as one line while `<div>` and
`<li>` each start a new one. Table cells are tab-joined per `<tr>`.

**Deduplication uses an inverted shingle index.** Jaccard over word trigrams at threshold 0.6,
but each document is only compared against candidates sharing at least one trigram, instead of
against everything kept so far. The threshold being 0.6 rather than 1.0 is exactly why this must
never be used as a filesystem deduplicator — see `docs/findings.md` §5.

**`read_warc_file` matches `Content-Type` by string equality.** This is course-provided and left
as-is, but it is why 34,661 records served as `text/html; charset=utf-8` never reach the
pipeline. Worth knowing before comparing these numbers against anyone else's.

## Provenance

Built for INFO7375 (Semantic Intelligence in Large Language Models) at Northeastern University.
Reorganised from the original single-directory assignment layout; the commit history was
reconstructed from file modification times rather than kept live during development.

The written portions of the assignment that were literature review — comparing published dataset
documentation and model cards — are not part of this repository. What is here is the code, the
measurements it produced, and the analysis of those measurements.

See [`NOTICE`](NOTICE) for which files were provided by the course.

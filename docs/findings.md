# Findings

Everything here was measured on a single WARC shard of the `CC-MAIN-2018-17` Common Crawl dump
(`CC-MAIN-20180420081400-20180420101400-00000`, 3.7 GB uncompressed). Reproduce with:

```bash
bash scripts/download_data.sh
python scripts/census.py --fname data.warc
```

which writes `results/shard-census.json`.

## 1. What is actually in the shard

| | count |
|---|---|
| `response` records | 48,572 |
| served as `text/html*` | 47,839 |
| served as exactly `text/html` | 6,368 |
| distinct `Content-Type` values | 208 |

The gap between 47,839 and 6,368 matters. `read_warc_file` compares the `Content-Type` header
for **string equality** against `"text/html"`, so `text/html; charset=UTF-8` — 21,870 records,
by far the most common value — never reaches the pipeline. Every number below is over the 6,368
records the reader actually yields, not over the shard as a whole.

## 2. What extraction loses

Measured over all 6,368 records:

| element | pages containing it |
|---|---|
| `<table>` | 55.3% |
| `<select>` | 22.2% |
| `<th>` | 10.3% |
| `<pre>` | 1.6% |
| `<code>` | 0.6% |
| `<img alt=>` | 84.0% |
| `<h1>` | 61.3% |

- **Tables survive as content but lose their structure.** One line per `<tr>`, cells joined by
  tabs. Reading order is preserved; the link between a header cell and the column under it is not.
- **Code loses its indentation.** Whitespace is normalised within each line, so a `<pre><code>`
  Python block comes out syntactically invalid. Nothing marks the block as code.
- **Headings lose their level.** `<h1>`–`<h6>` become ordinary lines. Since headings rarely
  contain punctuation, `clean_text` then deletes most of them — so 61.3% of pages have their
  `<h1>` silently removed two stages later.
- **`alt` text is discarded entirely.** 84.0% of pages carry an `img alt=` attribute, which is
  often a real natural-language description, and none of it survives.
- **`<select>` options become body text.** On 22.2% of pages, dropdown contents (prefecture
  names, country lists) are indistinguishable from prose in the output.

`tests/test_extract.py` pins all of these against a golden fixture.

## 3. The PII mask collides with the bad-word list

`replace_pii` masks phone numbers and SSNs as `+1 XXX XXX XXXX` and `XXX-XX-XXXX`. Both `xx` and
`xxx` are entries in `data/bad_word_list.txt` (lines 397–398).

So if quality filtering runs *after* masking, **every document containing a US phone number or an
SSN is deleted for containing a bad word** — the masking itself causes the rejection.

| stage order | deleted | rate |
|---|---|---|
| clean → mask → filter | 892 of 6,368 | 14.01% |
| clean → filter → mask | 861 of 6,368 | 13.52% |

Measured with the code in this repository: the collision costs **31 documents** on this shard, 13.52% becoming 14.01%. Small in aggregate, but it is a filter deleting documents for a property the pipeline introduced one line earlier, and it falls hardest on exactly the documents that contained personal data.

`cli.py` and `mini_ccc.py` therefore judge quality on the unmasked text and mask only what
survives. `tests/test_quality.py::test_pii_masks_collide_with_the_bad_word_list` is the
regression test.

## 4. What the quality filter removes, and who it removes it from

Extrapolating the corrected deletion rate to the roughly 3 billion documents in Common Crawl
gives 0.41 × 10^8 — roughly 406 million documents this classifier would discard.

Two documents that pass but carry no usable text:

- `palmspringsphotographers.net/.../photo045.html` — 58 characters, entirely navigation chrome
  (`[INDEX] [<<] [>>] Date : ... Comments :`)
- `wookmark.com/group/23160/sztuka-baroku-ii` — 70 characters of sign-up boilerplate

Both are trivially catchable by a minimum word count and a stop-word-ratio test of the kind
Gopher uses. Heuristics are the right tool here: cheap over billions of documents and easy to
audit. A trained classifier earns its cost on the harder cases heuristics cannot express —
machine-generated spam that is fluent, well-punctuated and substantively empty.

**The filter is not language-neutral, and the asymmetry runs in both directions.** The 80%
character-class test does *not* penalise non-Latin scripts: `str.isalnum()` is Unicode-aware, so
kana and Cyrillic count as alphanumeric. But both the document-level punctuation test and the
per-paragraph test in `clean_text` use ASCII-only `string.punctuation`, so Chinese and Japanese
text punctuated solely with full-width marks is stripped paragraph by paragraph and then rejected
outright. Meanwhile the bad-word list is English-only, so non-English adult and spam content is
systematically *under*-filtered relative to its English equivalent.

`tests/test_quality.py::test_cjk_fullwidth_punctuation_survives` is an `xfail(strict=True)` —
it documents the bias as an executable claim, and will fail loudly if the behaviour changes.

## 5. Deduplication

Jaccard similarity over word trigrams, threshold 0.6, with an inverted shingle index so each
document is only compared against candidates that share at least one trigram.

On `data/topic_dataset.json`: **219 documents in, 188 kept, 31 removed.** A naive exact-string
baseline removes about 20, so the near-duplicate matching finds roughly 50% more.

Two things follow from the threshold being 0.6 rather than 1.0:

- **This must not be used as a filesystem deduplicator.** It deliberately collapses *near*
  duplicates, whereas a filesystem may only ever collapse bit-identical blocks. Two revisions of
  a document, or two config files differing in one value, would be stored as one — irreversible
  data corruption. It also lowercases and tokenises on non-alphanumeric characters, which is
  meaningless for binary content.
- **Deduplication is not free.** Muennighoff et al. (2023), *Scaling Data-Constrained Language
  Models*, find that in data-constrained regimes repeating training data for up to ~4 epochs
  yields loss almost indistinguishable from training on fresh unique data. Aggressively removing
  redundancy throws away value. Near-duplicate methods additionally risk false positives that
  erase legitimately distinct documents sharing a template.

## 6. Throughput

Building the dataset end to end took **370.7 s** wall clock (336 s of that in the generation
pass), reading 6,368 pages and writing the ones that pass. That is 0.058 s per document, so a
single process would need roughly 1.75 × 10^8 seconds — about **5.5 years** — to process all of
Common Crawl.

The dominant cost is HTML parsing and the workload is embarrassingly parallel, so the largest
win is processing shards across many processes or machines; Common Crawl is already partitioned
into thousands of independent shards. Within a process: swap BeautifulSoup's `html.parser` for
the C-backed `lxml`, or a dedicated extractor such as `trafilatura`/`resiliparse`, for a
several-fold speedup; and run cheap filters before expensive ones so junk is rejected early.

## 7. How this compares to Common Crawl's own WET extraction

For `http://01tec.de/`: this pipeline produces 390 characters, the WET record 455.

WET segments text more coarsely — it merges content separated by `<br>` and by short inline
blocks onto one line, while this pipeline breaks at every block boundary and inserts blank lines.
Both retain the page `<title>`; neither does boilerplate removal, so navigation menus, cookie
notices and copyright footers survive in both.

**WET is the better input for language model training**, because its coarser segmentation keeps
semantically related lines adjacent. That matters specifically because `clean_text` here deletes
short punctuation-free lines, and so discards fragments that WET would have merged into a
surviving sentence.

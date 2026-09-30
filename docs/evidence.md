# Evidence

Raw material behind `findings.md`: the controlled fixture, two real pages from the shard, and the
WARC-vs-WET comparison. Kept separate so the claims in `findings.md` stay short and every one of
them has something concrete to point at.

## A. Reproducing the record counts

```bash
bash scripts/download_data.sh
python cli.py --fname data.warc --count_only
# -> 6368 HTML pages in data.warc
python scripts/census.py --fname data.warc
# -> results/shard-census.json, with the full Content-Type breakdown
```

An independent census over every record, applying no `Content-Type` equality test:

```
record types      : {'warcinfo': 1, 'request': 48572, 'response': 48572, 'metadata': 48572}
response records  : 48572
no Content-Type   :    24
text/html*        : 47839
exactly text/html :  6368      <- what read_warc_file returns
xhtml*            :     9
other             :   709      (47839 + 709 + 24 = 48572)
distinct CT values:   152

  34661  'text/html; charset=utf-8'
   6368  'text/html'
   3074  'text/html;charset=utf-8'
   1415  'text/html; charset=iso-8859-1'
    656  'text/html; charset=windows-1251'
    212  'image/jpeg'
    212  'application/pdf'
```

## B. The controlled fixture

The structural claims need markup this shard does not contain — a real data table, an indented
code block — so they are demonstrated on a constructed input, `tests/fixtures/revenue_table.html`:

```html
<html><head><title>Revenue</title>
<style>.x{color:red}</style><script>var a=1;</script></head><body>
<h1>Quarterly Revenue</h1>
<img src="logo.png" alt="Acme Corp logo">
<h2>By region</h2>
<table>
<tr><th>Region</th><th>Q1</th><th>Q2</th></tr>
<tr><td>EMEA</td><td>1.2</td><td>1.9</td></tr>
<tr><td>APAC</td><td>0.8</td><td>1.1</td></tr>
</table>
<p>Fetch it with <code>requests.get(url)</code>.</p>
<pre><code>def total(rows):
    s = 0
    for r in rows:
        s += r.amount
    return s
</code></pre>
<!-- internal note -->
</body></html>
```

`html_to_text` output, verbatim — this is `tests/fixtures/revenue_table.expected.txt`, compared
byte for byte by `test_matches_golden_output`:

```
Revenue
Quarterly Revenue

By region

Region	Q1	Q2

EMEA	1.2	1.9

APAC	0.8	1.1

Fetch it with requests.get(url).

def total(rows):
s = 0
for r in rows:
s += r.amount
return s
```

What that shows, each with its own test:

- `<title>` is prepended; `<style>` and `<script>` bodies, the HTML comment and
  `alt="Acme Corp logo"` are all absent.
- `<h1>` and `<h2>` are emitted unmarked — nothing records that they were headings.
- `<th>` and `<td>` cells are tab-joined per row, so reading order survives but the
  header-to-column association does not.
- The inline `<code>` does **not** split the sentence (block tags break lines, inline tags do not).
- The `<pre><code>` block loses its indentation and is no longer valid Python.

## C. Two real pages from the shard

**Record #1**, `http://00monthly.com/kouchi/goiken/` — detected encoding Shift-JIS, two `<table>`
elements, no `<th>`, 53 `<option>` elements.

```html
<h1>ウィークリーマンション、マンスリーマンション 高知</h1>
<h2> ウィークリー、マンスリーマンションで</h2>
<p id="paragraph">敷金0礼金ゼロで家具付き賃貸マンションで仮住まい</p>
<h3>全国のウィークリーマンション・マンスリーマンション検索サイト</h3>
<img src="/common/img/logo/kouchi.gif"
     alt="高知のウィークリーマンション、マンスリーマンションなら00マンスリードットコム" ... />
<select name="pref2"><option value="北海道">北海道</option>
                     <option value="青森県">青森県</option> ... </select>
```

h1, h2 and h3 come out indistinguishable from the `<p>`; the `alt` string has vanished; and the
dropdown's prefecture names have become body text:

```
ウィークリーマンション、マンスリーマンション 高知     <- h1

ウィークリー、マンスリーマンションで                 <- h2

敷金0礼金ゼロで家具付き賃貸マンションで仮住まい       <- p, same treatment

全国のウィークリーマンション・マンスリーマンション検索サイト   <- h3, same treatment
...
ご意見地域

北海道                                              <- <option>, not prose
青森県
岩手県
```

This page is also the clearest case of the language bias in `findings.md` §4: punctuated entirely
with full-width marks, it is reduced to the empty string by `clean_text`.

**Record #3**, `http://01tec.de/` — the first record containing a `<code>` element.

```html
<abbr title="HyperText Markup Language"><code> &#60;html&#62;</code></abbr>
<a href="http://validator.w3.org/check?uri=www.01tec.de" class="validateLink"
   title="valides html5 Dokument"><strong>5</strong></a> Design by ...
```

becomes two orphaned lines, with both `title` attributes discarded:

```
<html>

5

Design by
viridis.de
```

## D. WARC vs WET, same URL

`http://01tec.de/` — this pipeline 390 characters, WET 455.

```
--- html_to_text(WARC) ---        --- CommonCrawl WET ---
01TEC It-Consulting ®             Andreas Degenhart • 01TEC. IT-Consulting • IT-Beratung und Systementwicklung
                                  01TEC It-Consulting ®
Andreas Degenhart                 Andreas Degenhart Schornstrasse 52, 82266 Inning a. Ammersee
                                  t:+49 (8143) 26 48 113
Schornstrasse 52, 82266 Inning    f:+49 (8143) 26 48 114
a. Ammersee                       m:+49 (171) 9798 476
                                  e: info@01tec.de
t:+49 (8143) 26 48 113            IT-Beratung und Systementwicklung
                                  Mein Motto: "Nicht lange überlegen, einfach machen."
e:                                Andreas Degenhart, IT-Spezialist.
info@01tec.de                     <html> 5 Design by viridis.de
                                  Copyright © 2016 Andreas Degenhart. Alle Rechte vorbehalten
Mein Motto:
"Nicht lange überlegen, einfach machen."
```

The page's `<title>` is `Andreas Degenhart • 01TEC. IT-Consulting • IT-Beratung und
Systementwicklung`, which matches the WET record's first line.

Reproduce the WET side with:

```bash
python cli.py --wet_name data.wet --num_records 8
```

## Note on provenance

The fixture in §B and the two case studies in §C were recorded while the extraction logic was
still being written. The golden output above has been regenerated against the current code, so
it reflects what `html_to_text` does today — tab-joined table rows and a prepended `<title>`,
both of which the earliest draft did not do.

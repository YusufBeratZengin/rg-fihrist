# rg-fihrist

Turn the daily index (*fihrist*) of Turkey's **Resmî Gazete** into structured
JSON or RSS 2.0, with Turkish-aware keyword filtering — from the terminal, with
zero runtime dependencies.

The index is the table of contents of the day's Official Gazette: section,
sub-heading, title and link to the document. That is exactly what compliance
officers, lawyers and accountants read every morning; this tool fetches it,
groups it by section and lets you watch the handful of titles you care about.

- Sections: `yasama` (legislation), `yurutme` (executive), `yargi` (judiciary),
  `ilan` (announcements), `diger` (anything unrecognised).
- Turkish case folding (`I` → `ı`, `İ` → `i`) and suffix-aware prefix matching
  (`vergi` matches `vergisi`, `kitap` matches `kitabı`).
- Works with both page layouts: today's `/fihrist?tarih=…` view (UTF-8) and the
  legacy `/eskiler/YYYY/MM/YYYYMMDD.htm` archive (Windows-1254).
- Polite by default: descriptive `User-Agent`, robots.txt honoured, and a
  **hard floor of 2 seconds** between requests that no flag can lower.

**This tool is not an official source.** It reads a public page and copies
titles and links. Always verify against
<https://www.resmigazete.gov.tr/> before relying on a document.

## Install

```console
$ pipx install rg-fihrist        # recommended: isolated CLI
# or, from a checkout:
$ python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
$ pip install -e ".[dev]"
```

Python 3.10+ is required; there are no runtime dependencies.

## 30-second example

```console
$ rg-fihrist tarih 2026-11-03 --ara "tebliğ"
Resmi Gazete fihristi - 2026-11-03 (sayi 33419)
Baslik: 03 Kasım 2026 Tarihli ve 33419 Sayılı
Kaynak: https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03
Arama: tebliğ
Girdi: 2

[YURUTME] (2)
  - Özelleştirme İdaresi Başkanlığının 30/10/2026 Tarihli ve 2026/ÖİB-K-46 Sayılı Kararı (TEBLİĞLER)
    https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-2.pdf
  - Avukatlık Asgari Ücret Tarifesi (TEBLİĞLER)
    https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-3.htm
```

Same data as JSON (the real output has 13 entries; shortened here):

```console
$ rg-fihrist tarih 2026-11-03 --json
{
  "kaynak": "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03",
  "tarih": "2026-11-03",
  "mukerrer": 0,
  "sayi": "33419",
  "baslik": "03 Kasım 2026 Tarihli ve 33419 Sayılı",
  "girdi_sayisi": 13,
  "girdiler": [
    {
      "baslik": "Ormancılık Faaliyetlerinde Vahidi Fiyatla Çalışan Orman Köylülerine Yapılacak Ayni veya Nakdi Dağıtımın Uygulamasına Dair Yönetmelik",
      "baglanti": "https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-1.htm",
      "bolum": "yurutme",
      "alt_baslik": "YÖNETMELİK"
    }
  ],
  "arama": [],
  "kodlama": "utf-8"
}
```

## Commands

```console
rg-fihrist bugun [options]                 # today's index
rg-fihrist tarih 2026-11-02 [options]      # a specific date (YYYY-MM-DD)
```

Options accepted by both commands:

| Option | Meaning |
| --- | --- |
| `--json` | JSON on stdout instead of the grouped text report |
| `--cikti DOSYA` | write the report/JSON to a file instead of stdout |
| `--rss DOSYA` | also write an RSS 2.0 feed |
| `--ara SORGU` | Turkish-aware keyword filter; repeatable (OR) |
| `--bolum yasama\|yurutme\|yargi\|ilan\|diger` | keep only these sections; repeatable |
| `--ilan-yok` | drop the announcements (`ilan`) section |
| `--mukerrer N` | request the N-th duplicate issue of that day |
| `--ham` | read the legacy `/eskiler/...` archive page instead of `/fihrist` |
| `--url URL` | fetch an explicit URL (archives, mirrors, offline tests) |
| `--min-aralik SN` | wait between requests; cannot go below 2 |
| `--timeout SN` | request timeout (default 30) |
| `--robots-yok` | skip the robots.txt check (local testing only) |

`--cikti` and `--rss` may not point at the same file: the second write would
overwrite the first, so the pair is rejected instead.

### Three real scenarios

1. **Morning scan.** `rg-fihrist bugun` — one screen, grouped by section.
2. **Watching a topic.** `rg-fihrist bugun --ara "kişisel veri" --rss kvkk.xml`
   and subscribe to `kvkk.xml` in any feed reader.
3. **Archive search.** `rg-fihrist tarih 2015-03-17 --ham --ara "yönetmelik"`
   reads the legacy Windows-1254 page and prints the 5 matching regulations.

### Turkish search semantics

Matching is per token and **prefix-based** after Turkish case folding:

| Query | Matches | Does not match |
| --- | --- | --- |
| `vergi` | `vergisi`, `Vergi Usul Kanunu` | `verimsiz` |
| `veri` | `verilerin`, `Veri Sorumlusu` | — |
| `kitap` | `kitabı` (p → b softening) | — |
| `ara` | `arama` | `taraftar` (only an inner substring) |

All query tokens must match (AND); several `--ara` flags are OR-ed. One-letter
tokens match exactly. Vowel drop inside a word (`ağız` → `ağzı`) is **not**
handled — that would need a real stemmer.

## Politeness, robots.txt and terms

- One request per page, at most one every 2 seconds, with a `User-Agent` that
  names the project. The 2-second floor is enforced in `Indirici` and in the
  CLI parser, so neither `--min-aralik 0` nor a library caller can disable it.
- `robots.txt` is fetched once per host and honoured. If it cannot be read
  (network error), access is **allowed** — the `urllib` default — and the CLI
  prints a warning on stderr instead of staying silent.
- Only titles and links are copied. Full texts of decisions are never fetched,
  stored or republished; each entry links to the official page.
- The site's terms of use were **not** reviewed in detail for this release;
  robots.txt was read on 2026-11-04 and no rule blocked `/fihrist`. Re-check
  before heavy or automated use, and keep the rate limit.

## Personal data

Titles in the `ilan` (announcements) section can contain natural-person names
(inheritance and bankruptcy notices, for example). This tool copies titles, not
the notices, and never fetches the linked documents. Use `--ilan-yok` if you do
not want that section in your output or feed at all.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success (an empty filter result is still a success, with a warning) |
| 2 | network/HTTP error, including a robots.txt refusal or an unexpected redirect |
| 3 | page structure or content error (unknown layout, empty index, not published yet) |
| 4 | usage error (bad date, bad number, conflicting flags) |
| 5 | output file could not be written |

## Known limits

- **Duplicate issues are unverified.** The site answers
  `/fihrist?tarih=…&mukerrer=N` with a redirect to `/` for every value tested on
  2026-11-04, so `--mukerrer` reports a clear network error rather than a wrong
  page. The flag is kept for the day the site exposes the parameter (see
  `CHANGELOG.md`, 0.2.0).
- A layout change is reported as exit code 3, never as a silently empty result.
  No JavaScript is executed: the tool reads the HTML the server sends.
- The index is a table of contents only. Deciding what a regulation *means*,
  or diffing legal text, is out of scope.

## Development

```console
$ pip install -e ".[dev]"
$ bash scripts/check.sh        # secret scan, ruff, ruff format, mypy, pytest + coverage
```

`scripts/check.sh` is the same gate CI runs; it fails loudly (non-zero) when any
step fails and never swallows a failing command. Tests are offline: recorded
pages live in `tests/fixtures/` (see the README there) and HTTP is injected.

Layout:

```
src/rg_fihrist/
  indir.py     polite HTTP downloader (rate limit, robots.txt, charset)
  ayristir.py  html.parser based index parser (modern + legacy layouts)
  ara.py       Turkish case folding and prefix matching
  rss.py       RSS 2.0 writer
  cli.py       argparse front end and exit codes
tests/         offline tests + fixtures
scripts/       check.sh, secret scanner
```

Contributions: see `CONTRIBUTING.md`. Security reports: `SECURITY.md`.

## License

MIT — see `LICENSE`. This project is not affiliated with the Republic of
Turkey or the Official Gazette; the source data belongs to its publisher.

Türkçe belge: [README.tr.md](README.tr.md)

# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-04

### Fixed

- **`--min-aralik inf` and `--timeout inf` crashed with `OverflowError`.** Both
  parsers now reject non-finite numbers as usage errors, and
  `aralik_dogrula(inf)` clamps to the 2-second floor, so a library caller cannot
  trigger the crash either.
- **Malformed URLs no longer escape as tracebacks.** `http://[::1/x` used to
  raise `ValueError` and `http://host:abc/` an `InvalidURL` from inside the
  downloader; both become `AgHatasi` with exit code 2. `--url` accepts only
  `http(s)`, so a `file://` URL can no longer read a local file.
- **`k` softening added to Turkish matching.** `yönetmelik` now matches
  `yönetmeliğinde` (k → ğ) and `renk` matches `rengi` (k → g); both forms are
  tried because the correct one depends on the suffix. This was the largest
  remaining gap for regulation titles.

- **Search no longer matches a substring in the middle of a word.** `eslesme_mi`
  used `sorgu in metin_jetonu`, so `ara` matched `taraftar` and `tat` matched
  `istatistik`. Matching is now prefix-only, as the documentation always
  claimed; regression tests pin both directions.
- **The 2-second politeness floor can no longer be disabled.** `--min-aralik 0`
  and negative values are rejected with exit code 4, and `Indirici` clamps any
  value it is given (library callers included).
- **Documented usage exit code matches the implementation.** Argparse exits with
  2 by default; the CLI now returns 4 for every usage error, as documented.
- **Legacy archive entries without a leading dash are no longer lost.** On the
  Windows-1254 `/eskiler/` pages, entries such as `1084 Anayasa Mahkemesine Üye
  Seçimine İlişkin Karar` have no dash; they are now recognised by the
  `YYYYMMDD-N.htm` document naming, while previous/next-day navigation links and
  the issue-wide `YYYYMMDD.pdf` button stay out.
- **Line breaks inside titles are collapsed** (`\r\n` used to leak into titles
  on archive pages).
- **Unexpected redirects are reported as network errors.** Invalid dates used to
  redirect to `/` and produced a misleading "unknown page structure" message.
- **An unpublished day gets its own message** instead of a generic parse error.
- `--cikti` and `--rss` pointing at the same file are rejected (the second write
  used to overwrite the first).
- Output file errors are reported on stderr with exit code 5 and a one-line
  message.
- RSS `lastBuildDate` is the generation time in Turkish local time; `pubDate`
  no longer invents a publication hour.

### Added

- `--ilan-yok` to drop the announcements section from output and feeds.
- `--help` and `--surum` exit through `main()` with a return code, so the
  function is testable without catching `SystemExit`.
- Status messages (`yazildi: ...`, `RSS yazildi: ...`, warnings) go to stderr;
  stdout carries data only.
- Offline test suite (94 tests, ~96% line/branch coverage) with recorded
  fixtures for the modern UTF-8 layout, the Windows-1254 archive layout and the
  "not published yet" page.
- `scripts/check.sh` (secret scan, ruff, ruff format, mypy, pytest + coverage)
  and a matching GitHub Actions workflow for Linux and Windows.
- English and Turkish user documentation.

### Changed

- Turkish suffix matching also handles consonant softening (`kitap` → `kitabı`,
  `ağaç` → `ağacı`, `kanat` → `kanadı`).
- `robots.txt` failure is documented as an explicit decision and surfaced as a
  warning instead of being silent.

## [0.1.0] - 2026-11-02

### Added

- Initial CLI: `bugun` and `tarih` commands, grouped text report, `--json`,
  `--ara`, `--rss`, `--bolum`, `--ham`, `--url`.
- Polite downloader with `User-Agent`, robots.txt support and Windows-1254
  decoding for the legacy archive.
- Index parser for the modern `div.fihrist-item` layout and the legacy
  `<b><u>` layout; `YapiHatasi` instead of silently empty results.

# Test fixtures

These files are **recordings** of pages from <https://www.resmigazete.gov.tr/>,
trimmed to the part the parser reads. They are not invented HTML. Nothing here
is fetched at test time: the suite is fully offline.

All three files were captured on **2026-11-04** with the project's own
`User-Agent` and a 2-second gap between requests.

## `fihrist-2026-11-03.htm` — modern layout, UTF-8

- Source: `https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03`
  (issue 33419, dated 3 November 2026).
- Encoding: UTF-8, as served (`Content-Type: text/html; charset=utf-8`).
- Kept: the `preview-title` header block ("03 Kasım 2026 Tarihli ve 33419
  Sayılı") and the whole `#html-content` block — 2 sections, 16
  `div.fihrist-item` nodes (13 entries and 3 sub-heading links such as
  `a - Yargı İlânları`).
- Removed: page chrome, menus, modals, search form, analytics and the
  `google-site-verification` meta tag. Wrapped in a minimal `<html><head>` with
  the original charset so the decoding path stays realistic.
- Contains public document titles and links only — no natural-person data.

## `arsiv-2015-03-17.htm` — legacy layout, Windows-1254

- Source: `https://www.resmigazete.gov.tr/eskiler/2015/03/20150317.htm`
  (issue 29298).
- Encoding: **Windows-1254 bytes preserved**; the file is not valid UTF-8 — that
  is the point of the fixture (`test_eski_arsiv_sayfasi_windows1254` asserts it).
- Kept: the original `<head>`, the header paragraph ("17 Mart 2015 Tarihli ve
  29298 Sayılı Resmî Gazete") and four sections — `YASAMA BÖLÜMÜ` (TBMM KARARI),
  `YÜRÜTME VE İDARE BÖLÜMÜ` (BAKANLAR KURULU KARARI), `YÖNETMELİKLER` with four
  entries. Two of the six entries carry **no leading dash**, which is the
  regression this fixture exists for. Line breaks inside titles are original.
- Removed: navigation tables (`Sonraki Sayı`, the `Æ` arrow), the issue-wide PDF
  button, the `ATAMA KARARLARI` and `BAKANLIKLARA VEKÂLET ETME İŞLEMİ` sections
  (they name individuals), and all other unused markup.
- The `YASAMA BÖLÜMÜ` heading is open-ended in the original Word HTML; here the
  enclosing paragraph is closed so the file stays well-formed. Its markup is
  otherwise untouched.

## `yayimlanmadi.htm` — "not published yet" page, UTF-8

- Source: `https://www.resmigazete.gov.tr/fihrist` on 2026-11-04, before the day's
  issue was published.
- Kept: the `#html-content` block only, which contains the site's notice
  "~ RESMÎ GAZETE'NİN YAYIMLANMASI ÇALIŞMALARI DEVAM ETMEKTEDİR."
- This is the real shape of an early-morning request; `ayristir` turns it into a
  clear `YapiHatasi` instead of "0 entries".

## Updating a fixture

Re-record the page, trim it the same way, keep the numbers above truthful, and
mention the new date here. Never hand-edit a title to make a test pass — change
the test or the parser instead.

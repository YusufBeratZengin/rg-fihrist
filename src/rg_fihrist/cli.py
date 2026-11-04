"""Komut satiri arayuzu.

Kullanim::

    rg-fihrist bugun [--json] [--ara "kelime"] [--rss cikti.xml]
    rg-fihrist tarih 2026-11-02 --json
    rg-fihrist bugun --ara "vergi" --rss cikti.xml

Cikis kodlari:

===  ==========================================================
0    basari
2    ag/HTTP hatasi (robots.txt reddi dahil)
3    sayfa yapisi veya icerik hatasi (bos/yayimlanmamis fihrist)
4    kullanim hatasi (argparse hatalari dahil)
5    cikti dosyasi yazilamadi
===  ==========================================================
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date
from typing import NoReturn
from urllib.parse import urlparse

from rg_fihrist._surum import SURUM
from rg_fihrist.ara import eslesme_mi, girdi_metni
from rg_fihrist.ayristir import BOLUMLER, Fihrist, YapiHatasi, ayristir
from rg_fihrist.indir import (
    MIN_ARALIK_SN,
    AgHatasi,
    Indirici,
    IndiriciProtokolu,
    RobotsHatasi,
    arsiv_url,
    fihrist_url,
)
from rg_fihrist.rss import rss_olustur

CIKIS_TAMAM = 0
CIKIS_AG = 2
CIKIS_YAPI = 3
CIKIS_KULLANIM = 4
CIKIS_DOSYA = 5


class _Parser(argparse.ArgumentParser):
    """argparse'in varsayilan cikis kodu 2'dir; burada 4'e sabitlenir."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(CIKIS_KULLANIM, f"{self.prog}: hata: {message}\n")


def _tarih_arg(deger: str) -> date:
    try:
        return date.fromisoformat(deger)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"gecersiz tarih: {deger!r} (YYYY-MM-DD bekleniyor)"
        ) from None


def _aralik_arg(deger: str) -> float:
    try:
        sayi = float(deger)
    except ValueError:
        raise argparse.ArgumentTypeError(f"gecersiz sayi: {deger!r}") from None
    # NaN veya sonsuz bir deger sleep'i cokertecegi icin reddedilir.
    if not math.isfinite(sayi) or sayi < MIN_ARALIK_SN:
        raise argparse.ArgumentTypeError(
            f"{MIN_ARALIK_SN:g} saniye veya uzeri sonlu bir deger olmali "
            "(kaynak sunucuya kibar davranmak icin)"
        )
    return sayi


def _timeout_arg(deger: str) -> float:
    try:
        sayi = float(deger)
    except ValueError:
        raise argparse.ArgumentTypeError(f"gecersiz sayi: {deger!r}") from None
    if not math.isfinite(sayi) or sayi <= 0:
        raise argparse.ArgumentTypeError("zaman asimi sonlu ve sifirdan buyuk olmali")
    return sayi


def _url_arg(deger: str) -> str:
    """Yalniz http(s) URL kabul et; ``file://`` gibi semalar yerel dosya acardi."""
    parca = urlparse(deger)
    if parca.scheme.lower() not in ("http", "https") or not parca.netloc:
        raise argparse.ArgumentTypeError(f"http(s) URL bekleniyor: {deger!r}")
    return deger


def _mukerrer_arg(deger: str) -> int:
    try:
        sayi = int(deger)
    except ValueError:
        raise argparse.ArgumentTypeError(f"gecersiz sayi: {deger!r}") from None
    if sayi < 0:
        raise argparse.ArgumentTypeError("mukerrer sayisi negatif olamaz")
    return sayi


def _parser_olustur() -> argparse.ArgumentParser:
    p = _Parser(
        prog="rg-fihrist",
        description="Resmi Gazete gunluk fihristini JSON/RSS'e ceviren acik kaynak CLI.",
    )
    p.add_argument("--surum", action="version", version=f"rg-fihrist {SURUM}")
    alt = p.add_subparsers(dest="komut", required=True)

    def ortak(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--json", action="store_true", help="JSON ciktisi (stdout veya --cikti)")
        sp.add_argument(
            "--ara",
            action="append",
            default=[],
            metavar="SORGU",
            help="Turkce duyarli anahtar sozcuk suzgeci (tekrarlanabilir, VEYA)",
        )
        sp.add_argument("--rss", metavar="DOSYA", help="RSS 2.0 dosyasi yaz")
        sp.add_argument("--cikti", metavar="DOSYA", help="Ciktiyi dosyaya yaz (stdout yerine)")
        sp.add_argument(
            "--bolum",
            action="append",
            default=[],
            choices=BOLUMLER,
            help="Yalnizca bu bolumler (tekrarlanabilir)",
        )
        sp.add_argument(
            "--ilan-yok",
            action="store_true",
            help="Ilan bolumunu ciktidan cikar (kisisel veri iceren duyurular)",
        )
        sp.add_argument(
            "--mukerrer",
            type=_mukerrer_arg,
            default=0,
            metavar="N",
            help="Mukerrer sayi numarasi (varsayilan 0 = ana sayi)",
        )
        kaynak = sp.add_mutually_exclusive_group()
        kaynak.add_argument(
            "--ham",
            action="store_true",
            help="Modern /fihrist gorunumu yerine ham arsiv sayfasini (/eskiler/...) cek",
        )
        kaynak.add_argument(
            "--url",
            metavar="URL",
            type=_url_arg,
            help="http(s) URL'yi dogrudan ver (arsiv/ayna/test icin)",
        )
        sp.add_argument(
            "--min-aralik",
            type=_aralik_arg,
            default=MIN_ARALIK_SN,
            metavar="SN",
            help="Istekler arasi bekleme suresi; alt sinir 2 sn",
        )
        sp.add_argument(
            "--timeout",
            type=_timeout_arg,
            default=30.0,
            metavar="SN",
            help="Istek zaman asimi (sn)",
        )
        sp.add_argument(
            "--robots-yok",
            action="store_true",
            help="robots.txt kontrolunu kapat (yalniz yerel test icin)",
        )

    sp_bugun = alt.add_parser("bugun", help="Bugunku fihrist")
    ortak(sp_bugun)
    sp_tarih = alt.add_parser("tarih", help="Belirli tarihli fihrist")
    sp_tarih.add_argument("tarih", type=_tarih_arg, help="Tarih: YYYY-MM-DD (orn. 2026-11-02)")
    ortak(sp_tarih)
    return p


def _url_olustur(args: argparse.Namespace) -> tuple[str, str, int]:
    """Komut + argumanlardan (url, tarih_metni, mukerrer) uret."""
    tarih = date.today() if args.komut == "bugun" else args.tarih
    mukerrer = args.mukerrer
    if args.url:
        url = args.url
    elif args.ham:
        url = arsiv_url(tarih, mukerrer)
    else:
        url = fihrist_url(tarih, mukerrer)
    return url, tarih.isoformat(), mukerrer


def _filtrele(fihrist: Fihrist, args: argparse.Namespace) -> Fihrist:
    """--bolum, --ilan-yok ve --ara (birden fazla --ara VEYA ile) suzgeclerini uygula."""
    havuz = fihrist.girdiler
    if args.bolum:
        havuz = [g for g in havuz if g.bolum in args.bolum]
    if args.ilan_yok:
        havuz = [g for g in havuz if g.bolum != "ilan"]
    if args.ara:
        havuz = [g for g in havuz if any(eslesme_mi(sorgu, girdi_metni(g)) for sorgu in args.ara)]
    fihrist.girdiler = havuz
    return fihrist


def _metin_rapor(fihrist: Fihrist, arama: list[str]) -> str:
    satirlar: list[str] = []
    mk = f", {fihrist.mukerrer}. mukerrer" if fihrist.mukerrer > 0 else ""
    ust = f"Resmi Gazete fihristi - {fihrist.tarih}{mk}"
    if fihrist.sayi:
        ust += f" (sayi {fihrist.sayi})"
    satirlar.append(ust)
    if fihrist.baslik:
        satirlar.append(f"Baslik: {fihrist.baslik}")
    satirlar.append(f"Kaynak: {fihrist.kaynak}")
    if arama:
        satirlar.append(f"Arama: {', '.join(arama)}")
    satirlar.append(f"Girdi: {len(fihrist.girdiler)}")
    satirlar.append("")
    for bolum, girdiler in fihrist.bolumler().items():
        satirlar.append(f"[{bolum.upper()}] ({len(girdiler)})")
        for g in girdiler:
            alt = f" ({g.alt_baslik})" if g.alt_baslik else ""
            satirlar.append(f"  - {g.baslik}{alt}")
            satirlar.append(f"    {g.baglanti}")
        satirlar.append("")
    return "\n".join(satirlar).rstrip() + "\n"


def _stdout_yaz(metin: str) -> None:
    """stdout'a yaz; konsol Turkce karakterleri kodlayamiyorsa kayipsiz dus."""
    try:
        sys.stdout.write(metin)
    except UnicodeEncodeError:
        kodlama = getattr(sys.stdout, "encoding", None) or "ascii"
        sys.stdout.write(metin.encode(kodlama, "replace").decode(kodlama))


def _ayni_yol(a: str, b: str) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _yaz(yol: str, metin: str) -> None:
    """Dosyaya UTF-8 yaz; OSError'i cagirana birak."""
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write(metin)


def main(argv: list[str] | None = None, indirici: IndiriciProtokolu | None = None) -> int:
    parser = _parser_olustur()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help/--surum (0) ve kullanim hatasi (4)
        kod = exc.code
        return kod if isinstance(kod, int) else (CIKIS_TAMAM if kod is None else 1)

    if args.cikti and args.rss and _ayni_yol(args.cikti, args.rss):
        print(
            "hata (kullanim): --cikti ve --rss ayni dosyayi gosteriyor; "
            "ikinci yazim ilk ciktinin uzerine yazardi.",
            file=sys.stderr,
        )
        return CIKIS_KULLANIM

    url, tarih_metni, mukerrer = _url_olustur(args)
    ind = indirici or Indirici(
        min_aralik=args.min_aralik, timeout=args.timeout, robots=not args.robots_yok
    )
    try:
        sayfa = ind.indir(url)
        fihrist = ayristir(sayfa.metin, sayfa.url, tarih=tarih_metni, mukerrer=mukerrer)
    except RobotsHatasi as e:
        print(f"hata (robots.txt): {e}", file=sys.stderr)
        return CIKIS_AG
    except AgHatasi as e:
        print(f"hata (ag): {e}", file=sys.stderr)
        return CIKIS_AG
    except YapiHatasi as e:
        print(f"hata (sayfa yapisi): {e}", file=sys.stderr)
        return CIKIS_YAPI

    if ind.robots_uyarisi:
        print(f"uyari: {ind.robots_uyarisi}", file=sys.stderr)

    fihrist = _filtrele(fihrist, args)
    if not fihrist.girdiler:
        print("uyari: suzgeclerden sonra gosterilecek girdi kalmadi.", file=sys.stderr)

    if args.json:
        veri = fihrist.to_dict()
        veri["arama"] = args.ara
        veri["kodlama"] = sayfa.kodlama
        cikti_metni = json.dumps(veri, ensure_ascii=False, indent=2) + "\n"
    else:
        cikti_metni = _metin_rapor(fihrist, args.ara)

    if args.cikti:
        try:
            _yaz(args.cikti, cikti_metni)
        except OSError as e:
            print(f"hata (dosya): {args.cikti} yazilamadi: {e.strerror or e}", file=sys.stderr)
            return CIKIS_DOSYA
        print(f"yazildi: {args.cikti}", file=sys.stderr)
    else:
        _stdout_yaz(cikti_metni)

    if args.rss:
        rss_metni = rss_olustur(fihrist, arama=", ".join(args.ara) or None)
        try:
            _yaz(args.rss, rss_metni)
        except OSError as e:
            print(f"hata (dosya): {args.rss} yazilamadi: {e.strerror or e}", file=sys.stderr)
            return CIKIS_DOSYA
        print(f"RSS yazildi: {args.rss} ({len(fihrist.girdiler)} girdi)", file=sys.stderr)

    return CIKIS_TAMAM


if __name__ == "__main__":
    sys.exit(main())

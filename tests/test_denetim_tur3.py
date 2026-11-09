"""Regression tests for edge cases found during review (second batch)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from rg_fihrist.ayristir import ayristir
from rg_fihrist.rss import rss_olustur

FIXTURES = Path(__file__).parent / "fixtures"
ARSIV_URL = "https://www.resmigazete.gov.tr/eskiler/2026/11/20261102.htm"
MODERN_URL = "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-02"


def test_kabul_betigi_yayin_kapilarini_calistirir() -> None:
    betik = (Path(__file__).parents[1] / "scripts" / "check.sh").read_text(encoding="utf-8")

    for komut in (
        '"$PYTHON" scripts/sir_tara.py',
        '"$PYTHON" -m ruff check .',
        '"$PYTHON" -m ruff format --check .',
        '"$PYTHON" -m mypy',
        '"$PYTHON" -m pytest --cov --cov-report=term-missing',
        '"$PYTHON" -m rg_fihrist --surum',
    ):
        assert komut in betik


def _eski_fihrist():  # type: ignore[no-untyped-def]
    return ayristir(
        (FIXTURES / "eski_2026-11-02_windows1254.htm").read_text(encoding="windows-1254"),
        ARSIV_URL,
        tarih="2026-11-02",
    )


def test_eski_arsiv_ilan_baglantilari_girdi_olarak_doner() -> None:
    """a/b/c - ... İlânları baglantilari alt baslik degil, gercek girdidir (9/9)."""
    fihrist = _eski_fihrist()

    basliklar = [g.baslik for g in fihrist.girdiler]
    assert len(basliklar) == 9
    assert "a - Yargı İlânları" in basliklar
    assert "b - Artırma, Eksiltme ve İhale İlânları" in basliklar
    assert "c - Çeşitli İlânlar" in basliklar


def test_eski_arsiv_gercek_alt_baslik_korunur_ve_ilan_girdisine_sizmaz() -> None:
    """<u> ile gelen gercek alt basliklar korunur; a/b/c girdileri alt baslik olmaz."""
    fihrist = _eski_fihrist()

    yonetmelikler = [g for g in fihrist.girdiler if "Eskişehir Osmangazi" in g.baslik]
    assert len(yonetmelikler) == 1
    assert yonetmelikler[0].alt_baslik == "YÖNETMELİKLER"

    merkez = [g for g in fihrist.girdiler if "T.C. Merkez Bankasınca" in g.baslik]
    assert len(merkez) == 1
    assert merkez[0].alt_baslik is None


def test_ayristir_rss_zinciri_tarihsiz_girdiyle_calisir() -> None:
    """Eski API uyumu: ayristir varsayilan tarihle RSS'e dogrudan zincirlenebilmeli."""
    fihrist = ayristir(
        (FIXTURES / "fihrist_2026-11-02.htm").read_text(encoding="utf-8"),
        MODERN_URL,
    )

    kok = ET.fromstring(rss_olustur(fihrist))

    assert kok.tag == "rss"
    kanal = kok.find("channel")
    assert kanal is not None
    assert len(kanal.findall("item")) == len(fihrist.girdiler)

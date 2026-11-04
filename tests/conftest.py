"""Ortak fixture'lar: kaydedilmis fihrist sayfalari ag kullanmadan okunur."""

from __future__ import annotations

from pathlib import Path

import pytest

from rg_fihrist.ayristir import Fihrist, ayristir
from rg_fihrist.indir import kodlama_algila, metin_coz

FIXTURE_DIZINI = Path(__file__).with_name("fixtures")

MODERN_AD = "fihrist-2026-11-03.htm"
MODERN_URL = "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03"
MODERN_TARIH = "2026-11-03"

ARSIV_AD = "arsiv-2015-03-17.htm"
ARSIV_URL = "https://www.resmigazete.gov.tr/eskiler/2015/03/20150317.htm"
ARSIV_TARIH = "2015-03-17"


def sayfa_oku(ad: str) -> str:
    """Fixture'i gercek indiricinin kodlama mantigiyla coz."""
    ham = (FIXTURE_DIZINI / ad).read_bytes()
    return metin_coz(ham, kodlama_algila(None, ham))


@pytest.fixture
def modern() -> Fihrist:
    return ayristir(sayfa_oku(MODERN_AD), MODERN_URL, tarih=MODERN_TARIH)


@pytest.fixture
def arsiv() -> Fihrist:
    return ayristir(sayfa_oku(ARSIV_AD), ARSIV_URL, tarih=ARSIV_TARIH)


@pytest.fixture
def arsiv_ham() -> bytes:
    return (FIXTURE_DIZINI / ARSIV_AD).read_bytes()

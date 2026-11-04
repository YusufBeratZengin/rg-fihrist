"""Turkce duyarli arama testleri.

``test_onek_eslesmesi_metnin_ortasindaki_parcayi_yakalamaz`` bir hata duzeltmesinin
regresyon testidir: eski surum ``sorgu in metin_jetonu`` kullandigi icin sorgu
metnin ortasinda gectiginde de eslesiyordu (``ara`` -> ``taraftar``).
"""

from __future__ import annotations

import pytest

from rg_fihrist.ara import ara, eslesme_mi, girdi_metni, jetonler, turkce_kucuk
from rg_fihrist.ayristir import Girdi


def test_turkce_kucuk_harf_kurallari() -> None:
    assert turkce_kucuk("İSTANBUL") == "istanbul"
    assert turkce_kucuk("ISPARTA") == "ısparta"
    assert turkce_kucuk("KİŞİSEL VERİ") == "kişisel veri"
    assert turkce_kucuk("Iğdır") == "ığdır"


def test_jetonler_noktalama_ve_rakamlari_ayirir() -> None:
    assert jetonler("Kişisel Verilerin Korunması Hakkında (6698)") == [
        "kişisel",
        "verilerin",
        "korunması",
        "hakkında",
        "6698",
    ]
    assert jetonler("   ") == []


@pytest.mark.parametrize(
    ("sorgu", "metin"),
    [
        ("vergi", "Katma Değer Vergisi Oranı"),
        ("veri", "Kişisel Verilerin Korunması Kanunu"),
        ("tebliğ", "TEBLİĞLER"),
        ("kişisel veri", "Kişisel Verilerin Korunması Hakkında Kanun"),
    ],
)
def test_onek_eslesmesi_kabul(sorgu: str, metin: str) -> None:
    assert eslesme_mi(sorgu, metin) is True


@pytest.mark.parametrize(
    ("sorgu", "metin"),
    [
        ("ara", "Taraftar Dernekleri Yönetmeliği"),
        ("tat", "İstatistik Tebliği"),
        ("ver", "Çevre Kanunu"),
    ],
)
def test_onek_eslesmesi_metnin_ortasindaki_parcayi_yakalamaz(sorgu: str, metin: str) -> None:
    """Regresyon: ic parca eslesmesi yanlis pozitif uretmemeli."""
    assert eslesme_mi(sorgu, metin) is False


def test_tek_harfli_jeton_yalnizca_tam_eslesir() -> None:
    assert eslesme_mi("a", "abonelik") is False
    assert eslesme_mi("a", "a") is True


def test_unsuz_yumusamasi() -> None:
    assert eslesme_mi("kitap", "kitabı") is True
    assert eslesme_mi("ağaç", "ağacı") is True
    assert eslesme_mi("kanat", "kanadı") is True


def test_k_yumusamasi_iki_bicimde_de_eslesir() -> None:
    """k -> ğ (ünlüden sonra) ve k -> g (n'den sonra) ayrı ayrı denenir."""
    assert eslesme_mi("yönetmelik", "Yönetmeliğinde Değişiklik Yapılmasına Dair Düzenleme") is True
    assert eslesme_mi("renk", "Araç Rengi") is True
    assert eslesme_mi("yönetmelik", "Yönetici Atama Kararı") is False
    assert eslesme_mi("renk", "Kürek Yarışı") is False


def test_tum_jetonlar_gerekli_and_mantigi() -> None:
    assert eslesme_mi("kişisel veri", "Kişisel Sağlık Verisi") is True
    assert eslesme_mi("kişisel veri", "Kişisel Sağlık Bilgisi") is False


def test_bos_sorgu_eslesmez_ama_filtre_uygulanmaz() -> None:
    girdiler = [Girdi(baslik="Vergi Usul Kanunu", baglanti="https://ornek/1")]
    assert eslesme_mi("   ", "Vergi") is False
    assert ara(girdiler, "  ") == girdiler
    assert ara(girdiler, "vergi") == girdiler
    assert ara(girdiler, "harç") == []


def test_girdi_metni_bolum_ve_alt_basligi_kapsar() -> None:
    g = Girdi(baslik="Tebliğ", baglanti="https://ornek/1", bolum="yurutme", alt_baslik="TEBLİĞLER")
    assert girdi_metni(g) == "Tebliğ TEBLİĞLER yurutme"
    assert eslesme_mi("yurutme", girdi_metni(g)) is True

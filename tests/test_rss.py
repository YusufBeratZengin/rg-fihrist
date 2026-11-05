"""RSS 2.0 ciktisi testleri: gecerli XML, alanlar, kacis ve tarih bicimi."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pytest

from rg_fihrist.ayristir import Fihrist, Girdi
from rg_fihrist.rss import TR_SAAT, rss_olustur

SIMDI = datetime(2026, 11, 4, 9, 30, tzinfo=timezone.utc)


def _fihrist(**kw: object) -> Fihrist:
    varsayilan: dict[str, object] = {
        "tarih": "2026-11-03",
        "mukerrer": 0,
        "kaynak": "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03",
        "baslik": "03 Kasım 2026 Tarihli ve 33419 Sayılı",
        "sayi": "33419",
        "girdiler": [
            Girdi(
                baslik="Vergi & Harç Yönetmeliği",
                baglanti="https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-1.htm",
                bolum="yurutme",
                alt_baslik="YÖNETMELİK",
            )
        ],
    }
    varsayilan.update(kw)
    return Fihrist(**varsayilan)  # type: ignore[arg-type]


def test_gecerli_rss_ve_kanal_alanlari() -> None:
    kok = ET.fromstring(rss_olustur(_fihrist(), simdi=SIMDI))
    assert kok.tag == "rss"
    assert kok.get("version") == "2.0"
    kanal = kok.find("channel")
    assert kanal is not None
    assert kanal.findtext("title") == "Resmi Gazete Fihristi 2026-11-03 (sayı 33419)"
    assert kanal.findtext("language") == "tr"
    assert kanal.findtext("link", "").startswith("https://www.resmigazete.gov.tr/fihrist")
    assert kanal.findtext("generator", "").startswith("rg-fihrist ")


def test_oge_alanlari_ve_kacis() -> None:
    kok = ET.fromstring(rss_olustur(_fihrist(), simdi=SIMDI))
    oge = kok.find("channel/item")
    assert oge is not None
    assert oge.findtext("title") == "Vergi & Harç Yönetmeliği"
    assert oge.findtext("category") == "yurutme"
    assert oge.findtext("description") == "Bölüm: yurutme — YÖNETMELİK"
    guid = oge.find("guid")
    assert guid is not None and guid.get("isPermaLink") == "true"
    assert guid.text == oge.findtext("link")


def test_tarihler_rfc822_ve_turkiye_saati() -> None:
    metin = rss_olustur(_fihrist(), simdi=SIMDI)
    kok = ET.fromstring(metin)
    kanal = kok.find("channel")
    assert kanal is not None
    assert kanal.findtext("pubDate") == "Tue, 03 Nov 2026 00:00:00 +0300"
    assert kanal.findtext("lastBuildDate") == "Wed, 04 Nov 2026 12:30:00 +0300"
    assert TR_SAAT.utcoffset(None).total_seconds() == 3 * 3600


def test_mukerrer_ve_arama_aciklamada_gorunur() -> None:
    f = _fihrist(mukerrer=2)
    kok = ET.fromstring(rss_olustur(f, arama="vergi", simdi=SIMDI))
    kanal = kok.find("channel")
    assert kanal is not None
    assert "2. mükerrer" in kanal.findtext("title", "")
    aciklama = kanal.findtext("description", "")
    assert "Arama: 'vergi'" in aciklama
    assert "tam metin degildir" in aciklama


def test_hatali_tarih_uydurulmaz() -> None:
    """Gecersiz tarih icin 2000-01-01 gibi uydurma bir gun yayinlanmamali."""
    with pytest.raises(ValueError, match="gecersiz tarih"):
        rss_olustur(_fihrist(tarih="bilinmiyor"), simdi=SIMDI)


def test_bos_girdi_listesi_de_gecerli_xml() -> None:
    kok = ET.fromstring(rss_olustur(_fihrist(girdiler=[]), simdi=SIMDI))
    assert kok.findall("channel/item") == []


def test_saat_dilimi_olmayan_simdi_turkiye_saati_sayilir() -> None:
    kok = ET.fromstring(rss_olustur(_fihrist(), simdi=datetime(2026, 11, 4, 9, 30)))
    assert kok.findtext("channel/lastBuildDate") == "Wed, 04 Nov 2026 09:30:00 +0300"

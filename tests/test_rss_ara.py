"""RSS ve Turkce arama regresyon testleri."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from rg_fihrist.ara import ara, eslesme_mi, jetonler, turkce_kucuk
from rg_fihrist.ayristir import Fihrist, Girdi
from rg_fihrist.rss import rss_olustur


def _fihrist() -> Fihrist:
    return Fihrist(
        tarih="2026-11-02",
        mukerrer=0,
        kaynak="https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-02",
        sayi="33418",
        girdiler=[
            Girdi(
                baslik="Vergi Usul Kanunu Genel Tebliği",
                baglanti="https://www.resmigazete.gov.tr/eskiler/2026/11/20261102-1.htm",
                bolum="yurutme",
                alt_baslik="TEBLİĞLER",
            ),
            Girdi(
                baslik="İlan Örneği",
                baglanti="https://www.resmigazete.gov.tr/ilanlar/20261102-2.htm",
                bolum="ilan",
            ),
        ],
    )


def test_rss_gecerli_xml_ve_kanal_alanlari() -> None:
    kok = ET.fromstring(rss_olustur(_fihrist(), arama="vergi"))

    kanal = kok.find("channel")
    assert kanal is not None
    assert kanal.findtext("title") == "Resmi Gazete Fihristi 2026-11-02 (sayı 33418)"
    assert kanal.findtext("language") == "tr"
    assert "Arama: 'vergi'" in (kanal.findtext("description") or "")

    ogeler = kanal.findall("item")
    assert len(ogeler) == 2
    assert ogeler[0].findtext("title") == "Vergi Usul Kanunu Genel Tebliği"
    assert ogeler[0].findtext("category") == "yurutme"
    assert ogeler[0].find("guid") is not None
    assert ogeler[0].find("guid").text == ogeler[0].findtext("link")  # type: ignore[union-attr]
    assert "TEBLİĞLER" in (ogeler[0].findtext("description") or "")


def test_rss_mukerrer_basligi() -> None:
    fihrist = _fihrist()
    fihrist.mukerrer = 2

    kanal = ET.fromstring(rss_olustur(fihrist)).find("channel")

    assert kanal is not None
    assert "2. mükerrer" in (kanal.findtext("title") or "")


def test_turkce_kucultme_ve_jetonlar() -> None:
    assert turkce_kucuk("IİI") == "ıiı"
    assert jetonler("Vergi Usul, 2026!") == ["vergi", "usul", "2026"]


def test_ara_ek_duyarli_ve_and_mantigi() -> None:
    girdiler = _fihrist().girdiler

    assert [g.baslik for g in ara(girdiler, "vergi")] == ["Vergi Usul Kanunu Genel Tebliği"]
    assert [g.baslik for g in ara(girdiler, "usul kanun")] == ["Vergi Usul Kanunu Genel Tebliği"]
    assert ara(girdiler, "vergi ilan") == []
    assert ara(girdiler, "  ") == girdiler
    assert eslesme_mi("tebli", "TEBLİĞLER") is True

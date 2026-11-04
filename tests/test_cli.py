"""CLI testleri: cikis kodlari, cikti dosyalari ve hata yollari.

Ag kullanilmaz; ``main`` fonksiyonuna sahte bir ``Indirici`` enjekte edilir.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from rg_fihrist.ayristir import YapiHatasi
from rg_fihrist.cli import (
    CIKIS_AG,
    CIKIS_DOSYA,
    CIKIS_KULLANIM,
    CIKIS_TAMAM,
    CIKIS_YAPI,
    main,
)
from rg_fihrist.indir import AgHatasi, RobotsHatasi, Sayfa
from tests.conftest import (
    ARSIV_AD,
    ARSIV_TARIH,
    ARSIV_URL,
    MODERN_AD,
    MODERN_TARIH,
    MODERN_URL,
    sayfa_oku,
)


class SahteIndirici:
    """``Indirici`` yerine gecen, aga cikmayan sahte indirici."""

    def __init__(
        self, ad: str = MODERN_AD, hata: Exception | None = None, url: str = MODERN_URL
    ) -> None:
        self.ad = ad
        self.hata = hata
        self.url = url
        self.robots_uyarisi: str | None = None
        self.istenen_url: str | None = None

    def indir(self, url: str) -> Sayfa:
        self.istenen_url = url
        if self.hata is not None:
            raise self.hata
        metin = sayfa_oku(self.ad)
        return Sayfa(
            url=self.url, ham=metin.encode(), content_type=None, kodlama="utf-8", metin=metin
        )


def _json_calistir(
    capsys: pytest.CaptureFixture[str], argv: list[str], ad: str = MODERN_AD
) -> tuple[int, dict[str, Any], Any]:
    url = ARSIV_URL if ad == ARSIV_AD else MODERN_URL
    kod = main(argv, indirici=SahteIndirici(ad, url=url))
    cikti = capsys.readouterr()
    return kod, json.loads(cikti.out), cikti


def test_bugun_json_ciktisi(capsys: pytest.CaptureFixture[str]) -> None:
    kod, veri, cikti = _json_calistir(capsys, ["bugun", "--json"])
    assert kod == CIKIS_TAMAM
    assert veri["sayi"] == "33419"
    assert veri["girdi_sayisi"] == 13
    assert veri["kodlama"] == "utf-8"
    assert len(veri["girdiler"]) == 13
    assert set(veri["girdiler"][0]) == {"baslik", "baglanti", "bolum", "alt_baslik"}


def test_tarih_komutu_arsiv_fixturei_ile(capsys: pytest.CaptureFixture[str]) -> None:
    kod, veri, cikti = _json_calistir(capsys, ["tarih", ARSIV_TARIH, "--json"], ad=ARSIV_AD)
    assert kod == CIKIS_TAMAM
    assert veri["sayi"] == "29298"
    assert veri["girdi_sayisi"] == 6
    assert veri["tarih"] == ARSIV_TARIH


def test_arama_suzgeci(capsys: pytest.CaptureFixture[str]) -> None:
    kod, veri, cikti = _json_calistir(capsys, ["bugun", "--json", "--ara", "Avukatlık"])
    assert kod == CIKIS_TAMAM
    assert veri["arama"] == ["Avukatlık"]
    assert veri["girdi_sayisi"] == 1
    assert "Avukatlık" in veri["girdiler"][0]["baslik"]


def test_bolum_ve_ilan_yok_suzgecleri(capsys: pytest.CaptureFixture[str]) -> None:
    kod, veri, cikti = _json_calistir(capsys, ["bugun", "--json", "--bolum", "ilan"])
    assert kod == CIKIS_TAMAM
    assert veri["girdi_sayisi"] == 1
    assert veri["girdiler"][0]["bolum"] == "ilan"

    kod, veri, cikti = _json_calistir(capsys, ["bugun", "--json", "--ilan-yok"])
    assert kod == CIKIS_TAMAM
    assert veri["girdi_sayisi"] == 12
    assert all(g["bolum"] != "ilan" for g in veri["girdiler"])


def test_bos_suzgec_sonucu_uyari_verir_ama_basarili_sayilir(
    capsys: pytest.CaptureFixture[str],
) -> None:
    kod, veri, cikti = _json_calistir(capsys, ["bugun", "--json", "--ara", "olmayan-kelime"])
    assert kod == CIKIS_TAMAM
    assert veri["girdi_sayisi"] == 0
    assert "girdi kalmadi" in cikti.err


def test_cikti_dosyasi_yazilir_stdout_bos_kalir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hedef = tmp_path / "fihrist.json"
    kod = main(["bugun", "--json", "--cikti", str(hedef)], indirici=SahteIndirici())
    cikti = capsys.readouterr()
    assert kod == CIKIS_TAMAM
    assert cikti.out == ""
    assert "yazildi" in cikti.err
    assert json.loads(hedef.read_text(encoding="utf-8"))["girdi_sayisi"] == 13


def test_rss_dosyasi_yazilir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    hedef = tmp_path / "fihrist.xml"
    kod = main(["bugun", "--rss", str(hedef)], indirici=SahteIndirici())
    cikti = capsys.readouterr()
    assert kod == CIKIS_TAMAM
    assert "RSS yazildi" in cikti.err
    kok = ET.fromstring(hedef.read_text(encoding="utf-8"))
    assert len(kok.findall("channel/item")) == 13


def test_cikti_ve_rss_ayni_dosya_reddedilir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hedef = tmp_path / "ayni.json"
    kod = main(
        ["bugun", "--json", "--cikti", str(hedef), "--rss", str(hedef)], indirici=SahteIndirici()
    )
    cikti = capsys.readouterr()
    assert kod == CIKIS_KULLANIM
    assert "ayni dosyayi" in cikti.err
    assert not hedef.exists()


def test_metin_ciktisi_bolumleri_gruplar(capsys: pytest.CaptureFixture[str]) -> None:
    kod = main(["bugun"], indirici=SahteIndirici())
    cikti = capsys.readouterr()
    assert kod == CIKIS_TAMAM
    assert "[YURUTME] (12)" in cikti.out
    assert "[ILAN] (1)" in cikti.out
    assert "sayi 33419" in cikti.out


@pytest.mark.parametrize(
    "argv",
    [
        ["tarih", "2026-13-01"],
        ["tarih", "02-11-2026"],
        ["bugun", "--min-aralik", "0"],
        ["bugun", "--min-aralik", "-1"],
        ["bugun", "--timeout", "0"],
        ["bugun", "--mukerrer", "-1"],
        ["bugun", "--mukerrer", "abc"],
        ["bugun", "--timeout", "abc"],
        ["bugun", "--min-aralik", "abc"],
        ["bugun", "--url", MODERN_URL, "--ham"],
        ["bugun", "--bolum", "olmayan"],
    ],
)
def test_kullanim_hatalari_cikis_kodu_4(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv, indirici=SahteIndirici()) == CIKIS_KULLANIM
    assert capsys.readouterr().err != ""


def test_min_aralik_alt_sinir_mesaji(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bugun", "--min-aralik", "0"], indirici=SahteIndirici()) == CIKIS_KULLANIM
    hata = capsys.readouterr().err
    assert "en az 2 saniye" in hata


def test_yardim_ve_surum_sifir_kodla_cikar(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bugun", "--help"]) == CIKIS_TAMAM
    assert "--json" in capsys.readouterr().out
    assert main(["--surum"]) == CIKIS_TAMAM
    assert "rg-fihrist 0.2.0" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("hata", "beklenen"),
    [
        (AgHatasi("baglanti yok"), CIKIS_AG),
        (RobotsHatasi("izin yok"), CIKIS_AG),
        (YapiHatasi("yapi bozuk"), CIKIS_YAPI),
    ],
)
def test_indirme_hatalari_kodlari(
    hata: Exception, beklenen: int, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["bugun"], indirici=SahteIndirici(hata=hata)) == beklenen
    assert "hata" in capsys.readouterr().err


def test_dosya_yazma_hatasi_kodu_5(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    hedef = tmp_path / "olmayan-dizin" / "fihrist.json"
    kod = main(["bugun", "--json", "--cikti", str(hedef)], indirici=SahteIndirici())
    cikti = capsys.readouterr()
    assert kod == CIKIS_DOSYA
    assert "yazilamadi" in cikti.err


def test_robots_uyarisi_kullaniciya_gosterilir(capsys: pytest.CaptureFixture[str]) -> None:
    ind = SahteIndirici()
    ind.robots_uyarisi = "robots.txt okunamadi (test)"
    assert main(["bugun", "--json"], indirici=ind) == CIKIS_TAMAM
    assert "robots.txt okunamadi" in capsys.readouterr().err


def test_url_ve_ham_url_uretimi() -> None:
    ind = SahteIndirici()
    assert main(["tarih", MODERN_TARIH, "--ham"], indirici=ind) == CIKIS_TAMAM
    assert ind.istenen_url is not None and ind.istenen_url.startswith(
        "https://www.resmigazete.gov.tr/eskiler/2026/11/20261103"
    )
    ind2 = SahteIndirici()
    assert main(["bugun", "--url", ARSIV_URL], indirici=ind2) == CIKIS_TAMAM
    assert ind2.istenen_url == ARSIV_URL


def test_rss_yazilamazsa_kod_5(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    hedef = tmp_path / "olmayan-dizin" / "fihrist.xml"
    kod = main(["bugun", "--rss", str(hedef)], indirici=SahteIndirici())
    cikti = capsys.readouterr()
    assert kod == CIKIS_DOSYA
    assert "yazilamadi" in cikti.err


def test_kodlanamayan_konsolda_cikti_kaybolmaz(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Windows konsolu bazi Turkce karakterleri kodlayamaz; program cokmemeli."""

    class DarStdout:
        encoding = "ascii"

        def __init__(self) -> None:
            self.yazilan: list[str] = []

        def write(self, metin: str) -> None:
            metin.encode("ascii")  # kodlanamayan karakterde UnicodeEncodeError
            self.yazilan.append(metin)

    dar = DarStdout()
    monkeypatch.setattr("sys.stdout", dar)
    kod = main(["bugun"], indirici=SahteIndirici())
    assert kod == CIKIS_TAMAM
    assert dar.yazilan and "YURUTME" in dar.yazilan[0]

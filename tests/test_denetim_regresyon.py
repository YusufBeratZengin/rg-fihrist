"""Regression tests for edge cases found during review."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from rg_fihrist.ayristir import Fihrist, Girdi, ayristir
from rg_fihrist.cli import main
from rg_fihrist.indir import AgHatasi, Indirici

FIXTURES = Path(__file__).parent / "fixtures"
KAYNAK = "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-02"


def _indirici(html: bytes, kodlama: str = "utf-8") -> Indirici:
    def getir(
        url: str, headers: dict[str, str], timeout: float
    ) -> tuple[bytes, dict[str, str], int]:
        return html, {"content-type": f"text/html; charset={kodlama}"}, 200

    return Indirici(getir_fn=getir, robots=False, min_aralik=2.0, sleep_fn=lambda _sn: None)


def _modern_indirici() -> Indirici:
    return _indirici((FIXTURES / "fihrist_2026-11-02.htm").read_bytes())


# --- N1: ayni dosyaya JSON ve RSS yazma veri kaybi ---


def test_ayni_cikti_ve_rss_yolu_reddedilir(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    hedef = tmp_path / "ortak.cikti"
    hedef.write_text("korunmali", encoding="utf-8")

    kod = main(
        ["tarih", "2026-11-02", "--json", "--cikti", str(hedef), "--rss", str(hedef)],
        indirici=_modern_indirici(),
    )

    yakalanan = capsys.readouterr()
    assert kod == 4
    assert hedef.read_text(encoding="utf-8") == "korunmali"
    assert "ayni" in yakalanan.err.lower()


def test_farkli_cikti_ve_rss_yolu_calismaya_devam_eder(tmp_path: Path) -> None:
    json_yolu = tmp_path / "fihrist.json"
    rss_yolu = tmp_path / "fihrist.xml"

    kod = main(
        ["tarih", "2026-11-02", "--json", "--cikti", str(json_yolu), "--rss", str(rss_yolu)],
        indirici=_modern_indirici(),
    )

    assert kod == 0
    assert json.loads(json_yolu.read_text(encoding="utf-8"))["girdi_sayisi"] == 9
    assert "<rss" in rss_yolu.read_text(encoding="utf-8")


# --- N2: eski arsivde tiresiz belgelerin sessizce dusmesi ---


def test_eski_tiresiz_girdiler_kaybolmaz() -> None:
    fihrist = ayristir(
        (FIXTURES / "arsiv_2015-03-17.htm").read_text(encoding="windows-1254"),
        "https://www.resmigazete.gov.tr/eskiler/2015/03/20150317.htm",
        tarih="2015-03-17",
    )

    basliklar = [g.baslik for g in fihrist.girdiler]
    assert len(basliklar) == 6
    assert "Vergi Usul Kanunu Genel Tebliği" in basliklar
    assert "Yargı İlânları" in basliklar


# --- N3: yayin API'sinin paket seviyesinde disa acilmasi ---


def test_paket_seviyesi_disa_acik_ogeler() -> None:
    import rg_fihrist

    for ad in (
        "MIN_ARALIK_SN",
        "aralik_dogrula",
        "girdi_metni",
        "kodlama_algila",
        "metin_coz",
    ):
        assert hasattr(rg_fihrist, ad), ad


def test_girdi_metni_baslik_alt_baslik_ve_bolumu_birlestirir() -> None:
    from rg_fihrist import girdi_metni

    girdi = Girdi(
        baslik="Vergi Usul Kanunu", baglanti="https://x/1", bolum="yurutme", alt_baslik="TEBLİĞLER"
    )

    metin = girdi_metni(girdi)
    assert "Vergi Usul Kanunu" in metin
    assert "TEBLİĞLER" in metin
    assert "yurutme" in metin


# --- N4: istek araligi alt siniri ---


def test_istek_araligi_iki_saniyenin_altina_inemez() -> None:
    # Yayin API'si hata firlatmaz, sessizce kibarlik alt sinirina kirpar.
    assert Indirici(min_aralik=0).min_aralik == 2.0
    assert Indirici(min_aralik=1.99).min_aralik == 2.0


def test_cli_min_aralik_alt_siniri_kullanim_hatasi(capsys) -> None:  # type: ignore[no-untyped-def]
    # CLI dogrulamasi kod 4 dondurur; main SystemExit firlatmaz.
    assert main(["tarih", "2026-11-02", "--min-aralik", "0"]) == 4
    hata = capsys.readouterr().err
    assert "--min-aralik" in hata
    assert "2 saniye veya uzeri" in hata


def test_aralik_dogrula_sinir_degerini_kabul_eder() -> None:
    from rg_fihrist import aralik_dogrula

    assert aralik_dogrula(2.0) == 2.0
    assert aralik_dogrula(5) == 5.0


# --- N5: --ilan-yok secenegi ---


def test_ilan_yok_secenegi_desteklenir(capsys) -> None:  # type: ignore[no-untyped-def]
    kod = main(
        ["tarih", "2026-11-02", "--json", "--ilan-yok"],
        indirici=_modern_indirici(),
    )

    veri = json.loads(capsys.readouterr().out)
    assert kod == 0
    assert veri["girdi_sayisi"] == 5
    assert all(g["bolum"] != "ilan" for g in veri["girdiler"])


# --- N6: yazma hatasi temiz cikis kodu ---


def test_yazma_hatasi_kisa_hata_ve_exit_5(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    hedef = tmp_path / "olmayan-dizin" / "fihrist.json"

    kod = main(
        ["tarih", "2026-11-02", "--json", "--cikti", str(hedef)],
        indirici=_modern_indirici(),
    )

    yakalanan = capsys.readouterr()
    assert kod == 5
    assert "Traceback" not in yakalanan.err
    assert "yazilamadi" in yakalanan.err.lower()
    assert not hedef.exists()


# --- N7: gecersiz URL ag hatasi olarak raporlanir ---


def test_gecersiz_url_ag_hatasi_olarak_raporlanir() -> None:
    with pytest.raises(AgHatasi):
        Indirici(robots=False, min_aralik=2.0).indir("http://[::1/x")


# --- B6: argparse kullanim hatasi dokumante kod 4 ---


def test_argparse_kullanim_hatasi_exit_4(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main([]) == 4
    assert "usage" in capsys.readouterr().err.lower()


# --- B7: bugun Turkiye saatini kullanir ---


def test_bugun_turkiye_saatini_kullanir() -> None:
    from rg_fihrist.cli import bugun_tarihi

    utc_gece_yarisindan_once = datetime(2026, 11, 5, 22, 30, tzinfo=timezone.utc)
    assert bugun_tarihi(utc_gece_yarisindan_once) == date(2026, 11, 6)


# --- B8: eski basliklarda satir sonu kalmaz ---


def test_eski_basliklarda_satir_sonu_yok() -> None:
    fihrist = ayristir(
        (FIXTURES / "eski_2026-11-02_windows1254.htm").read_text(encoding="windows-1254"),
        "https://www.resmigazete.gov.tr/eskiler/2026/11/20261102.htm",
        tarih="2026-11-02",
    )

    assert len(fihrist.girdiler) == 9
    for girdi in fihrist.girdiler:
        assert "\r" not in girdi.baslik
        assert "\n" not in girdi.baslik


# --- B9: meta baslik copu ---


def test_meta_baslik_tam_ve_temiz() -> None:
    fihrist = ayristir(
        (FIXTURES / "fihrist_2026-11-02.htm").read_text(encoding="utf-8"),
        KAYNAK,
        tarih="2026-11-02",
    )

    # Gercek preview-title tarih/sayi + "Resmî Gazete" icerir; yayin
    # normalizasyonu kurum adini cikartip tarih/sayiyi "Sayılı" ile bitirir.
    assert fihrist.baslik == "02 Kasım 2026 Tarihli ve 33418 Sayılı"


# --- B10: arama docstring ile tutarli: onek, her konumda substring degil ---


def test_arama_onek_eslesmesi_substringe_genislemez() -> None:
    from rg_fihrist.ara import eslesme_mi

    assert eslesme_mi("ila", "filan listesi") is False
    assert eslesme_mi("tebli", "TEBLİĞLER") is True


# --- B11: gecersiz RSS tarihi acik ValueError ile reddedilir ---


def test_rss_gecersiz_tarih_acik_hata_verir() -> None:
    from rg_fihrist.rss import rss_olustur

    fihrist = Fihrist(tarih="2026-02-30", mukerrer=0, kaynak=KAYNAK)

    with pytest.raises(ValueError) as bilgi:
        rss_olustur(fihrist)

    assert "gecersiz tarih" in str(bilgi.value).lower()


# --- B12: negatif mukerrer sessizce kirpilmaz ---


def test_negatif_mukerrer_reddedilir(capsys) -> None:  # type: ignore[no-untyped-def]
    kod = main(
        ["tarih", "2026-10-27", "--ham", "--mukerrer", "-5"],
        indirici=_modern_indirici(),
    )

    yakalanan = capsys.readouterr()
    assert kod == 4
    assert "mukerrer" in yakalanan.err.lower()
    assert yakalanan.out == ""

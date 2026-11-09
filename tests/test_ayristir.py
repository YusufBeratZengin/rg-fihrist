"""Ayristirici testleri: kaydedilmis sayfalar, kenar durumlar ve hata yollari.

Fixture'lar 2026-11-04'te canli siteden alinip icerik bloguna indirgenmistir
(ayrintilar: tests/fixtures/README.md).
"""

from __future__ import annotations

import pytest

from rg_fihrist.ayristir import Fihrist, YapiHatasi, ayristir
from tests.conftest import MODERN_URL, sayfa_oku


def test_modern_sayfa_meta_verisi(modern: Fihrist) -> None:
    assert modern.sayi == "33419"
    assert modern.baslik == "03 Kasım 2026 Tarihli ve 33419 Sayılı"
    assert modern.kaynak == MODERN_URL
    assert modern.tarih == "2026-11-03"
    assert modern.mukerrer == 0


def test_modern_sayfa_girdileri(modern: Fihrist) -> None:
    # Fixture HTML: 12 /eskiler/ belgesi + 4 /ilanlar/ baglantisi = 16 girdi.
    assert len(modern.girdiler) == 16
    bolumler = modern.bolumler()
    assert list(bolumler) == ["yurutme", "ilan"]
    assert len(bolumler["yurutme"]) == 12
    assert len(bolumler["ilan"]) == 4

    ilk = modern.girdiler[0]
    assert ilk.bolum == "yurutme"
    assert ilk.alt_baslik == "YÖNETMELİK"
    assert ilk.baslik.startswith("Ormancılık Faaliyetlerinde Vahidi Fiyatla")
    assert ilk.baglanti == "https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-1.htm"


def test_modern_sayfa_ilan_alt_basligi_ve_baglantisi(modern: Fihrist) -> None:
    # a/b/c etiketleri baglantili ilan girdileridir; alt baslik degildir.
    ilanlar = modern.bolumler()["ilan"]
    assert [g.baslik for g in ilanlar[:3]] == [
        "a - Yargı İlânları",
        "b - Artırma, Eksiltme ve İhale İlânları",
        "c - Çeşitli İlânlar",
    ]
    assert ilanlar[3].baslik.startswith("T.C. Merkez Bankasınca Belirlenen Döviz Kurları")
    assert all(g.alt_baslik is None for g in ilanlar)
    assert [g.baglanti for g in ilanlar] == [
        f"https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/2026/11/20261103-{n}.htm"
        for n in range(2, 6)
    ]


def test_modern_sayfada_gezinme_baglantilari_girdi_olmaz(modern: Fihrist) -> None:
    basliklar = " | ".join(g.baslik for g in modern.girdiler)
    assert "PDF Görüntüle" not in basliklar
    assert "Sonraki" not in basliklar
    assert "Önceki" not in basliklar
    # Ilan baglantilari gezinme degildir; yukaridaki test dordunu de dogrular.


def test_eski_arsiv_sayfasi_windows1254(arsiv: Fihrist, arsiv_ham: bytes) -> None:
    # Kodlama gercekten Windows-1254: baytlar UTF-8 olarak cozulemez.
    with pytest.raises(UnicodeDecodeError):
        arsiv_ham.decode("utf-8")

    assert arsiv.sayi == "29298"
    assert arsiv.baslik == "17 Mart 2015 Tarihli ve 29298 Sayılı"
    assert len(arsiv.girdiler) == 6
    bolumler = arsiv.bolumler()
    assert list(bolumler) == ["yasama", "yurutme"]
    assert len(bolumler["yasama"]) == 1
    assert len(bolumler["yurutme"]) == 5


def test_eski_arsivde_tiresiz_girdi_de_alinir(arsiv: Fihrist) -> None:
    """TBMM karari satiri tire ile baslamaz; ayni gunun belgesi oldugu icin alinmali."""
    yasama = arsiv.bolumler()["yasama"][0]
    assert yasama.baslik == "1084 Anayasa Mahkemesine Üye Seçimine İlişkin Karar"
    assert yasama.alt_baslik == "TBMM KARARI"
    assert yasama.baglanti.endswith("/eskiler/2015/03/20150317-1.htm")


def test_eski_arsivde_kirilan_satirlar_tek_bosluga_indirilir(arsiv: Fihrist) -> None:
    yurutme = arsiv.bolumler()["yurutme"]
    vekalet = next(g for g in yurutme if g.baslik.startswith("2015/7391"))
    assert "\r" not in vekalet.baslik and "\n" not in vekalet.baslik
    assert "  " not in vekalet.baslik
    assert vekalet.baglanti.endswith("/eskiler/2015/03/20150317-2.htm")


def test_yayimlanmamis_sayfa_anlasilir_hata_verir() -> None:
    metin = sayfa_oku("yayimlanmadi.htm")
    with pytest.raises(YapiHatasi) as hata:
        ayristir(metin, "https://www.resmigazete.gov.tr/fihrist")
    assert "yayimlanmamis" in str(hata.value)


def test_yapi_degisince_sessiz_bos_sonuc_yok() -> None:
    metin = (
        "<html><body><div class='yeni-liste'><h2>YÜRÜTME VE İDARE BÖLÜMÜ</h2>"
        "<ul><li><a href='/mevzuat/2026/11/20261105-1.htm'>Bir Yönetmelik</a></li></ul>"
        "</div></body></html>"
    )
    with pytest.raises(YapiHatasi) as hata:
        ayristir(metin, "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-05")
    assert "taninamadi" in str(hata.value)


def test_bolum_var_girdi_yoksa_hata() -> None:
    metin = "<html><body><div class='html-title'>YÜRÜTME VE İDARE BÖLÜMÜ</div></body></html>"
    with pytest.raises(YapiHatasi) as hata:
        ayristir(metin, MODERN_URL)
    assert "girdisi bulunamadi" in str(hata.value)


def _a(href: str, metin: str) -> str:
    return f"<a href='{href}'>{metin}</a>"


def _sayfa(*ogeler: str, bolum: str = "YÜRÜTME VE İDARE BÖLÜMÜ") -> str:
    """Elle yazilmis kucuk fihrist HTML'i (canli sayfa degil, sozlesme testi)."""
    return (
        "<html><body>"
        f"<div class='html-title'>{bolum}</div>"
        + "".join(f"<div class='fihrist-item'>{oge}</div>" for oge in ogeler)
        + "</body></html>"
    )


def test_gezinme_baglantisi_ve_pdf_dugmesi_elenir() -> None:
    metin = (
        _sayfa(_a("/eskiler/2026/11/20261105-1.htm", "Deneme Yönetmeliği"))
        .replace("<body>", "<body>" + _a("/fihrist?tarih=2026-11-04", "Sonraki Sayı"))
        .replace("<body>", "<body>" + _a("/eskiler/2026/11/20261105.pdf", "PDF Görüntüle"))
    )
    f = ayristir(metin, "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-05")
    assert [g.baslik for g in f.girdiler] == ["Deneme Yönetmeliği"]


def test_main_aspx_sarmalayicisi_cozulur() -> None:
    metin = _sayfa(
        _a("/main.aspx?main=/eskiler/2026/11/20261105-3.htm", "Sarmalayıcılı Yönetmelik")
    )
    f = ayristir(metin, "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-05")
    beklenen = "https://www.resmigazete.gov.tr/eskiler/2026/11/20261105-3.htm"
    assert f.girdiler[0].baglanti == beklenen


def test_javascript_bos_ve_kisa_baglantilar_atlanir() -> None:
    metin = _sayfa(
        _a("javascript:void(0)", "Yazdırma Düğmesi"),
        _a("#icerik", "İçerik Bağlantısı"),
        _a("/eskiler/2026/11/20261105-4.htm", "Kısa"),
        _a("/eskiler/2026/11/20261105-5.htm", "Geçerli Yönetmelik"),
    )
    f = ayristir(metin, MODERN_URL)
    assert [g.baslik for g in f.girdiler] == ["Geçerli Yönetmelik"]


def test_ayni_belge_iki_kez_eklenmez() -> None:
    tekrar = _a("/eskiler/2026/11/20261105-1.htm", "Tekrar Eden Yönetmelik")
    assert len(ayristir(_sayfa(tekrar, tekrar), MODERN_URL).girdiler) == 1


def test_mukerrer_bilgisi_metinden_okunur() -> None:
    metin = _sayfa(_a("/eskiler/2026/11/20261103-9.htm", "Mükerrer Sayı Yönetmeliği")).replace(
        "<body>",
        "<body><p>3 Kasım 2026 Tarihli ve 33419 2 Mükerrer Resmî Gazete</p>",
    )
    f = ayristir(metin, "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03")
    assert f.mukerrer == 2
    assert f.baslik == "3 Kasım 2026 Tarihli ve 33419 Sayılı 2. Mükerrer"

"""Indirici testleri: ag yok; getir/sleep/saat fonksiyonlari enjekte edilir."""

from __future__ import annotations

import urllib.request
from datetime import date

import pytest

from rg_fihrist.indir import (
    MIN_ARALIK_SN,
    USER_AGENT,
    AgHatasi,
    Indirici,
    RobotsHatasi,
    aralik_dogrula,
    arsiv_url,
    fihrist_url,
    kodlama_algila,
    metin_coz,
)

SAYFA_URL = "https://ornek.test/fihrist?tarih=2026-11-03"
ROBOTS_URL = "https://ornek.test/robots.txt"
GOVDE = b"<html><body>fihrist</body></html>"


class SahteGetir:
    """getir_fn yerine gecen, cagrilari kaydeden sahte indirici."""

    def __init__(self, yanitlar: dict[str, tuple[bytes, dict[str, str], int]]) -> None:
        self.yanitlar = yanitlar
        self.cagrilar: list[str] = []
        self.basliklar: list[dict[str, str]] = []

    def __call__(
        self, url: str, headers: dict[str, str], timeout: float
    ) -> tuple[bytes, dict[str, str], int]:
        self.cagrilar.append(url)
        self.basliklar.append(dict(headers))
        if url not in self.yanitlar:
            raise AgHatasi(f"sahte ag hatasi: {url}")
        return self.yanitlar[url]


class SahteSaat:
    """Yalnizca uyku sirasinda ilerleyen monoton saat."""

    def __init__(self) -> None:
        self.an = 100.0
        self.uykular: list[float] = []

    def __call__(self) -> float:
        return self.an

    def sleep(self, saniye: float) -> None:
        self.uykular.append(saniye)
        self.an += saniye


def _indirici(getir: SahteGetir, saat: SahteSaat, **kw: object) -> Indirici:
    return Indirici(getir_fn=getir, sleep_fn=saat.sleep, saat_fn=saat, **kw)  # type: ignore[arg-type]


def test_varsayilan_aralik_en_az_iki_saniye() -> None:
    assert MIN_ARALIK_SN == 2.0
    assert aralik_dogrula(0) == 2.0
    assert aralik_dogrula(-5) == 2.0
    assert aralik_dogrula(float("nan")) == 2.0
    assert aralik_dogrula("gecersiz") == 2.0  # type: ignore[arg-type]
    assert aralik_dogrula(7.5) == 7.5


def test_sifir_aralik_verilse_bile_kirpilir() -> None:
    """Regresyon: --min-aralik 0 kibar istek politikasini kapatamaz."""
    ind = Indirici(min_aralik=0, robots=False)
    assert ind.min_aralik == 2.0
    ind = Indirici(min_aralik=-3, robots=False)
    assert ind.min_aralik == 2.0


def test_iki_istek_arasi_tam_olarak_beklenir() -> None:
    getir = SahteGetir({SAYFA_URL: (GOVDE, {}, 200)})
    saat = SahteSaat()
    ind = _indirici(getir, saat, robots=False)
    ind.indir(SAYFA_URL)
    assert saat.uykular == []
    ind.indir(SAYFA_URL)
    assert saat.uykular == [2.0]


def test_kullanici_ajani_gonderilir() -> None:
    getir = SahteGetir({SAYFA_URL: (GOVDE, {}, 200)})
    ind = _indirici(getir, SahteSaat(), robots=False)
    ind.indir(SAYFA_URL)
    assert getir.basliklar[0]["User-Agent"] == USER_AGENT
    assert "rg-fihrist" in getir.basliklar[0]["User-Agent"]


def test_robots_yasagi_istegi_durdurur() -> None:
    getir = SahteGetir(
        {
            ROBOTS_URL: (b"User-agent: *\nDisallow: /fihrist\n", {}, 200),
            SAYFA_URL: (GOVDE, {}, 200),
        }
    )
    ind = _indirici(getir, SahteSaat())
    with pytest.raises(RobotsHatasi):
        ind.indir(SAYFA_URL)
    assert getir.cagrilar == [ROBOTS_URL]


def test_robots_yoksa_erisim_serbest() -> None:
    getir = SahteGetir({ROBOTS_URL: (b"", {}, 404), SAYFA_URL: (GOVDE, {}, 200)})
    ind = _indirici(getir, SahteSaat())
    assert ind.indir(SAYFA_URL).url == SAYFA_URL
    assert ind.robots_uyarisi is None


def test_robots_okunamazsa_erisim_serbest_ama_uyari_verilir() -> None:
    getir = SahteGetir({SAYFA_URL: (GOVDE, {}, 200)})
    ind = _indirici(getir, SahteSaat())
    assert ind.indir(SAYFA_URL).url == SAYFA_URL
    assert ind.robots_uyarisi is not None
    assert "robots.txt okunamadi" in ind.robots_uyarisi


def test_robots_bir_kez_indirilir() -> None:
    getir = SahteGetir({ROBOTS_URL: (b"User-agent: *\n", {}, 200), SAYFA_URL: (GOVDE, {}, 200)})
    ind = _indirici(getir, SahteSaat())
    ind.indir(SAYFA_URL)
    ind.indir(SAYFA_URL)
    assert getir.cagrilar.count(ROBOTS_URL) == 1


def test_kodlama_content_type_oncelikli() -> None:
    assert kodlama_algila("text/html; charset=ISO-8859-9", b"<meta charset=utf-8>") == "iso-8859-9"


def test_kodlama_meta_etiketinden_okunur() -> None:
    ham = b'<meta http-equiv="Content-Type" content="text/html; charset=windows-1254">'
    assert kodlama_algila("text/html", ham) == "windows-1254"


def test_kodlama_utf8_denemesi_ve_windows1254_dususu() -> None:
    assert kodlama_algila(None, "Türkçe metin".encode()) == "utf-8"
    assert kodlama_algila(None, "İlan Bölümü".encode("windows-1254")) == "windows-1254"


def test_metin_coz_bilinmeyen_kodlamada_utf8e_duser() -> None:
    assert metin_coz(b"abc", "utf-8") == "abc"
    assert metin_coz("ı".encode("windows-1254"), "windows-1254") == "ı"
    assert metin_coz(b"abc", "olmayan-kodlama") == "abc"


def test_url_ureticileri() -> None:
    gun = date(2026, 11, 2)
    assert fihrist_url(gun) == "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-02"
    assert fihrist_url(gun, 2).endswith("tarih=2026-11-02&mukerrer=2")
    assert arsiv_url(gun) == "https://www.resmigazete.gov.tr/eskiler/2026/11/20261102.htm"
    assert arsiv_url(gun, 3).endswith("/eskiler/2026/11/20261102-3.htm")
    with pytest.raises(ValueError):
        fihrist_url(gun, -1)
    with pytest.raises(ValueError):
        arsiv_url(gun, -1)


class _Yanit:
    def __init__(self, son_url: str, govde: bytes) -> None:
        self._son = son_url
        self._govde = govde
        self.headers = {"Content-Type": "text/html"}

    def __enter__(self) -> _Yanit:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def geturl(self) -> str:
        return self._son

    def read(self) -> bytes:
        return self._govde


def test_ana_sayfaya_yonlendirme_ag_hatasi_olarak_bildirilir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gecersiz tarih/sayi istekleri site tarafindan '/' adresine yonlendiriliyor.

    Bu durumda govde ana sayfadir; 'sayfa yapisi taninamadi' demek yaniltici olur.
    """
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: _Yanit("https://ornek.test/", b"<html></html>")
    )
    ind = Indirici(robots=False)
    with pytest.raises(AgHatasi) as hata:
        ind.indir("https://ornek.test/fihrist?tarih=2026-11-03&mukerrer=9")
    assert "yonlendirildi" in str(hata.value)


def test_http_hatasi_ag_hatasina_cevrilir(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error
    from email.message import Message

    def _patlat(*_a: object, **_k: object) -> object:
        raise urllib.error.HTTPError("https://ornek.test/x", 503, "Servis yok", Message(), None)

    monkeypatch.setattr(urllib.request, "urlopen", _patlat)
    with pytest.raises(AgHatasi) as hata:
        Indirici(robots=False).indir("https://ornek.test/x")
    assert "HTTP 503" in str(hata.value)


def test_url_hatasi_ag_hatasina_cevrilir(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    def _patlat(*_a: object, **_k: object) -> object:
        raise urllib.error.URLError("dns yok")

    monkeypatch.setattr(urllib.request, "urlopen", _patlat)
    with pytest.raises(AgHatasi) as hata:
        Indirici(robots=False).indir("https://ornek.test/x")
    assert "dns yok" in str(hata.value)

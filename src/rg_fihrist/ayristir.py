"""Fihrist (gunluk icindekiler) sayfasini html.parser ile ayristirir.

Iki yerlesim desteklenir:

- Modern: ``/fihrist?tarih=...`` -> ``div.html-title`` bolum, ``div.html-subtitle``
  alt baslik, ``div.fihrist-item > a`` girdi (UTF-8).
- Eski arsiv: ``/eskiler/YYYY/MM/YYYYMMDD.htm`` -> Word HTML, bolumler
  ``<b><u>`` icinde, girdiler baglantili paragraflar (Windows-1254). Girdiler ya
  tire ile baslar ya da dogrudan ayni sayinin belgesine baglanir
  (``20150317-4.htm``); gezinme baglantilari (onceki/sonraki sayi, PDF) boylece
  ayiklanir.

Yalnizca baslik ve baglanti alinir; kararlarin tam metni kopyalanmaz.
Sayfa yapisi taninmazsa ``YapiHatasi`` firlatilir; sessiz bos sonuc yok.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

TIRNAK = "\xa0"  # &nbsp;

BOLUMLER = ("yasama", "yurutme", "yargi", "ilan", "diger")

_BOLUM_ANAHTAR = (
    (re.compile(r"YASAMA"), "yasama"),
    (re.compile(r"Y[ÜU]R[ÜU]TME|İDARE|IDARE"), "yurutme"),
    (re.compile(r"YARGI"), "yargi"),
    (re.compile(r"[İI]L[ÂA]N|ILAN"), "ilan"),
)

_BOLUM_DESENI = re.compile(r"B[ÖO]L[ÜU]M[ÜU]")
_SAYI_DESENI = re.compile(
    r"(?P<gun>\d{1,2})\s+(?P<ay>[A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(?P<yil>\d{4})\s+Tarihli\s+ve\s+"
    r"(?P<sayi>\d+)\s*(?:Sayılı|Sayili)?"
    r"(?:\s*(?P<mukerrer>\d+)\s*[Mm]ükerrer)?",
    re.IGNORECASE,
)
_ALT_BASLIK_DESENI = re.compile(r"^[a-zçğıöşü]\s*-\s*", re.IGNORECASE)
_ARSIV_YOLU = re.compile(
    r"/eskiler/\d{4}/\d{2}/(?P<gun>\d{8})(?:-\d+)?\.(?:html?|pdf)$", re.IGNORECASE
)
# Tek belge: /eskiler/YYYY/MM/YYYYMMDD-N.htm. Sayinin tamaminin PDF'i
# (YYYYMMDD.pdf) bu kaliba uymaz; boylece "PDF Görüntüle" dugmesi girdi sayilmaz.
_ARSIV_BELGE = re.compile(r"/eskiler/\d{4}/\d{2}/(?P<gun>\d{8})-\d+\.(?:html?|pdf)$", re.IGNORECASE)
_YAYIM_YOK = re.compile(r"YAYIMLANMASI\s+ÇALIŞMALARI\s+DEVAM", re.IGNORECASE)
_TIRELER = "—–‒―-"


class YapiHatasi(Exception):
    """Sayfa yapisi taninamadi veya fihrist girdisi yok; sessiz bos sonuc uretilmez."""


@dataclass
class Girdi:
    """Tek fihrist girdisi: baslik + baglanti (+ bolum ve alt baslik)."""

    baslik: str
    baglanti: str
    bolum: str = "diger"
    alt_baslik: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "baslik": self.baslik,
            "baglanti": self.baglanti,
            "bolum": self.bolum,
            "alt_baslik": self.alt_baslik,
        }


@dataclass
class Fihrist:
    """Ayristirilmis fihrist: meta veri + girdiler."""

    tarih: str
    mukerrer: int
    kaynak: str
    baslik: str | None = None
    sayi: str | None = None
    girdiler: list[Girdi] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "kaynak": self.kaynak,
            "tarih": self.tarih,
            "mukerrer": self.mukerrer,
            "sayi": self.sayi,
            "baslik": self.baslik,
            "girdi_sayisi": len(self.girdiler),
            "girdiler": [g.to_dict() for g in self.girdiler],
        }

    def bolumler(self) -> dict[str, list[Girdi]]:
        """Girdileri bolume gore grupla (siralama: BOLUMLER)."""
        grup: dict[str, list[Girdi]] = {b: [] for b in BOLUMLER}
        for g in self.girdiler:
            grup.setdefault(g.bolum, []).append(g)
        return {b: grup[b] for b in BOLUMLER if grup.get(b)}


def _bolum_adi(metin: str) -> str | None:
    """Bolum basligindan kanonik ad uret (YÜRÜTME VE İDARE BÖLÜMÜ -> yurutme)."""
    if not _BOLUM_DESENI.search(metin):
        return None
    for desen, ad in _BOLUM_ANAHTAR:
        if desen.search(metin):
            return ad
    return "diger"


def _baglanti_coz(kaynak: str, href: str) -> str | None:
    """Baglantiyi mutlak URL'ye cevir; main.aspx sarmalayicilarinda ic 'main' alinir."""
    href = href.strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript"):
        return None
    url = urljoin(kaynak, href)
    if "main.aspx" in urlparse(url).path:
        sorgu = parse_qs(urlparse(url).query)
        if sorgu.get("main"):
            url = urljoin(kaynak, sorgu["main"][0])
    return url


def _sayfa_tarihi(kaynak: str) -> str | None:
    """Sayfanin gununu ``YYYYMMDD`` olarak cikar (arsiv girdisi tanima icin)."""
    parca = urlparse(kaynak)
    sorgu = parse_qs(parca.query)
    if sorgu.get("tarih"):
        return sorgu["tarih"][0].replace("-", "")
    es = _ARSIV_YOLU.search(parca.path)
    return es.group("gun") if es else None


def _sadelestir(metin: str) -> str:
    """Bosluklari (satir sonu, &nbsp; dahil) tek bosluga indir."""
    return " ".join(metin.replace(TIRNAK, " ").split())


class _Ayrisitirici(HTMLParser):
    def __init__(self, kaynak: str) -> None:
        super().__init__(convert_charrefs=True)
        self.kaynak = kaynak
        self.bolum = "diger"
        self.alt_baslik: str | None = None
        self.girdiler: list[Girdi] = []
        self._bolum_goruldu = False
        self._tum_metin: list[str] = []
        self._belge_tarihi = _sayfa_tarihi(kaynak)
        # modern yerlesim durumu
        self._div_yigin: list[str] = []  # acik div class'lari
        self._baslik_modu: str | None = None  # "baslik" | "alt" | None
        self._baslik_metni: list[str] = []
        # baglanti yakalama
        self._a_href: str | None = None
        self._a_metni: list[str] = []
        self._a_girdide = False
        # eski yerlesim: <u> icindeki basliklar
        self._u_derinlik = 0
        self._u_metni: list[str] = []

    def _div_sinifi(self, attrs: list[tuple[str, str | None]]) -> str:
        for k, v in attrs:
            if k == "class" and v:
                return v
        return ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div":
            sinif = self._div_sinifi(attrs)
            self._div_yigin.append(sinif)
            if "html-title" in sinif:
                self._baslik_modu = "baslik"
                self._baslik_metni = []
            elif "html-subtitle" in sinif:
                self._baslik_modu = "alt"
                self._baslik_metni = []
        elif tag == "a":
            href = dict(attrs).get("href")
            self._a_href = href
            self._a_metni = []
            self._a_girdide = any("fihrist-item" in c for c in self._div_yigin)
        elif tag == "u":
            self._u_derinlik += 1
            self._u_metni = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            if self._baslik_modu is not None and self._div_yigin:
                metin = _sadelestir("".join(self._baslik_metni))
                if metin:
                    self._baslik_isle(metin)
                self._baslik_modu = None
                self._baslik_metni = []
            if self._div_yigin:
                self._div_yigin.pop()
        elif tag == "a":
            if self._a_href is not None:
                self._baglanti_isle(self._a_href, "".join(self._a_metni), self._a_girdide)
            self._a_href = None
            self._a_metni = []
            self._a_girdide = False
        elif tag == "u":
            self._u_derinlik = max(0, self._u_derinlik - 1)
            if self._u_derinlik == 0 and self._u_metni:
                metin = _sadelestir("".join(self._u_metni))
                if metin:
                    self._baslik_isle(metin)
                self._u_metni = []

    def handle_data(self, data: str) -> None:
        self._tum_metin.append(data)
        if self._baslik_modu is not None:
            self._baslik_metni.append(data)
        if self._a_href is not None:
            self._a_metni.append(data)
        if self._u_derinlik > 0:
            self._u_metni.append(data)

    def _baslik_isle(self, metin: str) -> None:
        """Bolum veya alt baslik olarak isle."""
        if self._baslik_modu == "alt" or (
            self._baslik_modu == "baslik"
            and _BOLUM_DESENI.search(metin.upper()) is None
            and _bolum_adi(metin.upper()) is None
        ):
            self.alt_baslik = metin
            return
        ad = _bolum_adi(metin.upper())
        if ad is not None:
            self.bolum = ad
            self._bolum_goruldu = True
            self.alt_baslik = None
        else:
            # bolum degil: alt baslik olarak dus
            self.alt_baslik = metin

    def _ayni_sayinin_belgesi(self, url: str) -> bool:
        """Baglanti bu fihristin gunune ait arsiv belgesine mi gidiyor?

        Onceki/sonraki sayi baglantilari baska tarihe gider ve boylece elenir.
        """
        if not self._belge_tarihi:
            return False
        es = _ARSIV_BELGE.search(urlparse(url).path)
        return bool(es and es.group("gun") == self._belge_tarihi)

    def _baglanti_isle(self, href: str, metin: str, girdide: bool) -> None:
        temiz = _sadelestir(metin)
        if not temiz:
            return
        url = _baglanti_coz(self.kaynak, href)
        tireli = temiz[0] in _TIRELER
        if not girdide and not tireli and not self._ayni_sayinin_belgesi(url or ""):
            return  # gezinme baglantilari (Onceki/Sonraki Sayi, PDF Goruntule vb.)
        if _ALT_BASLIK_DESENI.match(temiz) and not tireli:
            self.alt_baslik = temiz
            return
        baslik = temiz.lstrip(_TIRELER).strip()
        if len(baslik) < 8 or url is None:
            return
        self.girdiler.append(
            Girdi(baslik=baslik, baglanti=url, bolum=self.bolum, alt_baslik=self.alt_baslik)
        )


def ayristir(metin_html: str, kaynak_url: str, tarih: str = "", mukerrer: int = 0) -> Fihrist:
    """HTML fihrist sayfasini Fihrist'e cevirir; yapi taninmazsa YapiHatasi firlatir."""
    p = _Ayrisitirici(kaynak_url)
    p.feed(metin_html)
    p.close()
    tum = _sadelestir("".join(p._tum_metin))
    if _YAYIM_YOK.search(tum):
        raise YapiHatasi(
            "sayfa henuz yayimlanmamis (site, 'Resmî Gazete'nin yayımlanması "
            f"çalışmaları devam etmektedir' duyurusunu dondurdu). Kaynak: {kaynak_url}"
        )
    # meta veri: "02 Kasım 2026 Tarihli ve 33418 Sayılı Resmî Gazete"
    baslik: str | None = None
    sayi: str | None = None
    es = _SAYI_DESENI.search(tum)
    if es:
        sayi = es.group("sayi")
        baslik = f"{es.group('gun')} {es.group('ay')} {es.group('yil')} Tarihli ve {sayi} Sayılı"
        if es.group("mukerrer"):
            baslik += f" {es.group('mukerrer')}. Mükerrer"
            if mukerrer <= 0:
                mukerrer = int(es.group("mukerrer"))
    # ayni belge iki kez baglanabiliyor: baglantiya gore tekille
    tekrarsiz: list[Girdi] = []
    gorulen: set[str] = set()
    for g in p.girdiler:
        if g.baglanti in gorulen:
            continue
        gorulen.add(g.baglanti)
        tekrarsiz.append(g)
    if not p._bolum_goruldu and not tekrarsiz:
        raise YapiHatasi(
            "sayfa yapisi taninamadi (fihrist bolumleri ve girdileri bulunamadi); "
            f"site yerlesimi degismis olabilir. Kaynak: {kaynak_url}"
        )
    if not tekrarsiz:
        raise YapiHatasi(
            f"fihrist girdisi bulunamadi; bos sonuc sessizce dondurulmuyor. Kaynak: {kaynak_url}"
        )
    return Fihrist(
        tarih=tarih,
        mukerrer=mukerrer,
        kaynak=kaynak_url,
        baslik=baslik,
        sayi=sayi,
        girdiler=tekrarsiz,
    )

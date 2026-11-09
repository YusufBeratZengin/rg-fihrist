"""Kibar (rate-limited) HTTP indirici.

Politika:

- Istekler arasinda en az ``MIN_ARALIK_SN`` (2 sn) beklenir. Bu bir alt sinirdir:
  daha kucuk bir deger verilse bile kirpilir, boylece kaynak sunucuya karsi kibar
  davranis kapatilamaz.
- Tanimlayici bir ``User-Agent`` gonderilir.
- ``robots.txt`` saygiya gosterilir (stdlib ``urllib.robotparser``).
  ``robots.txt`` okunamazsa (ag hatasi) erisim serbest varsayilir; bu bilincli
  bir tercihtir (``urllib`` varsayilani) ve ``Indirici.robots_uyarisi`` alaninda
  kullaniciya bildirilir. Sitenin robots.txt dosyasi bu URL'leri yasaklarsa
  ``RobotsHatasi`` firlatilir.
- Eski arsiv sayfalari Windows-1254 kodludur; kodlama
  ``Content-Type`` -> ``<meta charset>`` -> UTF-8 denemesi -> Windows-1254
  sirasiyla algilanir.
"""

from __future__ import annotations

import http.client
import math
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from rg_fihrist._surum import __version__ as SURUM

TABAN_URL = "https://www.resmigazete.gov.tr"
MIN_ARALIK_SN = 2.0
VARSAYILAN_TIMEOUT = 30.0
USER_AGENT = f"rg-fihrist/{SURUM} (+https://github.com/YusufBeratZengin/rg-fihrist)"

GetirFn = Callable[[str, dict[str, str], float], tuple[bytes, dict[str, str], int]]


class IndiriciProtokolu(Protocol):
    """``Indirici`` yerine gecmesi gereken en kucuk arayuz (testler icin enjeksiyon)."""

    robots_uyarisi: str | None

    def indir(self, url: str) -> Sayfa:
        """URL'yi indirip ``Sayfa`` dondurur."""
        ...


class AgHatasi(Exception):
    """Ag/HTTP hatasi: sayfa indirilemedi."""


class RobotsHatasi(Exception):
    """robots.txt bu URL'ye erisime izin vermiyor."""


@dataclass
class Sayfa:
    """Indirilen ham sayfa ve cozulmus metni."""

    url: str
    ham: bytes
    content_type: str | None
    kodlama: str
    metin: str


def fihrist_url(tarih: date, mukerrer: int = 0, taban: str = TABAN_URL) -> str:
    """Modern fihrist gorunumunun URL'si: /fihrist?tarih=YYYY-MM-DD[&mukerrer=N]."""
    if mukerrer < 0:
        raise ValueError("mukerrer negatif olamaz")
    url = f"{taban}/fihrist?tarih={tarih.isoformat()}"
    if mukerrer > 0:
        url += f"&mukerrer={mukerrer}"
    return url


def arsiv_url(tarih: date, mukerrer: int = 0, taban: str = TABAN_URL) -> str:
    """Ham arsiv sayfasinin URL'si: /eskiler/YYYY/MM/YYYYMMDD[-N].htm."""
    if mukerrer < 0:
        raise ValueError("mukerrer negatif olamaz")
    yy = f"{tarih.year:04d}"
    mm = f"{tarih.month:02d}"
    dd = f"{tarih.day:02d}"
    ad = f"{yy}{mm}{dd}"
    if mukerrer > 0:
        ad += f"-{mukerrer}"
    return f"{taban}/eskiler/{yy}/{mm}/{ad}.htm"


def aralik_dogrula(deger: float) -> float:
    """Bekleme araligini alt sinira gore kirp (NaN/sonsuz/gecersiz -> varsayilan).

    Sonsuz bir aralik ``time.sleep`` icinde ``OverflowError`` ile cokerdi; bu
    yuzden sonlu olmayan degerler kibarlik alt sinirina cekilir.
    """
    try:
        sayi = float(deger)
    except (TypeError, ValueError):
        return MIN_ARALIK_SN
    if not math.isfinite(sayi):
        return MIN_ARALIK_SN
    return max(MIN_ARALIK_SN, sayi)


_META_KODLAMA = re.compile(rb"""charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""", re.IGNORECASE)


def kodlama_algila(content_type: str | None, ham: bytes) -> str:
    """Kodlamayi bul: Content-Type, <meta charset>, UTF-8 denemesi, Windows-1254."""
    if content_type:
        es = _META_KODLAMA.search(content_type.encode("latin-1", "replace"))
        if es:
            return es.group(1).decode("ascii", "replace").lower()
    es = _META_KODLAMA.search(ham[:8192])
    if es:
        return es.group(1).decode("ascii", "replace").lower()
    try:
        ham.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "windows-1254"


def metin_coz(ham: bytes, kodlama: str) -> str:
    """Ham baytlari bilinen kodlamayla coz; tanimayan kodlama icin UTF-8'e duser."""
    try:
        return ham.decode(kodlama)
    except (LookupError, UnicodeDecodeError):
        return ham.decode("utf-8", "replace")


def _varsayilan_getir(
    url: str, headers: dict[str, str], timeout: float
) -> tuple[bytes, dict[str, str], int]:
    """urllib ile GET istegi; (govde, headerlar, durum kodu) dondurur."""
    try:
        istek = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(istek, timeout=timeout) as yanit:
            son = yanit.geturl()
            if urlparse(son).path in ("", "/") and urlparse(url).path not in ("", "/"):
                raise AgHatasi(
                    f"istek {son} adresine yonlendirildi; istenen sayfa bulunamadi "
                    f"(gecersiz tarih veya sayi olabilir): {url}"
                )
            govde = yanit.read()
            hdrs = {k.lower(): v for k, v in yanit.headers.items()}
            return govde, hdrs, 200
    except urllib.error.HTTPError as e:
        raise AgHatasi(f"HTTP {e.code} hatasi: {url}") from e
    except urllib.error.URLError as e:
        raise AgHatasi(f"URL hatasi ({e.reason}): {url}") from e
    except (ValueError, http.client.InvalidURL) as e:  # orn. "http://[::1/x"
        raise AgHatasi(f"gecersiz URL ({e}): {url}") from e


class Indirici:
    """Kibar indirici: en az 2 sn aralik + User-Agent + robots.txt uyumu.

    Testlerde ``getir_fn``, ``sleep_fn`` ve ``saat_fn`` enjekte edilerek ag
    kullanmadan davranis olculur.
    """

    def __init__(
        self,
        min_aralik: float = MIN_ARALIK_SN,
        user_agent: str = USER_AGENT,
        timeout: float = VARSAYILAN_TIMEOUT,
        getir_fn: GetirFn | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        saat_fn: Callable[[], float] = time.monotonic,
        robots: bool = True,
    ) -> None:
        self.min_aralik = aralik_dogrula(min_aralik)
        self.user_agent = user_agent
        self.timeout = timeout
        self._getir = getir_fn or _varsayilan_getir
        self._sleep = sleep_fn
        self._saat = saat_fn
        self.robots = robots
        self.robots_uyarisi: str | None = None
        self._son_istek: float | None = None
        self._robots_onbellek: dict[str, RobotFileParser] = {}

    def _bekle(self) -> None:
        """Son istekten bu yana en az ``min_aralik`` saniye gecmesini sagla."""
        if self._son_istek is not None:
            gecen = self._saat() - self._son_istek
            if gecen < self.min_aralik:
                self._sleep(self.min_aralik - gecen)
        self._son_istek = self._saat()

    def _robots_parser(self, url: str) -> RobotFileParser | None:
        """Host icin robots.txt'yi (onbellekten) cek; okunamazsa serbest birak."""
        parca = urlparse(url)
        if parca.scheme not in ("http", "https"):
            return None
        ana = f"{parca.scheme}://{parca.netloc}"
        if ana in self._robots_onbellek:
            return self._robots_onbellek[ana]
        rp = RobotFileParser()
        rp.set_url(f"{ana}/robots.txt")
        try:
            self._bekle()
            govde, _, durum = self._getir(
                f"{ana}/robots.txt", {"User-Agent": self.user_agent}, self.timeout
            )
            if durum == 200:
                rp.parse(govde.decode("utf-8", "replace").splitlines())
            else:
                rp.parse([])  # robots.txt yoksa tumune izin var
        except AgHatasi as e:
            # Bilincli tercih: robots.txt okunamazsa erisim durdurulmaz, ama
            # kullaniciya bildirilir; sessiz varsayim yapilmaz.
            self.robots_uyarisi = (
                f"robots.txt okunamadi ({e}); erisim serbest varsayildi. "
                "--robots-yok ile bu denetimi tamamen kapatabilirsiniz."
            )
            rp.parse([])
        self._robots_onbellek[ana] = rp
        return rp

    def indir(self, url: str) -> Sayfa:
        """URL'yi indirir ve kodlanmis metne cevirir."""
        if self.robots:
            rp = self._robots_parser(url)
            if rp is not None and not rp.can_fetch(self.user_agent, url):
                raise RobotsHatasi(f"robots.txt bu URL'ye izin vermiyor: {url}")
        self._bekle()
        govde, hdrs, _durum = self._getir(url, {"User-Agent": self.user_agent}, self.timeout)
        content_type = hdrs.get("content-type")
        kodlama = kodlama_algila(content_type, govde)
        return Sayfa(
            url=url,
            ham=govde,
            content_type=content_type,
            kodlama=kodlama,
            metin=metin_coz(govde, kodlama),
        )

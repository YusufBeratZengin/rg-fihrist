"""Gercek HTTP yolunun uctan uca testi: yerel sunucu, urllib, robots.txt, kodlama.

Diger testler ``getir_fn`` enjekte eder; burada ise gercek soket ve gercek
``urllib`` kullanilir. Sunucu 127.0.0.1 uzerinde calisir, disariya cikilmaz ve
kaydedilmis fixture'lar servis edilir.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from rg_fihrist.ayristir import ayristir
from rg_fihrist.indir import USER_AGENT, AgHatasi, Indirici, RobotsHatasi

FIXTURE_DIZINI = Path(__file__).with_name("fixtures")
MODERN_GOVDE = (FIXTURE_DIZINI / "fihrist-2026-11-03.htm").read_bytes()
ARSIV_GOVDE = (FIXTURE_DIZINI / "arsiv-2015-03-17.htm").read_bytes()
ROBOTS = b"User-agent: *\nDisallow: /gizli\n"

Yanit = tuple[bytes, str, int]


class YerelSunucu:
    """127.0.0.1 uzerinde verilen yollari servis eden kucuk HTTP sunucusu."""

    def __init__(self, yanitlar: dict[str, Yanit]) -> None:
        self.yanitlar = dict(yanitlar)
        self.ajanslar: list[str] = []
        self.istekler: list[str] = []
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._isleyici())
        self._is_parcacigi = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def _isleyici(self) -> type[BaseHTTPRequestHandler]:
        sunucu = self

        class Isleyici(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                sunucu.istekler.append(self.path)
                sunucu.ajanslar.append(self.headers.get("User-Agent", ""))
                govde, tur, kod = sunucu.yanitlar.get(
                    self.path, (b"bulunamadi", "text/plain; charset=utf-8", 404)
                )
                self.send_response(kod)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass  # test ciktisini kirletme

        return Isleyici

    def url(self, yol: str) -> str:
        port = self._httpd.server_address[1]
        return f"http://127.0.0.1:{port}{yol}"

    def __enter__(self) -> YerelSunucu:
        self._is_parcacigi.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._is_parcacigi.join(timeout=5)


def _indirici() -> Indirici:
    # Uyku enjekte edilir: gercek HTTP yolu olculur, 2 sn beklemek gerekmez.
    return Indirici(sleep_fn=lambda _s: None, timeout=5.0)


def test_modern_sayfa_gercek_http_uzerinden_okunur() -> None:
    with YerelSunucu(
        {
            "/robots.txt": (ROBOTS, "text/plain", 200),
            "/fihrist?tarih=2026-11-03": (MODERN_GOVDE, "text/html; charset=utf-8", 200),
        }
    ) as sunucu:
        url = sunucu.url("/fihrist?tarih=2026-11-03")
        sayfa = _indirici().indir(url)

    assert sayfa.kodlama == "utf-8"
    fihrist = ayristir(sayfa.metin, url, tarih="2026-11-03")
    assert len(fihrist.girdiler) == 13
    assert fihrist.sayi == "33419"
    # robots.txt ve sayfa istegi projeyi tanitan ajani tasimali.
    assert sunucu.ajanslar == [USER_AGENT, USER_AGENT]


def test_eski_arsiv_windows1254_olarak_cozulur() -> None:
    with YerelSunucu(
        {
            "/robots.txt": (ROBOTS, "text/plain", 200),
            "/eskiler/2015/03/20150317.htm": (ARSIV_GOVDE, "text/html", 200),
        }
    ) as sunucu:
        url = sunucu.url("/eskiler/2015/03/20150317.htm")
        sayfa = _indirici().indir(url)

    assert sayfa.kodlama == "windows-1254"
    fihrist = ayristir(sayfa.metin, url, tarih="2015-03-17")
    assert len(fihrist.girdiler) == 6


def test_robots_yasagi_gercek_istekte_de_uygulanir() -> None:
    with YerelSunucu(
        {"/robots.txt": (ROBOTS, "text/plain", 200), "/gizli": (b"x", "text/html", 200)}
    ) as sunucu:
        with pytest.raises(RobotsHatasi):
            _indirici().indir(sunucu.url("/gizli"))
        assert sunucu.istekler == ["/robots.txt"]


def test_cli_sureci_gercek_http_ile_json_uretir(tmp_path: Path) -> None:
    """Uctan uca: gercek surec, gercek soket, --cikti dosyasi ve cikis kodu 0."""
    kok = Path(__file__).resolve().parents[1]
    ortam = dict(os.environ, PYTHONPATH=str(kok / "src"))
    hedef = tmp_path / "fihrist.json"
    with YerelSunucu(
        {
            "/robots.txt": (ROBOTS, "text/plain", 200),
            "/fihrist?tarih=2026-11-03": (MODERN_GOVDE, "text/html; charset=utf-8", 200),
        }
    ) as sunucu:
        url = sunucu.url("/fihrist?tarih=2026-11-03")
        surec = subprocess.run(
            [
                sys.executable,
                "-m",
                "rg_fihrist",
                "bugun",
                "--url",
                url,
                "--json",
                "--cikti",
                str(hedef),
            ],
            cwd=kok,
            env=ortam,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    assert surec.returncode == 0, surec.stderr
    veri = json.loads(hedef.read_text(encoding="utf-8"))
    assert veri["girdi_sayisi"] == 13
    assert veri["kodlama"] == "utf-8"
    assert veri["kaynak"] == url


def test_http_hatasi_ag_hatasi_olarak_bildirilir() -> None:
    with YerelSunucu(
        {"/robots.txt": (ROBOTS, "text/plain", 200), "/fihrist": (b"hata", "text/plain", 503)}
    ) as sunucu:
        with pytest.raises(AgHatasi) as hata:
            _indirici().indir(sunucu.url("/fihrist"))
    assert "HTTP 503" in str(hata.value)

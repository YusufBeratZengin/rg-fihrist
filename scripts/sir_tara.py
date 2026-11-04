#!/usr/bin/env python3
"""Depoda sir/anahtar aramasi yapar (pre-commit ve check.sh tarafindan kullanilir).

Kurallar:

- Yalnizca *bulundu/bulunmadi* bilgisi ve kural adi yazdirilir; eslesen deger
  asla ekrana basilmaz ve dosyaya yazilmaz.
- Ikili dosyalar, sanal ortamlar ve git nesneleri atlanir.
- Kullanim: ``python scripts/sir_tara.py [yol ...]`` (varsayilan: depo koku).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent

ATLANAN_DIZINLER = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
}

DESENLER: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-erisim-anahtari", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-jetonu", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("slack-jetonu", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("ozel-anahtar-blogu", re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    (
        "atanmis-gizli-deger",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password|passwd)\b"
            r"\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"
        ),
    ),
)

METIN_UZANTILARI = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".cfg",
    ".ini",
    ".yml",
    ".yaml",
    ".json",
    ".sh",
    ".ps1",
    ".html",
    ".htm",
    ".xml",
    ".csv",
    ".ts",
    ".js",
    ".ino",
}


def _adaylar(yollar: list[str]) -> list[Path]:
    if not yollar:
        yollar = [str(KOK)]
    sonuc: list[Path] = []
    for yol in yollar:
        p = Path(yol)
        if p.is_dir():
            for dosya in p.rglob("*"):
                if dosya.is_file() and not (ATLANAN_DIZINLER & set(dosya.parts)):
                    sonuc.append(dosya)
        elif p.is_file():
            sonuc.append(p)
    return sorted(set(sonuc))


def tara(yollar: list[str]) -> list[str]:
    """Bulunan ihlalleri ``yol:satir:kural`` biciminde dondurur (deger yok)."""
    bulgular: list[str] = []
    for dosya in _adaylar(yollar):
        if dosya.suffix.lower() not in METIN_UZANTILARI:
            continue
        try:
            metin = dosya.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for no, satir in enumerate(metin.splitlines(), start=1):
            for ad, desen in DESENLER:
                if desen.search(satir):
                    bulgular.append(f"{dosya.relative_to(KOK)}:{no}:{ad}")
    return bulgular


def main(argv: list[str]) -> int:
    bulgular = tara(argv)
    if bulgular:
        print("sir taramasi: SUPHELI ESLEME BULUNDU (degerler gizlendi)", file=sys.stderr)
        for b in bulgular:
            print(f"  {b}", file=sys.stderr)
        return 1
    print("sir taramasi: temiz")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

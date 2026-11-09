"""rg-fihrist: Resmi Gazete gunluk fihristini JSON/RSS'e ceviren acik kaynak CLI.

Sifir calisma zamani bagimliligi: yalnizca Python standart kutuphanesi kullanilir.
"""

from rg_fihrist._surum import __version__
from rg_fihrist.ara import ara, eslesme_mi, girdi_metni, turkce_kucuk
from rg_fihrist.ayristir import Fihrist, Girdi, YapiHatasi, ayristir
from rg_fihrist.indir import (
    MIN_ARALIK_SN,
    AgHatasi,
    Indirici,
    RobotsHatasi,
    Sayfa,
    aralik_dogrula,
    arsiv_url,
    fihrist_url,
    kodlama_algila,
    metin_coz,
)
from rg_fihrist.rss import rss_olustur

__all__ = [
    "MIN_ARALIK_SN",
    "AgHatasi",
    "Fihrist",
    "Girdi",
    "Indirici",
    "RobotsHatasi",
    "Sayfa",
    "YapiHatasi",
    "ara",
    "aralik_dogrula",
    "arsiv_url",
    "ayristir",
    "eslesme_mi",
    "fihrist_url",
    "girdi_metni",
    "kodlama_algila",
    "metin_coz",
    "rss_olustur",
    "turkce_kucuk",
    "__version__",
]

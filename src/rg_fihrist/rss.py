"""RSS 2.0 ciktisi uretir (standart kutuphane, ek bagimlilik yok).

Kararlarin tam metni yayinlanmaz; her oge baslik + baglanti tasir. Kanal ve
oge ``pubDate`` degeri, sayinin yayimlandigi gunun baslangicidir (00:00 TR);
fihrist sayfasi kesin yayim saatini vermedigi icin saat uydurulmaz.
``lastBuildDate`` beslemenin uretildigi andir.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, time, timedelta, timezone
from email.utils import format_datetime

from rg_fihrist._surum import __version__
from rg_fihrist.ayristir import Fihrist

TR_SAAT = timezone(timedelta(hours=3))  # Türkiye saati (UTC+3)


def _tarih_ayristir(tarih: str) -> date:
    """'YYYY-MM-DD' -> date; hatali tarih uydurulmaz, ValueError firlatilir."""
    try:
        return date.fromisoformat(tarih)
    except (ValueError, TypeError):
        raise ValueError(f"gecersiz tarih: {tarih!r} (YYYY-MM-DD bekleniyor)") from None


def rss_olustur(fihrist: Fihrist, arama: str | None = None, simdi: datetime | None = None) -> str:
    """Fihrist'ten RSS 2.0 XML metni uretir (girdi baglantilari guid olur)."""
    uretim = simdi or datetime.now(TR_SAAT)
    if uretim.tzinfo is None:
        uretim = uretim.replace(tzinfo=TR_SAAT)
    uretim = uretim.astimezone(TR_SAAT)  # besleme her zaman Turkiye saatinde

    # Eski API uyumu: tarihsiz fihrist icin Turkiye saatindeki bugunu kullan.
    gun = _tarih_ayristir(fihrist.tarih) if fihrist.tarih else uretim.date()
    tarih_metni = gun.isoformat()
    yayin_tarihi = datetime.combine(gun, time(0, 0), tzinfo=TR_SAAT)

    mk = f" {fihrist.mukerrer}. mükerrer" if fihrist.mukerrer > 0 else ""
    kanal_baslik = f"Resmi Gazete Fihristi {tarih_metni}{mk}"
    if fihrist.sayi:
        kanal_baslik += f" (sayı {fihrist.sayi})"

    kok = ET.Element("rss", {"version": "2.0"})
    kanal = ET.SubElement(kok, "channel")
    ET.SubElement(kanal, "title").text = kanal_baslik
    ET.SubElement(kanal, "link").text = fihrist.kaynak
    aciklama = f"T.C. Resmi Gazete gunluk fihristi ({tarih_metni}{mk})."
    if arama:
        aciklama += f" Arama: '{arama}'."
    aciklama += " Yalnizca baslik ve baglanti icerir; tam metin degildir."
    ET.SubElement(kanal, "description").text = aciklama
    ET.SubElement(kanal, "language").text = "tr"
    ET.SubElement(kanal, "pubDate").text = format_datetime(yayin_tarihi)
    ET.SubElement(kanal, "lastBuildDate").text = format_datetime(uretim)
    ET.SubElement(kanal, "generator").text = f"rg-fihrist {__version__}"
    ET.SubElement(kanal, "ttl").text = "1440"

    for girdi in fihrist.girdiler:
        oge = ET.SubElement(kanal, "item")
        ET.SubElement(oge, "title").text = girdi.baslik
        ET.SubElement(oge, "link").text = girdi.baglanti
        ET.SubElement(oge, "guid", {"isPermaLink": "true"}).text = girdi.baglanti
        ET.SubElement(oge, "pubDate").text = format_datetime(yayin_tarihi)
        ET.SubElement(oge, "category").text = girdi.bolum
        detay = f"Bölüm: {girdi.bolum}"
        if girdi.alt_baslik:
            detay += f" — {girdi.alt_baslik}"
        ET.SubElement(oge, "description").text = detay

    ET.indent(kok, space="  ")
    return ET.tostring(kok, encoding="unicode", xml_declaration=True)

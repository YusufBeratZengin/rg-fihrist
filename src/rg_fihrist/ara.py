"""Turkce duyarli anahtar sozcuk aramasi.

Kurallar:

- Turkce buyuk/kucuk harf: ``I`` -> ``ı``, ``İ`` -> ``i`` kuraliyla kucultme.
- Ek duyarli eslesme **onek** esaslidir: sorgu jetonu metin jetonunun basindan
  eslesmelidir (``veri`` -> ``verilerin``, ``vergi`` -> ``vergisi``). Metnin
  ortasindaki bir parca eslesme sayilmaz; ``ara`` sorgusu ``taraftar``
  jetonuyla eslesmez.
- Unsuz yumusamasi tek harfte karsilanir: ``kitap`` -> ``kitabı``,
  ``ağaç`` -> ``ağacı``, ``kanat`` -> ``kanadı`` (p->b, ç->c, t->d) ve
  ``yönetmelik`` -> ``yönetmeliği``, ``renk`` -> ``rengi`` (k->ğ veya k->g;
  hangisinin dogru oldugu ekin ilk unlusune baglidir, ikisi de denenir).
- Tum sorgu jetonlari eslesmedigi surece girdi elenmez (AND mantigi).

Sinirlar: onek eslesmesi govde degisimlerini (``kitap``/``kitaplar`` disinda
kalan ``iyelik`` eklerindeki unlu dusmesi: ``ağız`` -> ``ağzı``) kapsamaz.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from rg_fihrist.ayristir import Girdi

_JETON = re.compile(r"[0-9a-zçğıöşü]+")

# Turkce unsuz yumusamasi: sozcuk sonundaki sert unsuz, ek alirken yumusar.
# ``k`` iki bicimde yumusayabilir: unluden sonra ``ğ`` (yönetmelik -> yönetmeliği),
# ``n``den sonra ``g`` (renk -> rengi); ikisi de denenir.
_YUMUSAMA: dict[str, tuple[str, ...]] = {
    "p": ("b",),
    "ç": ("c",),
    "t": ("d",),
    "k": ("ğ", "g"),
}


def turkce_kucuk(metin: str) -> str:
    """Turkce alfabeye duyarli kucuk harfe cevir (I->ı, İ->i)."""
    return metin.replace("I", "ı").replace("İ", "i").lower()


def jetonler(metin: str) -> list[str]:
    """Metni Turkce duyarli jetonlara bol."""
    return _JETON.findall(turkce_kucuk(metin))


def _jeton_eslesir(sorgu_jetonu: str, metin_jetonu: str) -> bool:
    """Sorgu jetonu metin jetonunun basindan (yumusama dahil) eslesiyor mu?"""
    if len(sorgu_jetonu) < 2:
        return sorgu_jetonu == metin_jetonu
    if metin_jetonu.startswith(sorgu_jetonu):
        return True
    son = sorgu_jetonu[-1]
    if len(sorgu_jetonu) >= 3 and son in _YUMUSAMA:
        govde = sorgu_jetonu[:-1]
        return any(metin_jetonu.startswith(govde + yumusak) for yumusak in _YUMUSAMA[son])
    return False


def eslesme_mi(sorgu: str, metin: str) -> bool:
    """Sorgunun tum jetonlari metinde (onek duyarli) bulunuyor mu?"""
    sorgu_jetonlari = jetonler(sorgu)
    if not sorgu_jetonlari:
        return False
    metin_jetonlari = jetonler(metin)
    for sj in sorgu_jetonlari:
        if not any(_jeton_eslesir(sj, mj) for mj in metin_jetonlari):
            return False
    return True


def girdi_metni(girdi: Girdi) -> str:
    """Bir girdinin aranabilir metni: baslik + alt baslik + bolum."""
    return f"{girdi.baslik} {girdi.alt_baslik or ''} {girdi.bolum}"


def ara(girdiler: Iterable[Girdi], sorgu: str) -> list[Girdi]:
    """Girdileri Turkce duyarli sorguya gore suz (baslik + alt baslik + bolum)."""
    if not sorgu.strip():
        return list(girdiler)
    return [g for g in girdiler if eslesme_mi(sorgu, girdi_metni(g))]

# rg-fihrist

Resmî Gazete'nin günlük **fihristini** yapılandırılmış JSON veya RSS 2.0'a
çeviren, Türkçe duyarlı anahtar sözcük süzgeci olan komut satırı aracı. Çalışma
zamanı bağımlılığı yoktur.

Fihrist, o günkü Resmî Gazete'nin içindekiler sayfasıdır: bölüm, alt başlık,
belge başlığı ve belgeye bağlantı. Hukukçuların, mali müşavirlerin ve uyum
ekiplerinin her sabah elle taradığı şey tam olarak budur; bu araç onu indirir,
bölümlere ayırır ve yalnız ilgilendiğiniz başlıkları süzmenizi sağlar.

- Bölümler: `yasama`, `yurutme`, `yargi`, `ilan`, `diger`.
- Türkçe büyük/küçük harf duyarlılığı (`I` → `ı`, `İ` → `i`) ve ek duyarlı
  önek eşleşmesi (`vergi` → `vergisi`, `kitap` → `kitabı`).
- İki sayfa yerleşimi de desteklenir: güncel `/fihrist?tarih=…` görünümü
  (UTF-8) ve eski `/eskiler/YYYY/MM/YYYYMMDD.htm` arşivi (Windows-1254).
- Kibar varsayılanlar: projeyi tanıtan `User-Agent`, robots.txt'e uyum ve
  hiçbir bayrakla düşürülemeyen **en az 2 saniye** istek aralığı.

**Bu araç resmî bir kaynak değildir.** Herkese açık bir sayfayı okuyup yalnız
başlık ve bağlantıları kopyalar. Bir belgeye dayanmadan önce
<https://www.resmigazete.gov.tr/> üzerinden doğrulayın.

## Kurulum

```console
# kaynaktan (PyPI sürümü henüz yayımlanmadı):
$ python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
$ pip install -e .
# veya komutu yalıtılmış kurun:
$ pipx install .
```

Python 3.10 veya üzeri gerekir; çalışma zamanı bağımlılığı yoktur. İlk sürüm
PyPI'da yayımlandığında en kısa yol `pipx install rg-fihrist` olacak.

## 30 saniyelik örnek

```console
$ rg-fihrist tarih 2026-11-03 --ara "tebliğ"
Resmi Gazete fihristi - 2026-11-03 (sayi 33419)
Baslik: 03 Kasım 2026 Tarihli ve 33419 Sayılı
Kaynak: https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03
Arama: tebliğ
Girdi: 2

[YURUTME] (2)
  - Özelleştirme İdaresi Başkanlığının 30/10/2026 Tarihli ve 2026/ÖİB-K-46 Sayılı Kararı (TEBLİĞLER)
    https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-2.pdf
  - Avukatlık Asgari Ücret Tarifesi (TEBLİĞLER)
    https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-3.htm
```

Aynı veri JSON olarak (`--json`; gerçek çıktıda 13 girdi vardır, burada
kısaltıldı):

```json
{
  "kaynak": "https://www.resmigazete.gov.tr/fihrist?tarih=2026-11-03",
  "tarih": "2026-11-03",
  "mukerrer": 0,
  "sayi": "33419",
  "baslik": "03 Kasım 2026 Tarihli ve 33419 Sayılı",
  "girdi_sayisi": 13,
  "girdiler": [
    {
      "baslik": "Avukatlık Asgari Ücret Tarifesi",
      "baglanti": "https://www.resmigazete.gov.tr/eskiler/2026/11/20261103-3.htm",
      "bolum": "yurutme",
      "alt_baslik": "TEBLİĞLER"
    }
  ],
  "arama": [],
  "kodlama": "utf-8"
}
```

## Komutlar

```console
rg-fihrist bugun [seçenekler]                 # bugünün fihristi
rg-fihrist tarih 2026-11-02 [seçenekler]      # belirli bir gün (YYYY-AA-GG)
```

Her iki komutta geçerli seçenekler:

| Seçenek | Anlamı |
| --- | --- |
| `--json` | gruplanmış metin yerine stdout'a JSON |
| `--cikti DOSYA` | raporu/JSON'u dosyaya yaz |
| `--rss DOSYA` | ayrıca RSS 2.0 beslemesi yaz |
| `--ara SORGU` | Türkçe duyarlı süzgeç; tekrarlanabilir (VEYA) |
| `--bolum yasama\|yurutme\|yargi\|ilan\|diger` | yalnız bu bölümler; tekrarlanabilir |
| `--ilan-yok` | ilan bölümünü çıkar |
| `--mukerrer N` | o günün N. mükerrer sayısını iste |
| `--ham` | `/fihrist` yerine eski `/eskiler/...` arşiv sayfasını oku |
| `--url URL` | doğrudan `http(s)` URL ver (arşiv, ayna, test) |
| `--min-aralik SN` | istekler arası bekleme; 2'nin altına inemez |
| `--timeout SN` | istek zaman aşımı (varsayılan 30) |
| `--robots-yok` | robots.txt denetimini kapat (yalnız yerel test) |

`--cikti` ile `--rss` aynı dosyayı gösteremez: ikinci yazım birincinin üzerine
yazacağı için bu birleşim baştan reddedilir (sembolik bağlar dahil). İki dosya
da atomik yazılır — hedef dizinde geçici bir dosya oluşturulup yerine taşınır —
böylece yarıda kalan veya başarısız bir çalışma önceki raporu/beslemeyi bozmaz.
Erken kapanan bir boru (`rg-fihrist bugun | head`) traceback yerine sessizce
biter.

### Üç gerçek senaryo

1. **Sabah taraması.** `rg-fihrist bugun` — tek ekranda, bölümlere ayrılmış.
2. **Konu takibi.** `rg-fihrist bugun --ara "kişisel veri" --rss kvkk.xml` —
   `kvkk.xml` dosyasını herhangi bir besleme okuyucusuna abone edin.
3. **Arşiv araması.** `rg-fihrist tarih 2015-03-17 --ham --ara "yönetmelik"` —
   Windows-1254 kodlu eski sayfayı okur, eşleşen 4 yönetmeliği listeler.

### Türkçe arama davranışı

Eşleşme jeton bazındadır ve Türkçe harf katlamasından sonra **önek** üzerinden
yapılır:

| Sorgu | Eşleşir | Eşleşmez |
| --- | --- | --- |
| `vergi` | `vergisi`, `Vergi Usul Kanunu` | `verimsiz` |
| `veri` | `verilerin`, `Veri Sorumlusu` | — |
| `kitap` | `kitabı` (p → b yumuşaması) | — |
| `yönetmelik` | `yönetmeliği`, `yönetmeliğinde` (k → ğ) | `yönetici` |
| `renk` | `rengi` (n'den sonra k → g) | `kürek` |
| `ara` | `arama` | `taraftar` (yalnız iç parça) |

Tüm sorgu jetonları eşleşmelidir (VE); birden çok `--ara` bayrağı VEYA ile
birleşir. Tek harfli jetonlar yalnız tam eşleşir. Sözcük içinde ünlü düşmesi
(`ağız` → `ağzı`) kapsanmaz; bunun için gerçek bir gövdeleyici gerekir.

## Kibar istek politikası, robots.txt ve kullanım koşulları

- Sayfa başına tek istek, en çok 2 saniyede bir istek ve projeyi tanıtan bir
  `User-Agent`. 2 saniyelik alt sınır hem `Indirici` hem CLI ayrıştırıcısında
  uygulanır; `--min-aralik 0` bile onu kapatamaz.
- `robots.txt` her sunucu için bir kez indirilir ve uygulanır. Okunamazsa (ağ
  hatası) erişim **serbest** bırakılır — `urllib` varsayılanı — ve CLI sessiz
  kalmak yerine stderr'e uyarı yazar.
- Yalnız başlık ve bağlantı kopyalanır. Kararların tam metni hiçbir zaman
  indirilmez, saklanmaz veya yeniden yayımlanmaz; her girdi resmî sayfaya
  bağlanır.
- Sitenin kullanım koşulları bu sürümde ayrıntılı incelenmedi; robots.txt
  2026-11-04'te okundu ve `/fihrist` yolunu engelleyen kural yoktu. Yoğun veya
  otomatik kullanımdan önce yeniden kontrol edin ve istek aralığını koruyun.

## Kişisel veri

`ilan` bölümündeki başlıklar gerçek kişi adları içerebilir (miras ve iflas
ilanları gibi). Bu araç ilanların kendisini değil başlıklarını kopyalar ve
bağlantılı belgeleri hiç indirmez. Bu bölümü çıktıda veya beslemede hiç
istemiyorsanız `--ilan-yok` kullanın.

## Çıkış kodları

| Kod | Anlamı |
| --- | --- |
| 0 | başarı (süzgeç sonrası boş sonuç da başarıdır, uyarı verilir) |
| 2 | ağ/HTTP hatası; robots.txt reddi ve beklenmeyen yönlendirme dahil |
| 3 | sayfa yapısı veya içerik hatası (tanınmayan yerleşim, boş fihrist, henüz yayımlanmamış sayfa) |
| 4 | kullanım hatası (geçersiz tarih/sayı, http(s) olmayan `--url`, çakışan bayraklar) |
| 5 | çıktı dosyası yazılamadı |

## Bilinen sınırlar

- **Mükerrer sayı desteği doğrulanmadı.** Site, 2026-11-04'te denenen her değer
  için `/fihrist?tarih=…&mukerrer=N` isteğini `/` adresine yönlendirdi; bu
  yüzden `--mukerrer` yanlış bir sayfa göstermek yerine anlaşılır bir ağ hatası
  verir. Bayrak, site parametreyi açtığında çalışsın diye korundu
  (`CHANGELOG.md`, 0.2.0).
- Yerleşim değişirse çıkış kodu 3'tür; sessizce boş sonuç dönülmez. JavaScript
  çalıştırılmaz, sunucunun gönderdiği HTML okunur.
- Fihrist yalnız içindekiler listesidir. Bir düzenlemenin *ne anlama geldiğini*
  yorumlamak veya metin farkı üretmek kapsam dışıdır.

## Geliştirme

```console
$ pip install -e ".[dev]"
$ bash scripts/check.sh        # sır taraması, ruff, ruff format, mypy, pytest + kapsama
```

`scripts/check.sh` CI'ın çalıştırdığı kapıdır; bir adım kırmızı olursa betik de
kırmızı biter ve başarısız komutu gizlemez. Testler ağ kullanmaz: kaydedilmiş
sayfalar `tests/fixtures/` altındadır (kaynak bilgisi oradaki README'de) ve HTTP
enjekte edilir.

Katkı: `CONTRIBUTING.md`. Güvenlik bildirimi: `SECURITY.md`.

## Lisans

MIT — `LICENSE`. Bu proje T.C. devleti veya Resmî Gazete ile bağlantılı
değildir; kaynak veri yayıncısına aittir.

English documentation: [README.md](README.md)

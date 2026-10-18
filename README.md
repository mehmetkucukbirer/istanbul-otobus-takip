# Otobüs Takip — "Otobüs gelecek mi, ne zaman?" sorusuna dürüst cevap

> **English summary.** A real-time bus arrival system for Istanbul that keeps answering
> when the official app goes blank: when a bus's GPS is off, when a trip is cancelled, or
> when the last bus of the night has already passed. A collector polls the city's public
> İETT/İBB SOAP services every minute (~6,900 vehicles), infers stop passages from raw
> positions, learns trip durations per line and hour, and serves a SwiftUI iOS app over
> an authenticated tunnel. Every estimate carries a confidence level, and every design
> decision is backed by a measurement on real data — documented in an 87-section
> engineering log. Python (standard library only) + SQLite · SwiftUI · launchd ·
> Cloudflare Tunnel · HMAC-signed address board.

---

## Neden

İstanbul'un resmî "Otobüsüm Nerede" uygulaması yalnız **GPS'i açık ve düzgün çalışan**
araçları gösteriyor. Araç görünmediğinde ekran boş kalıyor ve yolcu "sefer iptal mi,
yoksa otobüs yolda ama görünmüyor mu?" ayrımını yapamıyor. Bu proje tam o boşluk için:
**araç görünmediğinde de bir şey söyleyebilmek** — ve emin olmadığında bunu açıkça söylemek.

## Ekranda ne var

| Satır | Anlamı | Kaynağı |
|---|---|---|
| 🟢 **12 dk** · *23:30 seferi · 4,8 km* | otobüs görünüyor; hangi seferin otobüsü olduğu da yazıyor | canlı konum + sefer kimliği |
| 🔵 **~18 dk** · *konum bildirmiyor* | sefer yolda ama GPS'i kapalı | planlı kalkış + ölçülmüş yolculuk süresi |
| ⚪ **35 dk** · *23:50 kalkışı* | henüz kalkmamış sefer | önceki benzer günün gerçekleşen sefer arşivi |
| 🔴 **İPTAL** | İETT bu seferin yapılmayacağını duyurdu | duyuru servisi |
| ⚫ *bugünkü son sefer geçti · 23:17* | o gece başka sefer yok | arşiv + duraktan geçişin görülmesi (sunucuda hazır, uygulama güncellemesi sürüyor) |

## Mimari

```
İETT / İBB SOAP servisleri ──(dakikada bir)──► kaydedici.py ──► kayit.db  (SQLite · ~11 GB)
                                                                  │
   gecis_dongusu   10 dk    ham konum → "araç bu duraktan geçti" çıkarımı
   model_dongusu   saatlik  hat × saat yolculuk süresi modeli
   duyuru_dongusu  10 dk    sefer iptal duyuruları
   gps_dongusu     10 dk    GPS'i kapalı seferlerin tespiti
   sabah_rutini    09:00    dünün gerçekleşen sefer arşivi → dizin.db  (sefer planı buradan)
                                                                  │
                         arayuz_sunucu.py  (HTTP · erişim anahtarı) ──► iOS uygulaması (SwiftUI)
                                   ▲
   cloudflared tüneli + imzalı adres panosu (ntfy · HMAC-SHA256): tünel adresi değişse de
   telefon yenisini kendisi bulur; sahte ilan anahtarı sızdıramaz
   gozcu_dongusu   kaydedici ve tünel nöbetçisi — takılırsa yeniden başlatır
```

Dokuz süreç macOS `launchd` altında çalışır. Sunucu tarafında **dış kütüphane yok**:
yalnız Python standart kütüphanesi ve SQLite.

## Ölçerek karar verme — örnekler

Bu projede bir tahmin ekrana girmeden önce gerçek veriyle sınanır. Birkaç örnek:

- **Gece "son sefer".** Son otobüs geçtikten sonra ekran "~8 dk" diyordu. Geçmiş durak
  ekranları sunucunun kendi koduyla yeniden üretilip o gecenin gerçekleşen seferleriyle
  karşılaştırıldı: gece gösterilen tahminlerin %65'i seferi bitmiş hattı gösteriyordu.
  Sefer listesi tarife yerine **arşivden** alınınca son kalkış tahmini %77 → **%94**
  doğru oldu; eski ve yeni kod aynı anlarda çalıştırıldı, hayalet kart **945 → 275**.
- **Sefer bazlı tahmin.** "Bu kalkış geçmişte bu durağa kaç dakikada geldi?" — durak
  durak toplanan parça modeline göre ortanca hata **4,5 → 2,4 dk**.
- **Duran araç canlı değildir.** Garajda bekleyen araç "yaklaşıyor" sayılıyordu; filtre
  sonrası gündüz gösterilen canlı araçların **%96,5**'i gerçekten yol alıyor.
- **İptal duyurusu kesin değildir.** Duyurulan iptallerin %66'sı gerçekleşiyor; ekranda
  "kesin" değil "orta" güvenle gösteriliyor.
- **Hız.** Rota ızgarası + izdüşüm önbelleği: durak isteği ortanca **0,07 sn**.

Her kararın gerekçesi ve ölçümü: [`Otobüs Takip Uygulaması PROJE DURUMU.md`](Otobüs%20Takip%20Uygulaması%20PROJE%20DURUMU.md)
(87 bölüm · en sondaki bölüm sistemin güncel özeti).

## Depo içeriği

| Dosya | İş |
|---|---|
| `kaydedici.py` | şehir genelinde araç konumlarını dakikada bir toplar (saatlik istek kotası içinde) |
| `gecisler.py` · `hat_tahmini.py` · `yon_tespit.py` | ham konumdan durak geçişi, hat ve yön çıkarımı |
| `sure_modeli.py` · `parca_havuz.py` | hat × saat yolculuk süresi modeli |
| `durakta_ne_var.py` | çekirdek: bir durakta hangi otobüs, ne zaman, ne güvenle |
| `arayuz_sunucu.py` | HTTP API (durak, hat, araç, sefer, arama) |
| `duyurular.py` · `gps_izleyici.py` | iptal duyuruları · GPS'i kapalı seferler |
| `pano.py` | imzalı adres panosu + adres değişince bildirim |
| `ios/` | SwiftUI uygulaması |
| `*_dongusu.sh` · `launchd_kur.sh` · `durum.sh` | süreçler, kurulum, günlük kontrol |
| `PROMPT_uygulama.md` | ürün tanımı |

**Bu depoda olmayanlar:** `veri/` (SQLite veritabanları ve erişim anahtarı) ve `arac/`
(indirilen ikili dosyalar).

---

*Kişisel projedir; İBB ve İETT ile resmî bir bağlantısı yoktur. Kullanılan veriler bu
kurumların herkese açık servislerinden alınır; logolar ilgili kurumlara aittir.*

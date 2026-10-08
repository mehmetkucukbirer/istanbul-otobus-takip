# OTOBÜS TAKİP UYGULAMASI — PROJE DURUMU

> Bu projenin **devir dosyası**. Seans başında `PROMPT_uygulama.md` (ne yapıyoruz)
> ve bu dosya (nerede kaldık) okunur. Her seans sonunda burası güncellenir.
>
> Proje başlangıcı: 26 Ağustos 2026
> **Son güncelleme: 9 Ekim 2026** — 85 bölüm.
>
> **Yeni seansa başlarken:** önce `PROMPT_uygulama.md` (ne yapıyoruz), sonra bu
> dosyanın **EN SONDAKİ bölümü** okunmalı (şu an Bölüm 85 — sistemin şu anki hâli
> ve açık işler). Gerisi başvuru kaynağı — baştan sona okumaya gerek yok.

---

## 1. KLASÖR

```
mobil otobüsüm nerede/
├── PROMPT_uygulama.md      ürün tanımı, mimari, kararlar   (ana referans)
├── Otobüs Takip Uygulaması PROJE DURUMU.md   bu dosya — nerede kaldık
├── veri/
│   ├── rota_yollari.json          676 hat, OSRM ile yola oturmuş gerçek geometri (2,3 MB)
│   ├── guzergahlar.json           676 hat, 55.564 durak, koordinatlı (2,3 MB)
│   ├── gercek_sure_hat_saat.csv   hat × saat ölçülmüş gerçek sefer süresi + gözlem sayısı
│   └── gercek_sure_hat.csv        hat bazlı ortalama gerçek süre
└── notlar/
```

> `veri/` içindekiler biten İETT arz-talep projesinden **kopyalandı**. Yeniden
> üretilmeleri saatler sürer (OSRM ~25 dk, durak çekimi ~10 dk, arşiv taraması daha uzun).
> Eski proje `Desktop/iett-projesi/` — dokunulmadı, başvuru kaynağı olarak duruyor.

---

## 2. ⭐ 1. SEANSTA YAPILAN ÖLÇÜMLER (26 Ağustos 2026)

Mimarinin kaderini belirleyen soru şuydu: **iptal bilgisi canlı mı geliyor?**
Ölçüldü. Cevap: **HAYIR — ertesi gün geliyor.**

### 2.1. Arşiv tazeliği — ÖLÇÜLDÜ

`ibb/ibb360.asmx` → `GetIettArsivGorev_json` (`Tarih`, `yyyyMMdd`):

| Tarih | Sonuç |
|---|---|
| **20260826 (bugün)** — 15:54'te soruldu | **`[]` boş** |
| 20260825 (dün) | ✅ 18,9 MB · **51.764 kayıt** |
| 20260824 | ✅ 18,9 MB |

Dünün dosyası **tam günü kapsıyor**: bitiş zamanları 25 Ağustos 04:51'den
26 Ağustos 04:01'e kadar (gece hatları dahil). Yani günlük toplu yazılıyor,
akış hâlinde değil.

> **SONUÇ — mimari kararı:** Gerçek zamanlı iptal bilgisi **yok**. İptal, anlık olarak
> **çıkarılmak** zorunda. Arşiv iki iş için kullanılacak: (a) modeli **eğitmek** için
> etiket üretmek, (b) verdiğimiz tahminleri ertesi gün **doğrulamak**.
> Bu, `PROMPT_uygulama.md` Bölüm 4.3'teki "B senaryosu".

### 2.2. ⭐ İptal kaydının şekli — TEMİZ ETİKET VAR

İptal (`I`) kayıtları şöyle görünüyor:

```
hat BA-2   plan 2026-08-25 11:45   düzenlenen 11:45   başlama YOK   bitiş YOK   araç None
```

**1.932 iptal kaydının 1.919'unda gerçek başlama zamanı yok** (13 tanesi yarım kalmış sefer).
Yani her planlanan kalkış için `(kalkış saati) → (yapıldı / yapılmadı)` ikilisi
**doğrudan okunabiliyor.** Model eğitimi için aranan etiket bu — üretmeye gerek yok, hazır.

Alanlar: `ID, NARSIVGOREVID, NKAYITGUNU, SHATKODU, SGUZERGAHKODU, SKAPINUMARA,
DTBASLAMAZAMANI, DTBITISZAMANI, SGOREVDURUM, NGOREVID, DTPLANLANANBASLANGICZAMANI,
DTDUZENLENENBASLANGICZAMANI`

### 2.3. İptal oranları — 25 Ağustos 2026, tüm şehir

```
T  (tamamlandı)  49.378   %95,4
I  (iptal)        1.932   % 3,7
YK                  384   % 0,7
B                    70   % 0,1
                 ──────
toplam iptal/yarım  ~%4,6
```

**Saate göre** (planlanan kalkış saatine göre, yapılmayan sefer oranı):

```
03:00  %0,0        09:00  %4,7        15:00  %5,8        21:00  %3,3
05:00  %1,8        10:00  %5,5        16:00  %5,4        22:00  %3,8
06:00  %2,8        13:00  %6,3 ←zirve 17:00  %5,6        23:00  %2,6
08:00  %3,5        14:00  %6,0        18:00  %5,7
```

> Gece ve sabah erken en güvenilir; **öğleden sonra iki katına çıkıyor.**
> Saat, modelin ilk ve en ucuz değişkeni.

**⭐ Hatta göre — asıl sinyal burada.** İptal şehre eşit dağılmıyor, birkaç hatta yığılıyor:

```
T2      70 sefer   70 yapılmadı   %100,0   ← hat o gün hiç çalışmamış
71T     28 sefer   15 yapılmadı   % 53,6
154     40 sefer   20 yapılmadı   % 50,0
13FY    36 sefer   18 yapılmadı   % 50,0
136Z    30 sefer   10 yapılmadı   % 33,3
34A     54 sefer   16 yapılmadı   % 29,6   (Metrobüs)
BN1    157 sefer   41 yapılmadı   % 26,1
```

> **Ürün açısından en önemli bulgu.** Şehir ortalaması %4,6 iken bazı hatlar %50-100.
> Yani "hat kimliği" tek başına çok güçlü bir ön olasılık. Model karmaşık olmak zorunda
> değil — hat × saat tablosu bile ciddi iş görür.

### 2.4. Referans senaryo — 98 hattı, 25 Ağustos

```
98 hattı: 50 sefer, HEPSİ tamamlandı (0 iptal)
22:00 → T (gerçek 22:01)      23:00 → T (gerçek 23:00)
22:45 → T (gerçek 22:45)      23:30 → T (gerçek 23:30)   ← referans kalkış
```

> **Önemli:** Mehmet'in anlattığı Sefaköy senaryosunda 23:30 kalkışı **iptal değil.**
> En azından bu tarihte sefer yapılmış, tam zamanında kalkmış. Yani yolcunun ekranda
> hiçbir şey görememesinin sebebi büyük ihtimalle **iptal değil, GPS karanlığı.**
> Bu, ürünün ağırlık merkezini değiştirir: asıl kazanç "iptali haber vermek"ten çok
> **"görünmeyen ama yolda olan otobüsü tahmin etmek"**te.
> ⚠️ Tek gün, tek gözlem. Birkaç günlük veriyle doğrulanmalı.

### 2.5. Veri kalitesi — dikkat

- Bozuk zaman damgası var: `DTBASLAMAZAMANI` bazı kayıtlarda `2000-12-31 23:00`
  (boş değerin epoch karşılığı). Filtrelenmeli.
- Gelecek tarihli kayıt görüldü (26 Ağustos 22:33, sorgu 26 Ağustos 15:54'te yapıldı).
  Bozuk kayıt. Eski projede de "negatif ve milyonlarca dakikalık süreler" bulunmuştu.
- Zaman formatı `/Date(1786096228000)/` — milisaniye epoch, regex ile ayıklanır.

---

## 3. AÇIK KARARLAR

1. ~~Kodu kim yazıyor?~~ ✅ **KARAR VERİLDİ (26 Ağustos)** — Bölüm 6.
2. Mobil taraf: PWA mı, React Native mi?
3. Kaydedici 7/24 nerede çalışacak? (laptop yetmez)
4. Kaç hatla başlıyoruz? (öneri: 98 + 500T + 2-3 hat)
5. Rota planlayıcı: hazır motor (OpenTripPlanner) mu, kendi algoritmamız mı?

---

## 4. SIRADAKİ İŞ

1. ~~**Kaydedici**~~ ✅ **YAPILDI (26 Ağustos, 1. seans)** — `kaydedici.py`, Bölüm 7.
2. ~~**Denenmemiş metotlar**~~ ✅ **YAPILDI (1. seans)** — tam envanter çıkarıldı, Bölüm 8.
   Sonuç: umut edilen metotların hepsi geçitte kapalı, kısıt **gevşemedi**.
3. ~~**Durak → hat dizini**~~ ✅ **YAPILDI (1. seans)** — `durak_dizini.py`, Bölüm 9.
4. ~~**Tarife**~~ ✅ **YAPILDI (1. seans)** — `tarife.py`, Bölüm 9.
5. **Geçmiş arşiv taraması** — 2-4 haftalık `GetIettArsivGorev_json` çekip hat × saat ×
   gün tipi iptal olasılık tablosunu kur. Bu tablo, modelin ilk sürümü olabilir.

---

## 5. KISITLAR (eski projeden ölçülmüş, aynen geçerli)

- **Kota:** ~86 ardışık istekten sonra `Policy Falsified / Rate limit exceeded`.
  3 dakikada açılmadı. Blokluyken yoklamak cezayı uzatıyor → tamamen sus.
- **Canlı servis dakikada bir tazeleniyor**, her dakikanın ~5. saniyesinde.
- **CORS:** tarayıcı SOAP servisine doğrudan bağlanamaz (POST 200 ama başlık yok,
  OPTIONS 500). Backend zorunlu.
- **Yol bazında canlı trafik verisi açık veride YOK** (`TrafficDensity`, `RoadTraffic`,
  `Announcement` → 404). Trafik otobüslerin kendisinden çıkarılacak.
- **Doküman güvenilmez** — parametre adları WSDL'den okunmalı (`.asmx?wsdl`).
- **TLS:** macOS Python 3.9 + LibreSSL bazı dış servislerde el sıkışamıyor; `curl` çalışır.

---

## 6. ÇALIŞMA TARZI — bu projede geçerli kural

**Eski projedeki kural DEĞİŞTİ.** Mehmet'in 26 Ağustos'taki kararı:

> *"öğrenmek gerekiyor dediğin kısımları bana söyle, sen yaz genellikle ama söyle bana
> ne yaptığımızı ne işe yaradığını, ipi kaçırmayayım"*

Yani:

- **Kodu asistan yazar.** (Eski projede Mehmet yazıyordu — o kural burada geçerli değil.)
- **Ama her adımda anlatılır:** ne yaptık, neye yarıyor, neden böyle. Amaç Mehmet'in
  ipi kaçırmaması — dosyalar birikirken neyin ne olduğunu bilmesi.
- **Öğrenilmesi gereken yerler ayrıca işaretlenir.** Asistan "burayı anlaman lazım"
  dediği kısımları açıkça söyler; gerisi altyapı gürültüsü olarak geçilebilir.
- **Mesajlar kısa, tek seferde tek konu.** Uzun mesaj kafa karıştırıyor.
- Amaç hem çalışan bir uygulama hem öğrenmek; ikisi birden.

---

## 7. KAYDEDİCİ — `kaydedici.py` (1. seans)

Dakikada bir `GetHatOtoKonum_json` sorup sonucu SQLite'a yazan sürekli çalışan betik.
Şu an izlenen hatlar: **98, 500T** (`HATLAR` listesine kod eklenerek çoğaltılır).

**Bağımlılık yok.** Sadece Python standart kütüphanesi (`urllib`, `sqlite3`,
`xml.etree`, `json`). venv gerekmiyor. macOS Python 3.9.6 + LibreSSL ile İBB
adreslerine bağlanabildiği doğrulandı.

```
python3 kaydedici.py        # başlat · Ctrl+C ile durdur · kaldığı yerden devam eder
```

### ⭐ İKİ TABLO — tasarımın kritik kararı

| tablo | ne tutar |
|---|---|
| **`konum`** | görülen her aracın her yeni konum bildirimi |
| **`yoklama`** | **yapılan her sorgunun kendisi** — kaç araç görüldü, hata mı alındı |

`yoklama` tablosu neden şart: ileride "23:30'da 98 hattında araç var mıydı?" diye
soracağız. Veritabanında o ana ait konum satırı yoksa iki ihtimal var —
**(a)** baktık ve hiçbir araç yoktu *(bu bir bulgu)*, **(b)** o an hiç bakmadık
*(bu bir boşluk)*. Sadece konum tutulsaydı bu ikisi ayırt edilemezdi ve hayalet
sefer tespitinin temeli çökerdi. **Boş sonuç da bir veridir.**

### Diğer kararlar

- **Mükerrer engelleme:** `UNIQUE (hat, kapino, damga)` + `INSERT OR IGNORE`.
  Servis dakikada bir tazelendiği için aynı bildirim tekrar tekrar geliyor;
  yalnızca yeni damga taşıyanlar yazılıyor. *Test: aynı dakikada iki tur → 2. turda 0 yeni satır.*
- **Zamanlama:** her dakikanın **8. saniyesinde** soruluyor. Servis veriyi ~5. saniyede
  tazeliyor; daha erken sormak eski veriyi, daha sık sormak boş istek getirir.
- **İki zaman ayrı tutuluyor:** `damga` = servisin verdiği an (`son_konum_zamani`),
  `cekim_zamani` = bizim sorduğumuz an. Gecikmeyi ölçebilmek için ikisi de lazım.
- **Kota koruması:** hata alınınca 180 → 300 → 600 → 900 saniye susuluyor.
  Ölçülmüştü: blokluyken yoklamak cezayı uzatıyor.

### İlk doğrulama (26 Ağustos 16:03)

```
98    → 9 araç      500T → 27 araç
2. tur → 0 yeni kayıt   (mükerrer engelleme çalışıyor)
veritabanı: veri/kayit.db
```

⚠️ **Şu an Mehmet'in bilgisayarında çalışıyor.** Bilgisayar kapanınca duruyor.
7/24 nerede çalışacağı hâlâ açık karar (Bölüm 3, madde 3).

---

## 8. SERVİS ENVANTERİ — WSDL'den tam liste + geçit testi (1. seans)

WSDL'ler `?wsdl` ile çekildi, tanımlı **tüm** metotlar listelendi, umut verenler denendi.

**Beş servis yolu:**
`FiloDurum/SeferGerceklesme.asmx` (36 metot) · `UlasimAnaVeri/PlanlananSeferSaati.asmx` (12) ·
`UlasimAnaVeri/HatDurakGuzergah.asmx` (9) · `ibb/ibb.asmx` (9) · `ibb/ibb360.asmx` (4)

### ✅ YENİ ÇALIŞAN METOTLAR (bu seansta bulundu)

| Metot | Servis | Parametre | Ne verir |
|---|---|---|---|
| **`DurakDetay_GYY_wYonAdi`** | `ibb/ibb.asmx` | `hat_kodu` | Düz `DurakDetay_GYY`'nin **üstün sürümü**. 98 için 145 durak. Ek alanlar: `YON_ADI`, `ISLETMEALTBOLGE`. Bundan sonra bu kullanılmalı. |
| **`GetDurak_json`** | `HatDurakGuzergah.asmx` | `DurakKodu` | Durak künyesi: `SDURAKADI`, `KOORDINAT` (WKT POINT), `ILCEADI`, `SYON`, **`AKILLI`**, `FIZIKI`, `DURAK_TIPI`, `ENGELLIKULLANIM` |
| **`HatServisi_GYY`** | `ibb/ibb.asmx` | `hat_kodu` | Hat künyesi: `HAT_ADI`, **`HAT_DURUMU`**, `BOLGE`, `SEFER_SURESI` |

### ❌ GEÇİTTE KAPALI — hepsi "Service Not Found"

`GetPlanaUyum_json` · `GetSeferZayi_json` · **`GetPlanlananSeferSaatiAraDurak_json`** ·
**`GetStopLines_json`** · `GetDurakGecisZaman_IGA_json` · `GetMetobusFrekans_json` ·
`GetMetobusFrekansIlkSonSefer_json` · `GetFiloDurum_json` · `GetKaraKutuSeferBilgileri_json` ·
`GetUzulsuzKartKullanim_json` · `GetYolcuBilgilendirme_json` · `IETTPlakaServisi_Json`

> ⚠️ **"Service Not Found" ≠ kota.** İkisi de HTTP 500 döner, ayrım gövdedeki
> `policyResult status` alanında:
> `"Service Not Found..."` = geçit o operasyonu hiç açmamış (bekleme işe yaramaz)
> `"Rate limit exceeded."` = kota (susmak gerekir)
> **Teşhis için gövdeyi mutlaka oku.**

`GetDuyurular_XML` hiçbir WSDL'de yok — eski notlardaki isim yanlış olmalı.

### ⚠️ İKİ SONUÇ — mimariyi etkiliyor

**1. Durak bazlı tarife YOK.** `GetPlanlananSeferSaatiAraDurak_json` kapalı. Yani
"98 bu durağa kaçta uğrar" sorusunun resmî cevabı alınamıyor. **Kendimiz hesaplayacağız:**
kalkış saati + rota üzerinde o durağa kadar geçen süre. Zaten planlanan yöntem buydu,
ama artık alternatifi olmadığı kesin.

**2. Durak → hat sorgusu YOK.** `GetStopLines_json` kapalı. Uygulamanın en temel ekranı
("bu duraktayım, ne gelecek") bu sorguyu istiyor. Dizini kendimiz kuracağız —
Bölüm 4 madde 3.

### ⭐ YAN BULGU — senaryoyu açıklıyor

`GetDurak_json` ile Sefaköy Merkez durağına bakıldı:

```
kod 124081 · SEFAKÖY MERKEZ · Küçükçekmece
DURAK_TIPI : İETTBAYRAK        ← sadece bayrak direği
AKILLI     : YOK               ← akıllı durak ekranı YOK
```

> Mehmet'in senaryosundaki durakta **zaten ekran yok.** "Ekrandan hiçbir otobüs
> göremiyor" tespiti birebir doğru.
>
> ⚠️ Buradan çıkan "şehirdeki ekransız durakları haritala" fikri **kapatıldı**
> (Mehmet'in kararı, 1. seans): ilgi çekici ama projeyi saptırır. `AKILLI` alanı
> yalnızca durak künyesinde duruyor, peşine düşülmeyecek.

### 98 hattı — Sefaköy durak kodları (referans senaryo)

```
122622  sıra 16  yön D  SEFAKÖY
124081  sıra 19  yön D  SEFAKÖY MERKEZ      ← Bakırköy'den gelen yön
124082  sıra 53  yön G  SEFAKÖY MERKEZ
```

---

## 9. DURAK DİZİNİ + TARİFE — `durak_dizini.py`, `tarife.py` (1. seans)

### Neden kendimiz kurduk

`GetStopLines_json` ("bu duraktan hangi hatlar geçer") geçitte **kapalı** (Bölüm 8).
Ama ters yönü açık: `DurakDetay_GYY_wYonAdi` ile "şu hattın durakları neler"
sorulabiliyor. 781 hattın hepsi çekilip ilişki **ters çevrildi**.

### Sonuç — `veri/dizin.db`

```
781 hat çekildi · 1 hat boş döndü · 0 hata · ~11 dakika
13.196 ayrı durak
60.643 hat-durak bağı
koordinatsız durak: 0
enlem 40,814–41,478 · boylam 27,999–29,855   (İstanbul sınırları — sağlama tamam)
```

**Üç tablo:** `hat` (künye) · `durak` (kod, ad, koordinat, ilçe, tip) ·
`hat_durak` (hat + yön + **sıra no** + durak) · `tarife` (planlanan kalkışlar)

> ⭐ **Kritik indeks:** `CREATE INDEX ix_hat_durak_durak ON hat_durak (durak_kodu)`.
> Uygulamanın ana ekranı her açılışta "bu duraktan hangi hatlar geçer" sorgusunu
> yapacak. İndeks olmadan 60.643 satırın tam taraması, indeksle tek sıçrayış.

> **Ayrı veritabanı dosyası** kullanıldı (`dizin.db`, kaydedicinin `kayit.db`'sinden
> ayrı): biri sabit referans, diğeri saniye saniye büyüyen zaman serisi. Aynı dosyada
> olsalardı uzun taramalar kaydediciyi kilitlerdi.

> **Yarıda kesilme koruması:** her hattın çekilip çekilmediği `hat.durum` ve
> `hat.tarife_durum` sütunlarında işaretli; betik tekrar çalıştırılınca bitmişleri atlar.

### Doğrulama — referans senaryo

```
"Sefaköy Merkez (124081) durağındayım, hangi hatlar geçer?"  →  15 hat

  98    FENERTEPE/BAŞAKŞEHİR - BAKIRKÖY   yön D · 19. durak   ← senaryo
  98AB  ATAKENT/HALKALI - BAKIRKÖY        yön D · 19. durak
  98S   K.S.S. HASTANESİ - BAKIRKÖY       yön D · 19. durak
  89    K.S.S. HASTANESİ/ATAKENT-AKSARAY  yön D · 29. durak   (+11 hat daha)
```

> **`sira` alanı ürünün belkemiği.** 98, Sefaköy'de 19. durak. Varış tahmini
> "kalkış saati + ilk 19 durağın süresi" olarak kurulacak.

En çok hat geçen duraklar: VEFA ve UNKAPANI (52'şer hat), İBB (43).

### Tarife tablosu

`GetPlanlananSeferSaati_json` ile 781 hattın planlanan kalkışları çekildi.
⚠️ **Tarife tarihe değil GÜN TİPİNE bağlı** (`I` hafta içi · `C` cumartesi · `P` pazar).
Yani "25 Ağustos'ta ne planlanmıştı" diye sorulamıyor; "hafta içi ne planlanır"
sorulabiliyor. Belirli bir günün gerçek planı yalnızca arşiv görev kaydında.

⚠️ Serviste alan adı **`SGUZERAH`** (yazım hatası serviste, 'G' eksik) — `SGUZERGAH` değil.

---

## 10. ROTA GEOMETRİSİ — `rota.py` (1. seans)

Durakları ve araçları **gerçek yol çizgisine izdüşüren** modül. Hem tarife tabanlı
hem canlı araç tabanlı tahmin aynı hesabı kullanıyor.

**Neden kuş uçuşu mesafe yetmez:** otobüs yoldan gidiyor (viraj, sapma mesafeye
giriyor), ve kuş uçuşu mesafe aracın durağı **geçip geçmediğini** söyleyemez —
500 m ötedeki araç yaklaşıyor da olabilir uzaklaşıyor da. Çözüm: hem durağı hem
aracı rotaya izdüşürüp "rota başından kaç metre" tek sayısına indirgemek.
Fark negatifse araç durağı geçmiştir.

### Doğrulama — 98 · yön D

```
rota uzunluğu 33,4 km · 76 durak

  17  KARTALTEPE          8,83 km
  18  BELEDİYE CADDESİ    9,07 km
  19  SEFAKÖY MERKEZ      9,42 km   ← rotanın %28,2'i
  20  MERKEZ CADDESİ      9,69 km
  76  FENERTEPE PERONLAR 33,44 km

durakların rotadan sapması: 1-15 m   → geometri sağlam
```

> ⭐ **Mesafeye göre %28,2 · durak sayısına göre %24,0.** 4 puan fark, çünkü
> Bakırköy-Sefaköy arası duraklar sık, sonrası seyrek. Tahmin **mesafeye** göre
> yapılıyor; durak saymak sistematik hata üretirdi.

### ⭐ REFERANS SENARYONUN İLK CEVABI

```
98 · 23:30 Bakırköy kalkışı  →  Sefaköy Merkez'e 18-22 dk  →  23:48 – 23:52
```
(sefer süresi 64-79 dk aralığı × %28,2)

---

## 11. ⚠️ ELDEKİ SÜRE DOSYASI BOZUK — kendimiz hesaplıyoruz

Eski projeden gelen `veri/gercek_sure_hat_saat.csv` **yön ayırmıyor** ve "bacak
sorunu"nu içeriyor. 25 Ağustos arşiviyle ölçüldü:

```
98 · yön D →  5 sefer · ortalama  71 dk · aralık  64-79    tutarlı  (tek yön)
98 · yön G → 45 sefer · ortalama 187 dk · aralık 73-244    tutarsız (karışık)
             saat 13 → 217 dk    ama    saat 22 → 74 dk
```

Aynı hattın seferi 74 ile 217 dakika arasında olamaz. **G kayıtlarının çoğu
gidiş+dönüşü tek sefer sayıyor**, gece kalkışları ise tek yön — iki farklı şey
aynı sütunda toplanmış. CSV'deki "saat 22 → 128 dk" değeri bu yüzden anlamsız.

> **Karar:** o dosya varış tahmininde **kullanılmayacak**. Süreler arşivden,
> **yön ayrılarak** kendimiz hesaplanıyor → `sureler.py`, Bölüm 12.
> Dosya silinmedi; eski projenin çıktısı olarak `veri/` altında duruyor.

---

## 12. ARŞİV TARAMASI — `sureler.py` (1. seans)

14 günlük `GetIettArsivGorev_json` indirilip `sefer` tablosuna yazılıyor.
**Tek taramadan iki çıktı** alınıyor:

1. **Gerçek süreler** (hat × yön × saat) → varış tahmininin temeli
2. **İptal oranları** (hat × saat × gün tipi) → iptal tahmininin ön olasılığı

Temizlik: süre `5–400 dk` dışındaysa `NULL` (negatif ve milyonluk bozuk kayıt var);
`2000-12-31` damgası boş değerin epoch karşılığı, `None` sayılıyor.
Tekrar çalıştırılırsa çekilmiş günleri atlar (`arsiv_gun` tablosu).

---

## 13. ⭐⭐ İLK UÇTAN UCA ÇIKTI — `durakta_ne_var.py` (1. seans)

```
python3 durakta_ne_var.py 124081 23:20
```

Beş kaynağı tek cevapta birleştiriyor: `hat_durak` (durakta hangi hatlar, kaçıncı sıra) ·
`tarife` (kalkış saatleri) · `sefer` (gerçek süre + iptal oranı) · `konum` (canlı araçlar) ·
`rota.py` (rota üzerindeki yer).

### ⭐ REFERANS SENARYONUN TAM CEVABI

```
SEFAKÖY MERKEZ · Küçükçekmece · 26.08.2026 23:20 · hafta içi

  98  → FENERTEPE PERONLAR
        bu durak: 19/76 · rotanın %28'i
     ⏱ 23:30 kalkış → bu durağa 23:49 – 23:54   (orta nokta 23:51)
        ölçüm: 98_D_D0 varyantı, 26 seferde ortanca 76 dk
        geçmiş 14 gün: bu saatteki kalkışların %9'u yapılmadı (22 sefer)
```

Aynı sorguda o durağa uğrayan **15 hattın** hepsi için aynı cevap üretiliyor
(79Y, 89K, 98, 98AB, 98S, HT20 ... ).

### Tasarım — iki ayrı cevap, iki ayrı güven

| kaynak | ne zaman | güven |
|---|---|---|
| **CANLI** | araç görünüyor → konumundan hesap | yüksek |
| **TARİFE** | araç görünmüyor → plandan tahmin | orta / düşük |

> **Ürünün ana fikri bu ayrım.** "Otobüsüm Nerede"nin sustuğu yer ikinci satır.
> Varış **tek sayı değil aralık** olarak veriliyor (23:49–23:54); aralığın genişliği
> ölçülmüş sürelerin %10-%90 dilimlerinden geliyor, yani belirsizliğin kendisi ölçüm.

---

## 14. ~~AÇIK SORUN~~ ✅ ÇÖZÜLDÜ — araç hangi bacakta? (Bölüm 15)

`durakta_ne_var.py` şu an aracın yönünü `guzergahkodu`nun orta harfinden okuyor.
**Bu, gidiş+dönüş varyantlarında yetersiz:** `98_G_D7742` etiketli bir araç turun
ikinci yarısında D bacağında ilerliyor olabilir, ama etiket hâlâ G der.

Ölçüm (26 Ağustos 16:42, araç B-1519, etiket `98_G_D7742`):

```
D rotasına izdüşüm:  7,9 km · sapma 39 m
G rotasına izdüşüm: 26,7 km · sapma  2 m     ← gerçekte G bacağında
```

> Bu örnekte etiket doğruydu ve **sapma farkı** (2 m'ye karşı 39 m) da aynı sonucu
> verdi. Ama eski projede 98'in kalkışlarının **%91'i "G" etiketli** olduğu ölçülmüştü —
> etikete güvenilemez.

**Çözüm (eski projede kanıtlanmış, üç kademeli):**
1. **Hareket vektörü** — aracın iki ölçüm arasındaki yer değiştirme açısı, rotanın o
   noktadaki gidiş açısıyla karşılaştırılır. *Artık yapılabilir: kaydedici ardışık
   konumları saklıyor.* Koruma: 60 m'den az yer değiştirmede açı gürültülü, karar verilmez.
2. **İzdüşüm sapması** — hangi rotaya daha yakınsa o bacak (bu seansta işe yaradı).
   Zayıf noktası: gidiş ve dönüş aynı caddeyi kullanıyorsa ikisi de yakın çıkar.
3. **`guzergahkodu` harfi** — son çare.

✅ **ÇÖZÜLDÜ, 1. seans** — `yon_tespit.py`, Bölüm 15.

### Diğer küçük borçlar

- `durakta_ne_var.py`'de canlı bölüm **her zaman ŞU ANI** gösterir; komut satırında
  saat verilse bile geçmiş konum yok. Test ederken karıştırmamak lazım.
- Kaydedici yalnızca **98 ve 500T**'yi izliyor; diğer hatlarda canlı bölüm boş.
- Rota geometrisi **676 hat** için var, dizinde **781 hat**. Eksik hatlarda
  `durakta_ne_var.py` sessizce atlıyor — sayısı ölçülmedi.

---

## 15. ⭐⭐ YÖN TESPİTİ — `yon_tespit.py` (1. seans)

### Yöntem: ilerleme testi (açı hesabı değil)

Aracın ardışık konumları **her iki rotaya da** izdüşürülüyor.
Doğru bacakta rota üzerindeki mesafe **artar**, ters bacakta **azalır**.

```
uyum = rota üzerindeki ilerleme ÷ gerçek yer değiştirme
       +1 civarı → araç bu bacakta ileri gidiyor
       −1 civarı → tersine gidiyor (yani öbür bacakta)
```

> Açıyla uğraşmaya gerek kalmıyor; işaret yetiyor. Ayrıca ölçü, izdüşüm sapmasını
> kendiliğinden cezalandırıyor: araç o rotanın üzerinde değilse izdüşüm zıplar,
> oran 1'den uzaklaşır.

**Üç kademe:** (1) ilerleme testi — en güvenilir, ≥60 m hareket ister ·
(2) izdüşüm sapması — duran araçta çalışır, ortak güzergâhta zayıf ·
(3) `guzergahkodu` harfi — son çare.

### ⭐ ÖLÇÜM — sorun ne kadar büyükmüş (26 Ağustos 16:42, 98 hattı)

```
10 aracın 10'u "G" etiketli
hareket testi:  5'i gerçekte D bacağında     → etiketin YARISI yanlış

A-1682  etiket G → gerçek D   uyum +1.25  (ters bacak −1.02)
A-1731  etiket G → gerçek D   uyum +1.32  (ters bacak −1.08)
A-1739  etiket G → gerçek D   uyum +1.63  (ters bacak −1.60)
A-1859  etiket G → gerçek D   uyum +3.66  (ters bacak −4.44)
C-1623  etiket G → gerçek D   uyum +1.06  (ters bacak −1.03)

9 araç hareketle, 1 araç etiketle karara bağlandı
```

> Ayrım tertemiz: doğru bacak +1 civarı, ters bacak −1 civarı, arada gri bölge yok.

### ⭐ ARAÇ HIZI KENDİ İZİNDEN — `arac_hizi()`

Yön çözülünce hız bedavaya geldi: aracın rota üzerindeki ilerlemesi ÷ geçen süre.
**Tarifeden gelen ortalama değil, o aracın ŞU ANKİ trafikte gerçekte ne kadar
ilerlediği.** Otobüs hareketli bir trafik sensörü olarak kullanılıyor — yol bazında
canlı trafik verisi açık veride olmadığı için (404, Bölüm 5) tek yol bu.

```
98 hattı, 16:54 ölçümü (11 dakikalık iz):
  A-1739  27,3 km/sa      A-1682  19,7 km/sa
  B-1639  28,8 km/sa      A-1731  17,1 km/sa
  A-1859  31,1 km/sa      A-1736  10,0 km/sa  ← trafikte
```
Akıl sağlığı bandı: 2–70 km/sa dışı reddediliyor; geri gitmiş görünen ölçüm atılıyor.

### ⭐⭐ ÖNCESİ / SONRASI — Sefaköy Merkez, 16:54

```
ÖNCE   "hatta 10 araç var ama hiçbiri bu durağa yaklaşmıyor"

SONRA  🚌 A-1682   0,46 km uzakta → ~ 1 dakika · kendi ölçülen hızı 20 km/sa
          yön D (hareket ile tespit, etiket 'G' diyordu)
       🚌 A-1731   4,91 km uzakta → ~17 dakika · kendi ölçülen hızı 17 km/sa
          yön D (hareket ile tespit, etiket 'G' diyordu)
```

> **460 metre ötede gelen otobüs varken "otobüs yok" diyorduk.** Uygulamanın var oluş
> sebebi olan hatayı uygulamanın kendisi yapıyordu. Bu düzeltme olmadan ürünün
> hiçbir iddiası ayakta durmuyordu.

---

## 16. ⭐⭐⭐ İLK GERÇEK DOĞRULAMA — 26/27 Ağustos gecesi (2. seans)

Kaydedici gece boyunca **17,6 saat kesintisiz** çalıştı: 21.800 konum kaydı,
1.846 yoklama, %96 başarı, saat başına 52/60 dakika kapsama.
İzlenen hatlar: 98, 98AB, 98S, 500T.

### Referans senaryo canlı yakalandı — araç B-1639

```
23:09 → 23:20   D rotasında mesafe AZALIYOR (4,0 → 0,0 km)
                yani G bacağını bitirip Bakırköy'e geliyor
23:20 → 23:30   0,00 km'de duruyor — Bakırköy peronunda BEKLİYOR
23:31           0,30 km — KALKTI          (tarife: 23:30 · gecikme 1 dk)
23:50           8,84 km — Sefaköy'e 580 m kala
    ⚠️ 11 DAKİKA BOŞLUK
00:01          13,12 km — Sefaköy çoktan geçilmiş
```

### ⭐ TAHMİN vs GERÇEK

```
TAHMİN  :  23:49 – 23:54     (orta nokta 23:51)
GERÇEK  :  23:52             (boşluğun iki ucundan ara değerle)

aralık içinde: EVET · orta noktadan sapma: 1 dakika
```

> Tahmin, kalkıştan **önce** ve yalnızca tarife + geçmiş ölçümlerle üretilmişti;
> aracı görmeden. Bir gecelik tek gözlem, kanıt değil — ama yöntemin
> çalıştığının ilk somut işareti.

### ⭐⭐ `yoklama` TABLOSU İLK GERÇEK SINAVINI VERDİ

11 dakikalık boşluk göründüğünde ilk akla gelen açıklama "aracın GPS'i sustu" idi.
`yoklama` tablosu tersini söyledi:

```
23:48  ok    5 araç
23:49  ok    5 araç
23:50  ok    5 araç
23:51  ok    5 araç
23:52  HATA  HTTP 500          ← BİZ bakamadık
23:56  HATA  HTTP 500
00:02  ok    5 araç
```

**Boşluk aracın değil, BİZİM.** Kota hatası yüzünden 10 dakika kör kaldık.

> Bu tablo olmasaydı kendi kesintimizi "GPS karanlığı" sanacak ve hayalet sefer
> sinyalini kendi arızamızın üstüne kuracaktık. 1. seansta "boş sonuç da bir
> veridir" diye ayrı tablo açma kararı, ilk gerçek testte karşılığını verdi.

⚠️ **Bu gece senaryonun kendisi tekrarlamadı:** 98'de 5 araç görünüyordu, sefer
yapıldı, GPS sönmedi. Yani "hiçbir şey görünmüyor" durumu gözlenmedi. Hayalet
sefer tespitinin gerçek sınaması için daha çok gece gerekiyor.

### Not — kota hâlâ dar

Gece 67 yoklama hatası alındı (%4). Hepsi "Rate limit exceeded". Kaydedici
kendi kendine toparladı ama **kör dakikalar** üretti. Hat sayısını artırmadan
önce kotanın günlük mü saatlik mi olduğu ölçülmeli.

---

## 17. ⭐⭐⭐ KOTA ÖLÇÜLDÜ — SAATTE 100 İSTEK (2. seans)

Gece boyunca hatalar **her saat tam 4 tane** ve hep aynı dakikalarda (:52 ve :56) çıktı.
Sebep bulundu:

```
saat başına ilk hatadan önceki başarılı istek sayısı:
  18:00 → 100      21:00 → 100      00:00 → 100      03:00 → 100
  19:00 → 100      22:00 → 100      01:00 → 100      04:00 → 100
  20:00 → 100      23:00 → 100      02:00 → 100      05:00 → 100
                                                     06:00 → 100
15 saat, istisnasız 100.
```

> ⭐ **KOTA = SAATTE 100 İSTEK.** Dolunca `Rate limit exceeded` başlıyor,
> tam saat civarında açılıyor. Eski projedeki "~86 istek" tahmini yanlıştı;
> gerçek sayı 100 ve tam saate bağlı.

### Bunun bedeli — dün gece ölçüldü

Kaydedici 2 hat × 60 dakika = **saatte 120 istek** istiyordu, hakkı 100.
Sonuç: **her saatin son 8 dakikası sistematik olarak kör.**

⚠️ Ve tam da can alıcı yerde vurdu: 23:30 otobüsü Sefaköy'den **23:52'de** geçti,
kör pencere **23:52–00:01**. Gecenin en önemli gözlemi tam o boşluğa denk geldi
(Bölüm 16'daki geçiş saati ara değerle bulunmak zorunda kalındı).

### ⭐⭐ ÇÖZÜM BULUNDU — şehir geneli tek istek

```
GetFiloAracKonum_json  (parametresiz)
  → TEK İSTEKTE 6.911 araç · 1,3 saniye
  → alanlar: KapiNo, Plaka, Enlem, Boylam, Hiz, Saat, Operator, Garaj
  → KapiNo, hat bazlı servisin `kapino` alanıyla BİREBİR eşleşiyor (doğrulandı)
```

**Dakikada 1 istek = saatte 60** ile 2 hat yerine **tüm şehir** izlenebilir,
üstelik kotanın altında ve 40 istek artarak.

⚠️ **Eksik: hat kodu yok.** Araç → hat eşlemesi çıkarılmak zorunda. Ölçüldü:

```
canlı filodaki 6.911 aracın hattı biliniyor mu?
  dünkü arşivden        : 5.783 araç  (%84)
  14 günün tamamından   : 6.453 araç  (%93)

⚠️ AMA: 14 günde birden fazla hatta çalışan araç %90
```

> Yani **durağan bir araç→hat tablosu güvenilmez**; araçlar hat değiştiriyor.
> Eşleme (a) arşivden gelen ön bilgi, (b) konumun rota geometrisine oturması,
> (c) ara sıra atılacak hat bazlı sorgu ile birleştirilmeli.

### Önerilen mimari (karar bekliyor)

| bileşen | istek/saat | ne verir |
|---|---|---|
| şehir geneli konum, dakikada bir | 60 | 6.911 aracın konumu + hızı |
| dönüşümlü hat bazlı sorgu | ~30 | araç→hat eşlemesinin tazelenmesi |
| yedek / elle sorgu | ~10 | test ve araştırma payı |
| **toplam** | **~100** | kotanın tam sınırı |

---

## 18. ⭐⭐ KAYDEDİCİ v2 — ŞEHİR GENELİ (2. seans)

`kaydedici.py` baştan yazıldı. **2 hattan 780 hatta** geçildi.

### Nasıl çalışıyor

| iş | sıklık | istek/saat |
|---|---|---|
| **şehir görüntüsü** — `GetFiloAracKonum_json`, 6.911 aracın hepsi | dakikada 1 | 60 |
| **hat eşlemesi** — `GetHatOtoKonum_json`, sırayla bir hat | 2 turda 1 | ~30 |
| elle sorgu payı | — | ~5 |
| | | **~95** (kota 100) |

**Bütçe sayacı tam saatte sıfırlanır** — kotanın kendisi öyle davrandığı için (Bölüm 17).
Bütçe azalınca **önce hat sorguları kesilir**, şehir görüntüsü korunur: o daha değerli,
çünkü kaçırılan dakika geri gelmiyor.

### Üç tablo

| tablo | ne tutar |
|---|---|
| `filo_konum` | şehir geneli konum + **hız** · yalnızca hareketli araçlar |
| `arac_hat` | hangi araç hangi hatta · **zaman damgalı** |
| `yoklama` | yapılan her sorgu (v1'den devam) |

**`arac_hat` neden zaman damgalı:** araçlar hat değiştiriyor. Ölçüldü — 14 günde
araçların **%90'ı** birden fazla hatta çalışmış. Durağan bir araç→hat tablosu yanlış
cevap üretirdi; "şu anda hangi hatta" sorusu ancak zaman damgasıyla cevaplanabilir.

**Hareket süzgeci:** 30 metreden az kıpırdayan araç yazılmıyor. 6.911 aracın ~4.300'ü
garajda duruyor ve dakikada bir aynı koordinatı bildiriyor; hepsini saklamak günde
~800 MB üretir ve hiçbir soruya cevap vermezdi. Süzgeçle ~2.600 hareketli araç kalıyor
→ **günde ~300 MB**. `SAKLAMA_GUN = 10` ile her gece 04:00'te budanıyor.

### Hat sırası

780 hat sırayla dönüyor (bir tam tur ~26 saat). Her 5. sorgu **öncelikli hatlara**
ayrılmış: `98, 98AB, 98S, 500T` — referans senaryonun hatları, sık tazeleniyor.
Sıra `durum` tablosunda saklı, yeniden başlatınca kaldığı yerden devam eder.

### Test (API'ye dokunmadan, kayıtlı filo görüntüsüyle)

```
tur 1 → 6.911 araç yazıldı        (ilk tur, karşılaştırma yok)
tur 2 → 0 yeni satır              ✅ hareket süzgeci çalışıyor
hat sırası → 780 hat · öncelik serpiştirme: 98, 1, 10, 10A, 10E, 98AB, 10EK  ✅
bütçe sayacı → 3 istek sonra 92 kaldı  ✅
örnek satır: A-001 · 41.1218, 29.04419 · 47 km/sa
```

⚠️ **v1'in `konum` tablosu silinmedi** — 26/27 Ağustos gecesinin 22.000 kaydı orada
duruyor, Bölüm 16'daki doğrulama ona dayanıyor. Yeni veri `filo_konum`'a gidiyor.

⚠️ **`durakta_ne_var.py` ve `yon_tespit.py` hâlâ eski `konum` tablosunu okuyor.**
Yeni tabloya geçirilmeleri gerekiyor — sıradaki iş.

---

## 19. KAYDEDİCİYİ ÇALIŞTIRMA / DURDURMA / İZLEME

⚠️ **1. seansta yapılan hata:** kaydedici Claude uygulamasının içindeki bir terminalde
başlatılmıştı (`Claude.app → node → zsh → caffeinate → python3`). O pane kaybolunca
sürece ulaşılamaz oldu; ayrıca Claude kapanınca kaydedici de ölürdü.

**2. seansta düzeltildi:** artık hiçbir pencereye bağlı değil (`PPID 1`), çıktısı
dosyaya yazılıyor.

### Başlatma
```bash
cd "/Users/mehmetkucukbirer/Desktop/mobil otobüsüm nerede" && nohup caffeinate -i python3 -u kaydedici.py > veri/kaydedici.log 2>&1 &
```
> `nohup` + `&` → terminal kapansa da yaşar · `caffeinate -i` → bilgisayar boşta
> uykuya geçmez (ekranın kararması sorun değil) · `-u` → çıktı anında dosyaya düşer.

### Ne yaptığını görme
```bash
tail -f "/Users/mehmetkucukbirer/Desktop/mobil otobüsüm nerede/veri/kaydedici.log"
```
> `Ctrl+C` yalnızca izlemeyi bırakır, kaydediciyi DURDURMAZ.

### Çalışıyor mu
```bash
pgrep -fl kaydedici.py
```

### Durdurma
```bash
pkill -f kaydedici.py
```

---

## 20. KAYDEDİCİ v2 — İLK ÇALIŞTIRMADA BULUNAN İKİ HATA (2. seans)

Yeni kaydedici çalışır çalışmaz iki hata ortaya çıktı; ikisi de düzeltildi.

### Hata 1 — 507 uydurma "dünkü" kayıt

`GetFiloAracKonum_json` yalnızca **saat** veriyor (`"10:00:14"`), tarih yok; tarihi
biz ekliyoruz. İlk sürümdeki gece yarısı koruması şöyleydi: *"araç saati bizimkinden
5 dakika ileriyse dünden kalmadır"*.

Ama **saati bozuk araçlar var** — saat 10:00'da `"23:55"` bildiren araçlar ölçüldü.
Koruma onları bir gün geriye itti ve `filo_konum`'a **507 uydurma kayıt** yazdı.

**Düzeltme, iki parça:**
1. Gün kaydırması artık yalnızca **12 saatten** fazla sapmada yapılıyor (gerçek gece
   yarısı dönüşü), her iki yöne de.
2. Damgası **30 dakikadan** uzak sapan araç tamamen **reddediliyor** — bu bir gözlem
   değil, bozuk cihaz. Zaman serisine girmemeli.

507 kayıt silindi, doğrulandı: yanlış günlü kayıt **0**.

> **Zaman damgası ölçümü (5.875 araç):** ortanca sapma **−57 saniye**, ileri tarihli
> yalnızca **3 araç**, 5 dakikadan eski **0**. Yani filo genelinde saatler sağlam;
> sorun avuç dolusu bozuk cihazda.

### Hata 2 — bütçe sayacı yeniden başlatmada sıfırlanıyordu

Saatlik istek sayacı süreç belleğindeydi. Betik saat ortasında yeniden başlatılınca
o saatte zaten harcanmış istekleri unutuyor, kotayı aşıyordu (gözlendi: 90/95 → 94/95).

**Düzeltme:** sayaç artık `yoklama` tablosundan okunuyor — hangi süreç yapmış olursa
olsun o saatin gerçek toplamı. Doğrulandı: yeniden başlatma sonrası 88/95.

### Küçük borç

Yeniden başlatıldığında hareket süzgecinin karşılaştırma noktası boş oluyor, ilk tur
~5.800 satırın hepsini yazıyor (normalde ~3.000). Zararsız ama gereksiz.
Çözüm: açılışta son konumları veritabanından yükle. Ertelendi.

### Çalışır durumdaki tipik tur

```
10:05:08  [bütçe 90/95]  şehir: 6911 araç · 3018 hareketli · +3018  |  hat 10F: 4 araç
10:07:08  [bütçe 88/95]  şehir: 6911 araç · 6028 hareketli · +5825
```

### `konum_birlesik` görünümü

Eski (hat bazlı, gece) ve yeni (şehir geneli) konum kayıtlarını tek sorguda okumak için
görünüm kuruldu. Bölüm 16'daki gece doğrulaması eski tabloya dayanıyor, silinmedi.

---

## 21. ⭐⭐⭐ TARİFE YETMİYOR — GÖZLEM TARİFENİN ÖNÜNE GEÇTİ (2. seans)

Geçiş sırasında ortaya çıkan en büyük modelleme sorunu.

### Bulgu

```
98 · hafta içi TARİFE
  yön G : 49 kalkış · 05:15 → 22:45      ← gündüz servisinin tamamı
  yön D :  6 kalkış · 00:00 06:10 06:30 06:40 23:00 23:30
```

Gündüz seferleri `98_G_D7742` varyantı, ortalama **193 dakika** = gidiş+dönüş.
Sefaköy'de **D yönüne** binen yolcu aslında bu turların **ikinci yarısıyla** taşınıyor.
Ama tarifede D yönünde 06:40 ile 23:00 arası **hiçbir şey yok**.

**Sonuç:** uygulama saat 10:13'te "sıradaki otobüs 23:00'te" diyordu. Canlı araç
görünmediği anda tamamen yanlış cevap.

### Gerçekte ne oluyor — kendi kaydımızdan ölçüldü

98 · D yönü · Sefaköy Merkez geçişleri (31 adet, konum izinden ara değerle):

```
26.08 akşam : 16:26 16:49 17:07 17:48 18:51 18:58 19:25 19:35 19:58 20:21
              20:31 20:53 20:57 21:40 21:52 23:16 23:23 23:52
27.08 sabah : 06:26 06:51 07:01 07:20 07:46 08:18 08:38 09:01 09:32 09:51 10:13

sefer aralığı — akşam: ortanca 23 dk (4-84)   sabah: ortanca 23 dk (10-32)
```

> **Tarife "sıfır" diyor, gerçek "23 dakikada bir" diyor.**

### Neden formülle türetmeye çalışmadık

G kalkışından D bacağı geçişini hesaplamak mümkün görünüyor
(`kalkış + tur/2 + oran × tur/2`) ama tur süresi saate göre **160-244 dakika**
arasında oynuyor ve peron bekleme süresi de değişken. Denendi, tutmadı.
Formülle kovalamak kırılgan olurdu.

### ⭐ KARAR — üç kademeli cevap, gözlem tarifenin önünde

| kademe | kaynak | ne zaman | güven |
|---|---|---|---|
| **1. CANLI** | görünen araç + rota üzerindeki mesafe | araç varsa | yüksek |
| **2. GÖZLEM** | bizim ölçtüğümüz geçmiş geçişler (`gecis` tablosu) | yeterli gözlem varsa | orta |
| **3. TARİFE** | `GetPlanlananSeferSaati_json` | gözlem yoksa | düşük |

> **Bu aynı zamanda ürünün rakibe karşı asıl üstünlüğü.** Herkes tarifeyi
> gösterebilir; **o durakta gerçekte kaç dakikada bir otobüs geçtiğini** yalnızca
> ölçen bilir. Tarife kâğıt, gözlem gerçek.

⚠️ Gözlem kademesi veri birikimi ister. Şu an yalnızca 98 ve 500T için birkaç saatlik
gözlem var (kaydedici v1'den). v2 tüm şehri topladığı için bu hızla genişleyecek.

---

## 22. GEÇİŞ ÇIKARIMI — `gecisler.py` (2. seans)

Konum izinden "hangi araç, hangi duraktan, kaçta geçti" bilgisini çıkarır.
Araç izi rotaya izdüşürülür; izdüşüm durağın rota mesafesini yukarı doğru kestiği
anda geçiş kaydedilir, tam an iki ölçüm arasında **ara değerle** bulunur.

### ⚠️ Üç denemede oturdu — kaydetmeye değer

| deneme | yöntem | 98·D·Sefaköy'de 31 gerçek geçişten kaçı |
|---|---|---|
| 1 | tüm iz için **tek yön** belirle | **11** — araç gün boyu gidip geliyor, "net yön" diye bir şey yok |
| 2 | izi **bacaklara böl**, grupla | **8** — grup sınırlarında adım kaybı + G'ye yanlılık (G 1738 / D 689) |
| 3 | **gruplama yok**, her adım bağımsız | ✅ **28 / 31 (%90)**, yön dengeli (D 2345 / G 2130) |

**Çalışan yöntem:** her ölçüm çifti bağımsız değerlendirilir; adım, iki rotadan
**ilerlemesi daha büyük** olanına atanır. G ve D birbirinin tersi olduğu için araç
D'de ilerlerken G izdüşümü geriler — karar adım başına zaten belirgin, durum tutmaya
gerek yok.

> **Ders:** karmaşık çözüm (bacak gruplama) basit olandan **daha kötü** sonuç verdi.
> Önce en basit yöntemi ölçmek gerekiyordu.

Korumalar: rotadan >250 m sapan ölçüm atlanır · iki ölçüm arası >15 dk boşluk varsa
geçiş anı uydurma olacağı için atlanır · >6 km atlama `kesin=0` diye işaretlenir.

### İlk çıkarım

```
14.508 geçiş · 361 durak · 6 hat  (kaydedici v1'in 2 hattı + v2'nin ilk eşlemeleri)
```

---

## 23. ⭐ ÜÇ KADEMELİ CEVAP DEVREDE — `durakta_ne_var.py`

```
🚌 CANLI   görünen araç + rota üzerindeki mesafe + kendi ölçülen hızı     yüksek güven
📊 GÖZLEM  o durakta gerçekte ölçülmüş sefer aralığı                      orta güven
⏱  TARİFE  yayımlanmış kalkış saatleri                                    düşük güven
```

### Öncesi / sonrası — Sefaköy Merkez, saat 10:16

```
ÖNCE   ⏱ 23:00 kalkış → bu durağa 23:19 – 23:24
       (12 saat sonrası! Gündüz D yönü tarifede yok — Bölüm 21)

SONRA  📊 GÖZLEM  bu saatte ortanca 31 dakikada bir geçiyor (4-42 dk · 4 ölçüm)
          son geçiş 1 dk önce → sıradaki ~10:48 civarı
       ⏱ tarife (gözlem varken daha zayıf kaynak): 23:00 ...
```

⚠️ **Gözlem şu an çok ince** — yalnızca 2 günlük, saat penceresi ±1 ile 4 ölçüm.
Kaydedici v2 tüm şehri topladıkça hem gözlem sayısı hem durak kapsamı hızla artacak.
`gecisler.py` yeniden çalıştırıldıkça tablo büyür (işlenmiş aralık `durum` tablosunda).

---

## 24. ⭐⭐⭐ HAYALET SEFER TESPİTİ — `hayalet.py` (2. seans)

Ürünün asıl fikri. Tarifede olup ortada görünmeyen kalkışı bulur ve **açıklar**.

### Üç açıklama ayrılıyor

```
İPTAL          sefer hiç yapılmadı          → "sıradaki kalkış 23:50"
GPS KARANLIĞI  araç yolda ama bildirmiyor   → "konum yok, tahmini varış 23:52"
BİZ KÖRÜZ      o an biz bakamadık           → "bilmiyorum" demek zorundayız
```

⚠️ **Üçüncüsü en önemlisi.** Kendi kesintimizi iptal sanıp "otobüs gelmeyecek" dersek
yolcuyu yanıltırız — ve bu, uygulamanın tek kozu olan güvenilirliği yok eder.

### Kalkış nasıl tespit ediliyor

Perona bakılmıyor (orada araçlar park hâlinde durur, sinyal gürültülü). Rotanın
başından **~400 m ötedeki ilk durak** "kalkış habercisi" sayılıyor: bir araç oradan
geçtiyse sefer başlamıştır. Geçişler `gecis` tablosundan geliyor, yani yön gerçek
hareketten belirlenmiş oluyor.

98 için: yön G → `11.BÖLGE` (508 m) · yön D → `KLİNİK` (591 m)

### ⚠️ AÇGÖZLÜ EŞLEŞTİRME ÇÖKTÜ — sıra koruyan hizalamaya geçildi

İlk sürüm "pencereye giren ilk geçişi al" diyordu. **Sefer aralığı 20 dakika,
pencere 35 dakika** olunca bir geçiş birden çok plana uyuyor ve zincir kayıyor:

```
planlar : 16:00 16:20 16:40 17:00 17:20 17:40 18:00 ...
geçişler:       16:23 16:43       17:22 17:47 18:17 ...

açgözlü : 16:23'ü 16:00'a verdi → sonraki her şey bir slot kaydı
sonuç   : 2 yanlış alarm + gerçek iptali kaçırma (0/3 doğru)
```

**Çözüm:** diziyi bütün olarak, **sırayı koruyarak** hizalamak (dizi hizalama
algoritmalarının aynısı: eşleş / plan boşluğu / geçiş boşluğu, toplam sapmayı
en küçükle). Otobüsler kalkış sırasını bozmadığı için sıra koruyan hizalama doğru araç.

Hizalamadan sonra sapmalar: **+2, +2, +3, −3 dk** — tertemiz oturdu.

### ⚠️ İkinci düzeltme — kayıt başlangıcı

16:00 kalkışı "hayalet" işaretlenmişti; kaydedici **16:03'te** başlamıştı.
Kapsama oranı yanıltıcıydı (pencerenin yarısı kayıt sonrasına düşünce eşiği geçiyordu).
Artık ayrı ve kesin kontrol var: **kayıt başlamadan önceki kalkış hakkında hiçbir
şey iddia edilmiyor.**

### ⭐ DOĞRULAMA — 98 hattı, 26 Ağustos, arşivle karşılaştırma

26 Ağustos arşivi (ertesi gün dolduğu için bugün indirilebildi) gerçeği veriyor.
Kaydedici o gün **16:03'ten** itibaren çalışıyordu.

```
bizim 'hayalet'    · arşiv 'YAPILMADI (I)'  →  1   ✅ gerçek iptal yakalandı
bizim 'yapildi'    · arşiv 'yapıldı'        → 16   ✅ hepsi doğru
bizim 'bilinmiyor' · arşiv 'yapıldı'        → 36      (kayıt öncesi — doğru davranış)
bizim 'bilinmiyor' · arşiv 'YAPILMADI (YK)' →  2      (07:20 ve 13:40, kayıt öncesi)

KAPSADIĞIMIZ DÖNEMDE (16:03–24:00): 17 kalkış · 17 doğru · 0 yanlış alarm
```

> **26 Ağustos 18:00 kalkışı gerçekten iptal edilmişti ve biz bunu yalnızca konum
> verisinden, arşivi görmeden bulduk.** Ürünün ana iddiası ilk kez ölçülerek çalıştı.

⚠️ **Bu bir kanıt değil, bir işaret.** Tek hat, tek akşam, tek iptal. `YK` (yarım kalan)
seferler hiç sınanamadı — ikisi de kayıt öncesindeydi. Günlerce veri ve çok hat gerekiyor.

### Sıradaki

- Çok hat × çok gün doğrulama (kaydedici v2 şehir geneli topladıkça)
- `YK` (yarım kalan sefer) tespiti — şu an hiç ele alınmıyor
- "İptal mi GPS karanlığı mı" ayrımı henüz YAPILMIYOR: ikisi de "hayalet" diyor.
  Ayrım için aracın rotanın ilerisinde sonradan belirip belirmediğine bakılmalı.

---

## 25. İPTAL / GPS KARANLIĞI AYRIMI — kuruldu, kısmen çalışıyor (2. seans)

### Fikir

Hayalet kalkışı rotanın **ilerisinde** aramak:

```
kalkışta yok + ileride de yok  →  İPTAL
kalkışta yok, ileride belirdi  →  GPS KARANLIĞI (sefer yapıldı, sinyal sustu)
```

### ⚠️ ZAMANLA EŞLEŞTİRME ÇÖKTÜ — araç kimliğine geçildi

İlk sürüm planları kontrol noktasına kaydırıp orada da hizalıyordu. Ama sefer aralığı
20 dk iken yolculuk süresi ±15 dk oynuyor; bu belirsizlikte **her geçiş her plana
uyuyor**. 26 Ağustos 18:00 iptali bu yüzden yanlışlıkla "GPS karanlığı" sayıldı.

> ⭐ **Doğru sinyal zaman değil, ARAÇ KİMLİĞİ.** Her geçişte kapı numarası var.
> Sefer yapılmış ama kalkışta GPS'i susmuşsa, o araç ileride görünür ve **kalkış
> durağında hiç görünmemiş** olur. Aranan tam olarak bu.

Düzeltmeden sonra 18:00 doğru şekilde **iptal** çıktı.

### ⚠️⚠️ İKİNCİ HAT SINAVI — 98 beni yanıltmış

500T'de aynı yöntem çöktü:

```
98    (sefer aralığı ~20 dk)  →  17 kalkış · 17 doğru · 0 hata
500T  (sefer aralığı ~ 7 dk)  →  8 iptalden 1'i yakalandı · 3 yanlış alarm
```

**Kök sebep:** 500T'de kalkışlar 7 dakikada bir (17:03 17:10 17:17 17:24 17:31 ...).
Kalkış gecikmesi ±5 dk, bizim ölçümümüz dakikada bir, geçiş anı ara değerle bulunuyor.
Belirsizlik sefer aralığına yaklaşınca **hangi seferin yapılmadığı ayırt edilemiyor**.

> **Bu bir yazılım hatası değil, yöntemin fiziksel sınırı.** Tek hatla doğrulama
> yanıltıcıydı; ikinci hat olmasa bu sınır fark edilmeyecekti.

### ⭐ Sınır ürüne dönüştürüldü

```
seyrek hat (20-60 dk aralık)  →  iptal yolcuyu ÇOK etkiler  →  yöntem çalışıyor ✅
yoğun hat  ( 5-10 dk aralık)  →  iptal yolcuyu AZ etkiler   →  yöntem çalışmıyor
```

Özellik, en çok işe yaradığı yerde çalışıyor. Sefaköy 23:30 senaryosu tam da seyrek
hat vakası.

**Kural devreye alındı:** sefer aralığı **12 dakikanın altındaki** hatlarda tek tek
sefer iddiası **yapılmıyor** ("bilinmiyor" deniyor). Yanlış iptal alarmı, uygulamanın
tek kozu olan güvenilirliği yok eder.

Onun yerine `servis_duzeyi()` eklendi: *"son 1 saatte beklenen 8 sefer yerine 5 sefer
geçti"* — yoğun hatta yolcunun asıl merak ettiği soru zaten bu.

Düzeltmeden sonra 500T'de **yanlış iptal alarmı: 0**.

### Uyarlanabilir tolerans

Hizalama toleransı artık sabit değil, hattın **kendi sefer aralığının %45'i**
(en az 4, en çok 18 dk). Sabit 18 dk tolerans 500T'de her planın komşusunun geçişini
kapmasına yol açıyordu.

### ⚠️ AÇIK KALAN

- **`gps_karanligi` dalı hâlâ DOĞRULANMADI.** Hiçbir sınanabilir vakada doğru
  ateşlenmedi; şu an yalnızca "iptal" tarafı kanıtlı.
- **`YK` (yarım kalan sefer)** hiç ele alınmıyor.
- Doğrulama yalnızca **2 hat, 1 gün**. Kaydedici v2 şehir geneli topladıkça
  çok hat × çok gün doğrulama yapılmalı — asıl sınav o.

---

## 26. PANO — `notlar/pano.html` (2. seans)

Mehmet'in isteği: *"bu verinin toplandığını, analiz kısmını göremez miyim,
hep arka planda mı çalışacak, ne yaptığımı tam anlayamıyorum"*.

**Artifact olarak yayımlandı:** https://claude.ai/code/artifact/caf98c95-0389-4410-a980-3eabc1e642eb
(aynı dosya yolundan yeniden yayımlanınca aynı adres güncellenir)

### Tasarım fikri

Pano, **Sefaköy'de olmayan ekranın kendisi** gibi görünüyor — durak ekranı dili.
Servis kaydında o durak için `AKILLI: YOK` yazıyor (Bölüm 8); sayfa, orada bir ekran
olsaydı ne yazması gerektiğini gösteriyor. Üstteki durak ekranı, her satırın hangi
kaynaktan geldiğini de söylüyor: 🚌 canlı · 📊 gözlem · ⏱ tarife.

### İçerik

| bölüm | ne gösteriyor |
|---|---|
| durak ekranı | Sefaköy Merkez için üç kademeli cevap, kaynak etiketleriyle |
| canlı harita | son 3 dk'da bildiren ~2.600 aracın konumu (canvas), 98'in rotası, Sefaköy |
| sayaçlar | konum kaydı · araç · geçiş · durak · bağ · geçmiş sefer |
| kota grafiği | saatlik istek; **kırmızı = kota dolduğu için kaybedilen** — dünkü körlük ile bugünkü temiz akış yan yana |
| boru hattı | yedi betik, sırayla, her birinin çıktısıyla |
| doğrulama | 98 ve 500T tablosu, dürüst sonuçlarla |
| geçiş şeridi | Sefaköy'den gerçekte geçen otobüsler, 23:52 vurgulu |
| açık kalanlar | **bilerek var** — neyin kanıtlanmadığı da aynı yerde |

> Palet renk körlüğü ayrımı dahil altı denetimden geçirildi (teal #4EA8B8 / amber
> #F0A63C, koyu ve açık temada ayrı ayrı). `node` kurulu olmadığı için denetim
> Python'la hesaplandı.

⚠️ Pano **o anın fotoğrafı** — canlı değil. Güncellemek için veriyi yeniden toplayıp
dosyayı yeniden yayımlamak gerekiyor.

---

## 27. GÜNLÜK RUTİN — `gunluk.py` (2. seans)

Her sabah çalıştırılacak **tek komut**:

```bash
cd "/Users/mehmetkucukbirer/Desktop/mobil otobüsüm nerede" && python3 gunluk.py
```

Üç işi sırayla yapar:
1. **Dünün arşivini indirir** — gerçek: hangi sefer yapıldı, hangisi iptal
2. **Yeni konum kayıtlarını işler** — `gecis` tablosunu büyütür (artımlı)
3. **Geniş doğrulama** — o gün gözlem yapılan tüm hatlarda tahminleri gerçekle kıyaslar

Çıktıdaki en önemli sütun **yanlış alarm**: "iptal" deyip otobüs gelirse yolcu
uygulamayı bir daha açmaz.

> Bu rutinin değeri şu: tahmini kalkıştan **önce**, yalnızca konum verisinden veriyoruz;
> arşiv cevabı **ertesi gün** söylüyor. Yani her gün, cevabı görmeden verilmiş bir
> sınavın kâğıdı okunuyor. Model geliştikçe bu tablo iyileşmeli — iyileşmiyorsa
> yaklaşım yanlıştır.

### İlk geniş doğrulama çıktısı (26 Ağustos, 2 hat)

```
hat      kapsanan  doğru  iptal  yakalanan  yanlış  kaçan
500T           75     69      6          0       0      6
98             17     17      1          1       0      0

TOPLAM  · 92 kalkış · 86 doğru (%93,5)
İPTAL   · gerçekte 7 · yakalanan 1 (%14) · kaçan 6 · yanlış alarm 0
```

**Okunuşu:** genel isabet iyi görünüyor (%93,5) ama bu yanıltıcı — çünkü kalkışların
çoğu zaten yapılıyor, "yapıldı" demek kolay. Asıl ölçü **iptal yakalama oranı: %14**.
Buna karşılık **yanlış alarm 0** — uygulama hiçbir zaman yanlışlıkla "iptal" demedi.

> Bu ikisi arasındaki denge bilinçli: yanlış alarm, kaçırılan iptalden daha zararlı.
> "İptal" deyip otobüs gelirse yolcu uygulamayı bir daha açmaz; "bilmiyorum" demek
> can sıkıcı ama güveni yıkmıyor.

---

## 28. 🔜 YARIN — sıradaki iş

**1. Tek komutla geniş doğrulama.** Gece boyunca kaydedici tüm şehri topladı ve hat
eşlemesi 780 hattın tamamını bir tur döndü. Sabah:
```bash
cd "/Users/mehmetkucukbirer/Desktop/mobil otobüsüm nerede" && python3 gunluk.py
```
Bu, 2 hat yerine **onlarca hatta** doğrulama tablosu üretecek. Asıl sınav bu.

**2. İptal yakalama oranını yükselt.** %14 düşük. Bakılacaklar:
- Kalkış habercisi durak seçimi (şu an rota başından 400 m; hatta göre değişmeli)
- `arac_hat` eşlemesinin tazeliği — eski eşleme geçişi kaçırtıyor olabilir
- Yoğun hat eşiği (12 dk) doğru mu, veriyle ölçülmeli

**3. Kaçan iptaller neden kaçıyor?** 500T'de 6 iptal kaçtı; her birinin izini tek tek
sürmek en hızlı öğrenme yolu.

**4. `gps_karanligi` dalını doğrula.** Hâlâ hiç kanıtlanmadı.

**5. Panoyu tazele** — `notlar/pano.html` o anın fotoğrafı; yeni sayılarla yeniden
yayımlanmalı (aynı dosya yolu → aynı adres).

---

## 29. ⛔ GENİŞ DOĞRULAMA ÇÖKTÜ — mimarinin duvarı bulundu (3. seans, 28 Ağustos)

Gece boyunca şehir geneli toplandı, sabah 259 hatta doğrulama koşuldu. Sonuç:

```
259 hat · 6.291 kalkış kapsandı · 4.695 doğru (%74,6)
İPTAL   · gerçekte 173 · yakalanan 64 (%37) · YANLIŞ ALARM 1.487
```

**Kalkışların dörtte birinde yolcuya "iptal" diyecektik, oysa otobüs geliyordu.**

> ⚠️ **Dünkü 2 hatlık sonuç (0 yanlış alarm) yanıltıcıymış.** 98 ve 500T öncelikli
> listede olduğu için sürekli eşleniyordu; sıradan hatlar öyle değil.

### Kök sebep — ölçüldü

```
336 hattın 332'si gün boyunca YALNIZCA BİR KEZ eşlendi
öncelikli 4 hat (98, 98AB, 98S, 500T) ~27 kez eşlendi
hat × saat kapsaması: %2,2
```

Kaydedici v2 konumları **herkesten** alıyor ama hat kimliğini hatları **tek tek
sorarak** öğreniyor; kota (saatte 100) buna günde ancak bir tur izin veriyor.

> **Konumda 780 hattayız, hat kimliğinde 4 hattayız.** 2. seansta "780 hatta çıktık"
> denirken bu ölçülmemişti.

### Geçici koruma — eşleme tazeliği

`hayalet.py`'ye kural eklendi: **eşlemesi taze olmayan hatta iptal iddia edilmez.**
Bilmediğimiz şey hakkında konuşmuyoruz.

```
tolerans 45 dk → 161 yanlış alarm · %9 yakalama
tolerans 15 dk →  32 yanlış alarm · %4 yakalama   ← şu anki ayar
```

İyi bir nokta yok; sorun ayarda değil, veride.

---

## 30. ⭐ ÇÖZÜM — `hat_tahmini.py`: hat kimliğini geometriden çıkar (3. seans)

676 hattın gerçek yol geometrisi elimizde. Aracın izini rotalarla eşleştirip hangi
hatta olduğunu **kotaya hiç dokunmadan** buluyoruz.

**Izgara indeksi:** rota noktaları ~550 m'lik hücrelere indeksleniyor; 780 hattı tek
tek denemek yerine avuç dolusu aday kalıyor.

### ⚠️ İLK PUANLAMA ÇÖKTÜ — ölçülerek düzeltildi

İlk sürüm yalnızca ortalama sapmaya bakıyordu: **%67 isabet**. Teşhis:

```
gerçek hattın aday listesindeki sırası (178 örnek)
  1. sırada  : 54   ← yalnızca %30
  2. sırada  : 44
  3. sırada  : 21
  daha geride: 49
```

Aday listesi doğruydu, **puanlama ayırt edemiyordu** — hatlar uzun ortak koridorları
paylaşıyor, kısa iz birçok rotaya birden oturuyor.

**Eklenen ölçü — yol tutarlılığı:** rota üzerindeki ilerleme, aracın *gerçekte
katettiği yola* yakın olmalı. Yanlış rotada izdüşüm kayar, oran bozulur. Ortak
koridordan ayrılan hatları eleyen asıl ölçü bu. Ayrıca **en büyük sapma** eklendi
(yanlış rotada araç bir yerde ayrılır ve orada patlar) ve iz 12→28 dakikaya çıkarıldı.

```
önce : %67,1 isabet · örneklerin %25'inde karar
sonra: %93,7 isabet · %91,9 yön isabeti · %26'sında karar
```

⚠️ Kalan %6,3 yanlış atama önemli: yanlış hat, yanlış geçiş, yanlış alarm demek.
Ortak koridorlarda (E-5, Mecidiyeköy) geometri tek başına yetmiyor — orada
**karar verilmiyor**, uydurma yapılmıyor.

### ⭐ PARÇA IZGARASI — performans engeli aşıldı

İlk sürüm her aday için **tüm rotayı** tarıyordu: araç-anı başına ~5.600 izdüşüm.
Kaydediciye bağlanınca saatler sürerdi.

Izgara artık hat değil **rota parçası** düzeyinde: bir noktanın düştüğü hücreden
yalnızca yakındaki parçalar okunuyor.

```
ızgara kurulumu : 0,7 sn · 7.901 hücre
tahmin süresi   : 17 ms/araç
isabet          : %93,7 hat · %86,5 yön   (yavaş sürümle aynı)
```

Tüm rotalar tek referans enlemle (41,05) aynı düzleme taşındı — hücre hesabı ve
izdüşüm aynı koordinat sisteminde olsun diye.

### ⭐⭐ KAYDEDİCİ v3 — tahmin devrede

Her tur, tahmini en eski **220 hareketli araç** işleniyor (araç başına tazeleme
~10 dakika). Tur zamanlaması bozulmadı, kota harcanmıyor.

`arac_hat` tablosuna **`kaynak`** sütunu eklendi:
`servis` (hat sorgusu — gerçek) · `geometri` (rota eşleştirme — %93,7)

### İlk ölçüm (28 Ağustos 10:31, iki dakikalık pencere)

```
geometri : 142 eşleme ·  75 hat
servis   :  10 eşleme ·   2 hat
```

> Aynı sürede geometri, servisin **14 katı eşleme** ve **37 katı hat kapsaması**
> üretiyor — hem de kotadan tek istek harcamadan. Bölüm 29'daki %2,2'lik
> hat×saat kapsaması darboğazının çözümü bu.

⚠️ **Etkisi henüz doğrulanmadı.** Yanlış alarmın gerçekten düşüp düşmediği ancak
birkaç saat veri biriktikten sonra `gunluk.py` yeniden koşulunca görülecek.

---

## 31. 3. SEANS SONU — 28 Ağustos akşamı, YARIM KALAN DENEY

### Yapılanlar

1. **Geometrik hat tahmini kaydediciye bağlandı** (v3) — her tur 220 hareketli araç,
   ~17 ms/araç, kotadan istek harcamıyor.
2. **Geriye dönük tahmin** — 27 Ağustos'un konum verisi üzerinde çalıştırıldı:
   ```
   417.019 tahmin denendi · 90.142 karar (%22) · 666 hat
   hat×saat kapsaması: %2,2 → %42,6   (19 kat)
   ```
3. **Geçiş çıkarımı yeniden başlatıldı** — 708 hat, yeni eşlemelerle.
4. **Zincir kuruldu** — çıkarım bitince WAL'a geçip `gunluk.py 20260827` koşacak.

### ⚠️ ÇÖZÜLEN ARIZA — veritabanı kilidi kaydediciyi ÖLDÜRDÜ

`gecisler.py` uzun yazma işlemleri yaparken kaydedici `database is locked` alıp
**çöktü, 21 dakika veri kaybedildi** (16:11–16:32). Üstelik hatayı kaydetme yolu da
aynı kilide takıldığı için istisna döngüyü kırdı — yani koruma mekanizmasının kendisi
çöktü.

**Üç düzeltme:**
- `busy_timeout=90000` — kilitte hata vermek yerine bekle
- `_not_dus()` — hata kaydı yazılamazsa sessizce geç. *Tek bir kaydı yazmak,
  sürecin ayakta kalmasından önemli değil.*
- `gecisler.py` artık **her hatta bir** commit yapıyor, kilidi uzun tutmuyor

Düzeltmeden sonra ikisi yan yana sorunsuz çalıştı.

⚠️ **WAL kipine geçilemedi** — o ayar anlık bir dışlayıcı kilit istiyor, iki süreç de
bağlıyken olmuyor. Zincir, çıkarım bitince kaydediciyi 3 saniye durdurup deneyecek.

### 🔜 YARIN İLK İŞ — cevabı bekleyen tek soru

Kapak kapandığı için deney yarım kaldı. Mac açılınca zincir kendiliğinden devam eder.

```
SABAH (eşleme kapsaması %2,2):
  6.291 kalkış · %74,6 doğru · 1.487 YANLIŞ ALARM · %37 iptal yakalama

AKŞAM (kapsama %42,6) → ?
```

**Üç ihtimal, üçü de öğretici:**
- **Yanlış alarm düştü** → geometrik eşleme doğru çözümdü, yola devam
- **Değişmedi** → sorun eşlemede değil, hizalama mantığında; oraya bakılmalı
- **Arttı** → geometrinin %6 yanlış ataması yeni hata kaynağı; `USTUNLUK` eşiği
  yükseltilmeli (şu an 3,2) ya da yalnızca `kaynak='servis'` eşlemelerine güvenilmeli

### Uyku / taşıma notu

`sudo pmset -a disablesleep 1` **kullanılmadı ve kullanılmamalı** — kapalı çantada
uyumayan Mac ısınır, pil biter. Kapak kapanınca süreçler ölmez, **donar**; açılınca
kaldıkları yerden devam ederler. Kayıp yalnızca o süredeki veridir ve `yoklama`
tablosu o boşluğu "biz bakamadık" diye kaydeder — analiz iptal sanmaz.

---

## 32. ⭐ DENEYİN SONUCU — geometrik eşleme işe yaradı, ama yetmedi (29 Ağustos 01:04)

Zincir gece kendiliğinden tamamlandı. Aynı gün (27 Ağustos), aynı kod, tek fark
**araç→hat eşlemesinin kapsaması**.

```
                              SABAH        GECE
                          (kapsama %2,2)  (%42,6)
  ------------------------------------------------
  hat sayısı                     259         607   ↑
  kapsanan kalkış               6.291      26.679  ↑
  genel isabet                  %74,6       %94,9  ↑

  yanlış alarm (adet)           1.487         619  ↓
  yanlış alarm ORANI            %23,6        %2,3  ↓  ⭐

  iptal yakalama (recall)         %37         %13  ↓
  iptal İSABETİ (precision)      %4,1       %15,0  ↑
```

### Okunuşu

**⭐ Asıl kazanç yanlış alarm oranında: %23,6 → %2,3 (on kat).** Sabah kalkışların
dörtte birinde "iptal" diyecektik; şimdi kırkta birinde. Üstelik bunu **dört kat daha
fazla kalkışı** değerlendirirken başardık.

**⚠️ Recall'ün düşmesi (%37 → %13) kötü değil, dürüstleşme.** Sabahki %37 bir yetenek
değil, **aşırı işaretlemenin yan ürünüydü**: kalkışların dörtte birine "iptal" dersen
gerçek iptallerin bir kısmını da tesadüfen yakalarsın. Doğru ölçü precision ve o
**%4'ten %15'e** çıktı.

### ⛔ AMA HÂLÂ GÖNDERİLEBİLİR DEĞİL

```
"iptal" dediğimiz her 100 kalkıştan 15'i gerçekten iptal.
Yani 85'inde yolcuya yanlış söylüyoruz.
```

Ürünün tek kozu güven; bu haliyle ekrana konamaz. **Geometrik eşleme doğru yoldu ama
tek başına yetmedi.**

### Nerede duruyoruz

- Bazı hatlarda yöntem **tertemiz**: `BA-2` 382 kalkış, `429A` 232, `500T` 220,
  `19F` 226 — hiçbirinde yanlış alarm yok.
- Bazılarında bozuk: `15BK` 9, `13` 8 yanlış alarm.
- **Bu ayrımın sebebi henüz bilinmiyor.** İlk bakılan şey eşleme yoğunluğuydu, ayırt
  etmedi (hepsinde ~14 saat kapsama var).

### 🔜 Sıradaki iş — öncelik sırasıyla

1. **Temiz hatlar ile bozuk hatları ayıran şeyi bul.** Elimizde 607 hatlık bir tablo
   var; hat uzunluğu, sefer sıklığı, varyant sayısı, kalkış durağı seçimi gibi
   değişkenlerle karşılaştır. Bu, en hızlı öğrenme yolu.
2. **Eşleme kapsamasını %42,6'dan yukarı çek.** Hâlâ zamanın yarısından fazlasında
   hattın araçlarını görmüyoruz. `USTUNLUK` eşiği (3,2) düşürülüp isabet/kapsama
   dengesi yeniden ölçülebilir.
3. **Ürün kararı:** iptal iddiası yalnızca **temiz çıkan hatlarda** gösterilsin,
   diğerlerinde "bilmiyorum" densin. Kötü bir özelliği herkese göstermektense
   iyi çalıştığı yerde göstermek daha doğru.

---

## 33. ⛔⛔ TIKANIKLIĞIN KÖKÜ BULUNDU — 31 Ağustos, dört gün ve altı hipotez sonrası

### Dört günlük plato

```
27 Ağu  precision %15,0    28 Ağu  %11,5    29 Ağu  %11,6    30 Ağu  %12,5
```

Yüz binden fazla kalkış, hep aynı bant. İyileşme eğilimi yok.

### Altı hipotez, altı ret

| hipotez | sonuç |
|---|---|
| okul ringi / servis tipi farkı | ✗ temiz ve bozuk hatlar aynı tiplerden (ÖHO, OAS) |
| ortak koridor yoğunluğu | ✗ temiz ortanca 33,0 · bozuk 32,0 hat/hücre — fark yok |
| hat büyüklüğü / araç sayısı | ✗ eşik ne olursa olsun precision %13 civarı; ≥30 araçta %8'e **düşüyor** |
| kalkış durağı gözlenemiyor | ✗ yalnızca 2 hat (BU-1 Burgazada); toplam yanlış alarmın %6'sı |
| hizalama hatalı | ✗ **hizalama doğru çalışıyor** — komşu geçişler kendi planlarına 1 dk hassasiyetle oturuyor |
| sekiz özellikli sistematik tarama | ✗ hiçbir dilimde belirgin fark (hepsi %1,6-3,4) |

> **Hata belirli hatlarda değil, her yere eşit dağılmış.** Yani sorun bir kusurda
> değil, yöntemin kendisinde.

### ⭐ ASIL SEBEP — "yanlış alarm" dediğimiz şey gerçekte neydi

166 vaka tek tek izlendi (arşiv seferi yapan aracı da veriyor):

```
%71  araç konum bildiriyordu → gecikme/çakışma yüzünden yanlış plana yazıldı
%29  araç HİÇ (ya da <5 kez) bildirmemiş → GPS KARANLIĞI
```

**Somut örnek — hat 336, plan 07:20:**
```
planlar : 07:10   07:20   07:30
geçişler: 07:10           07:31
arşiv   : 07:20 seferi 07:30'DA kalktı (10 dk gecikme)

bizim hizalama: 07:31 geçişini 07:30 planına verdi → 07:20 hayalet sayıldı
```

İki plan, tek geçiş. **Bir seferin eksik olduğunu doğru gördük ama yanlış slota
yazdık.** Ölçüde iki kere ceza: hem yanlış alarm hem kaçırma.

> ⚠️ **Bu bir yazılım hatası değil, bilgi sınırı.** Gecikme sefer aralığına
> yaklaşınca hangi seferin yapılmadığı belirlenemez — aynı veriye bakan bir insan da
> ayıramaz.

### Sayarak bakmak daha iyi ama yetmiyor

Tek tek atama yerine "bu saatte kaç sefer eksik" diye sayınca:

```
tek tek sefer atama     precision %13
saatte ≥1 eksik         precision %33 · recall %23
saatte ≥2 eksik         precision %52 · recall  %8
korelasyon r = 0,14  (zayıf)
```

2,5-4 kat daha iyi ama hâlâ güvenilir değil.

---

## 34. ⭐ STRATEJİ DEĞİŞİKLİĞİ ÖNERİSİ — "iptal" yerine "görünmüyor"

Dört günlük ölçüm şunu söylüyor: **tek tek sefer iptalini konum verisinden
saptamak, bu verinin taşıyabileceğinin sınırında.** Sefer yapılıp araç bildirmediğinde
(vakaların %29'u) iptal ile GPS karanlığı **veride birbirinin aynısı** — ayırt edecek
bilgi yok.

**Ama ürünün buna ihtiyacı yok.** Sağlam ve gönderilebilir olan üç kademe zaten var:

```
🚌 CANLI    "otobüs 460 m ötede, ~1 dakika"           güven yüksek, ölçüldü
📊 GÖZLEM   "bu durakta bu saatte ortanca 23 dk'da bir geçiyor · son geçiş 12 dk önce"
⏱  TARİFE   plan
```

**Önerilen dördüncü satır — "iptal" iddiası yerine kalibre edilmiş belirsizlik:**

```
⚠️ 23:30 seferi görünmüyor.
   İptal olabilir ya da aracın GPS'i kapalı olabilir.
   Geçmişte böyle durumların %13'ünde sefer gerçekten yapılmadı —
   yani büyük ihtimalle otobüs geliyor ama izlenemiyor.
```

Bu cümle **her zaman doğru** (sefer gerçekten görünmüyor), yolcuya karar verdiriyor,
ve %87 yanılma riskini ortadan kaldırıyor. Ölçtüğümüz %13'lük oran da uydurma değil,
dört günlük doğrulamadan geliyor.

> Ürünün asıl değeri "iptal dedektörü" olmakta değil, **görünmeyeni görünür kılmakta**.
> Sefaköy'de sorun otobüsün iptal olması değildi; **hiçbir bilgi olmamasıydı.**

### 🔜 Karar bekleyen

- (A) "Görünmüyor + kalibre edilmiş oran" cümlesine geç, iptal iddiasını bırak
- (B) İptal tespitini sürdür ama yalnızca sayarak (saatte ≥2 eksik, precision %52)
- (C) Daha fazla veri biriktir; belki haftalık desenler yeni sinyal verir

---

## 35. ⭐⭐⭐ SAATLİ PARÇA MODELİ — ürünün asıl vaadi ölçüldü ve 3 kat iyileşti (31 Ağustos)

### Mehmet'in itirazı yön değiştirtti

3. seansta iptal tespiti tıkanınca "görünmüyor" cümlesine geri çekilmek önerilmişti.
Mehmet reddetti ve asıl farkı hatırlattı:

> *"projenin asıl farkı hayalet GPS'li aracın kaç dakikada durağa varıp varmadığını
> tespit etmesi... 98'in 23:00'te Bakırköy'den Sefaköy'e varacağı süre ile saat
> 14:00'takı aynı olamayacaktır"*

**Haklıydı ve o kısım hiç ölçülmemişti.**

### Eski modelin kusuru

Hattın **tek bir ortanca süresi** alınıp rota oranıyla çarpılıyordu:
*"yolun %28'ini yaptıysa sürenin de %28'ini harcamıştır."*

İki varsayım da yanlış: şehir içi bölüm ağır çevre yolu hızlı, **ve** saat 18'deki
trafik saat 23'tekiyle aynı değil.

### Yeni model — `sure_modeli.py`

`gecis` tablosunda hangi aracın hangi duraktan kaçta geçtiği yazıyor. Aynı aracın
**ardışık iki durak geçişi** bir parça süresi verir. Bunlar
**(hat, yön, parça, gün tipi, saat)** kırılımında toplanıp ortancası alınıyor.

```
716.682 parça-saat kaydı · 142.553 yedek (saatsiz) · 636 hat
```

⭐ **Saat ilerletilerek toplanıyor:** 23:00'te kalkan otobüs 40. dakikasında 23:40'ın
parça sürelerini yaşar. Uzun hatlarda bu fark büyük.

### ⭐ Mehmet'in örneği — 98 · Bakırköy → Sefaköy Merkez

```
saat    YENİ model   ESKİ model
06:00   20,9 dk      21,3 dk
14:00   36,2 dk      21,3 dk
18:00   53,1 dk      21,3 dk    ← 32 dakika yanılıyorduk
23:00   25,8 dk      21,3 dk
00:00   20,5 dk      21,3 dk
```

### ⭐⭐ TARAFSIZ ÖLÇÜM

⚠️ İlk karşılaştırma yanlıydı: "gerçek" olarak yeni tahmine en yakın geçiş seçilmişti,
bu doğal olarak yeni modeli kayırır. Sıraya göre eşleştirme de çöktü (ikisinde de
38 dk hata — planlar ve geçişler sırayla denk gelmiyor).

**Doğru referans araç kimliği:** kalkış durağından geçen aracın, orta duraktaki
kendi geçişi. Hiçbir modelin tahminini kullanmaz.

```
9.276 gerçek sefer · 30 Ağustos

ESKİ (rota oranı)    ortanca 5,12 dk · ≤3dk %33 · ≤5dk %49
YENİ (saatli parça)  ortanca 1,71 dk · ≤3dk %70 · ≤5dk %84

ortanca hatada iyileşme: %67
```

`durakta_ne_var.py` bu modeli kullanıyor; yeterli saatli veri yoksa genel ortancaya
düşüyor ve bunu çıktıda **açıkça söylüyor** ("18 parça o saatin verisinden,
3 parça genel ortalamadan").

### Ders

Üç gün iptal tespitini kovaladık ve yedi hipotezin yedisi de elendi. Asıl fark
yaratan iş, hiç ölçmediğimiz yerdeydi. **Ürünün ne olduğunu kullanıcı, neyin
ölçüleceğini veri söyler — ikisini karıştırmamak gerekiyor.**

---

## 36. ⭐ MODEL ARTIK CANLI — kayan pencere + kendini ayarlama (31 Ağustos)

### Mehmet'in ikinci itirazı

> *"haftalarca veri topladığımızda bu verilerden yapılan zaman çıkarımı güncel
> olmasını istiyorum... 98 Bakırköy'den Pazartesi 13:00'da 56 dk'da Sefaköy'de oldu,
> Salı da 56 dk çıkarımı yapılmasın; her geçen gün daha isabetli olsun"*

İki ayrı eleştiri vardı:
1. **Tek gözlemden çıkarım yapılmasın** → zaten yapılmıyordu (ortanca, n kayıtlı)
2. **Model donmasın, her gün tazelensin** → ⚠️ **haklıydı, model ELLE kurulmuştu**

### ⚠️ "Ne kadar çok veri o kadar iyi" YANLIŞ ÇIKTI

30 Ağustos'u tahmin etmek için farklı miktarda geçmişle eğitim:

```
2 günlük veri → ortanca hata 2,82 dk
3 günlük veri → ortanca hata 3,29 dk   ← DAHA KÖTÜ
EWMA α=0,5    → 3,29 dk    EWMA α=0,7 → 3,26 dk   (havuzu geçemedi)
```

Geçmişi biriktirip ortancasını almak isabeti **düşürüyor**. 27 Ağustos'un verisi
daha gürültülü (hat atamaları geriye dönük üretilmişti, %6 yanlış atama payı var).

### ⭐ Çözüm: sabit pencere değil, KENDİNİ ÖLÇEN pencere

Doğru pencere boyu veri biriktikçe **değişecek** — bugün 2 gün kazanırken üç hafta
sonra 7 gün kazanabilir (haftalık desenler oturunca). O yüzden sabitlenmedi:

`sure_modeli.pencere_ayarla()` her gün **2, 3, 5, 7, 10, 14 günlük** pencereleri
dün üzerinde deneyip en iyisini seçiyor ve kaydediyor. `kur()` o pencereyi kullanıyor.

`gunluk.py` artık dört adımlı: arşiv → geçişler → **süre modeli tazeleme** → doğrulama.
Her sabah 09:00'da kendiliğinden koşuyor.

### ⚠️ BULUNAN KUSUR — hafta sonu

İlk ayarlama denemesi 30 Ağustos (**pazar**) üzerinde yapıldı ve hiç sonuç vermedi:
eğitim verisi aynı gün tipiyle sınırlandığı için 2-14 günlük pencerede **başka pazar
yok**. Hafta sonları için kısa pencere işe yaramıyor.

> Pencere takvim günü yerine **aynı gün tipinden kaç gün** diye sayılmalı.
> Şu an 4 günlük veriyle sorun görünmüyor ama hafta sonu tahminleri zayıf kalacak.
> **Açık borç.**

### Şu anki durum

4 günlük veriyle altı pencere de aynı sonucu veriyor (3,18 dk) — çünkü 2 günlük
pencere bile tüm geçmişi kapsıyor. **Mekanizma çalışıyor, ayırt edecek veri henüz yok.**
Zaten beklenen bu: fark veri biriktikçe ortaya çıkacak.

---

## 37. VARIŞ TAHMİNİ HER DURAKTA GEÇERLİ Mİ? — ölçüldü (31 Ağustos)

Model önce yalnızca rotanın ortasındaki bir durakta ölçülmüştü (1,71 dk). Hata
mesafeyle birikeceği için uzak duraklarda ürünün vaadi zayıflayabilirdi. Ölçüldü:

```
rota üzerindeki yer   yolculuk   ortanca hata   ≤3dk   BAĞIL hata
%10                     4,0 dk       0,42 dk     %92      %10
%30                    16,0 dk       1,08 dk     %82       %7
%50                    27,0 dk       1,55 dk     %72       %6
%70                    37,5 dk       2,04 dk     %64       %5
%90                    49,4 dk       2,54 dk     %56       %5
```

⭐ **Bağıl hata mesafeyle AZALIYOR** (%10 → %5). Mutlak hata büyüyor ama doğrusaldan
yavaş: parça hataları birikmiyor, birbirini kısmen götürüyor.

> Elli dakikalık yolculuğun sonunda ortanca hata 2,5 dakika. Hattın son durağındaki
> yolcuya bile anlamlı bir cevap verilebiliyor.

**Ürün açısından:** vaat yalnızca yakın duraklar için değil, hattın tamamı için geçerli.

---

## 38. ⭐⭐⭐ iOS UYGULAMASI — motor artık telefonda (31 Ağustos)

Mehmet'in kararı: *"profesyonel iOS uygulaması yapanlar Xcode kullanıyorsa onu
kullanalım"*. Doğru karar — SwiftUI önizlemesi ve simülatör entegrasyonu orada.

### Ortam — hiçbir şey kurulmadı

```
Xcode 26.4.1 ✅   Swift 6.3.1 ✅   iPhone simülatörleri ✅   Node.js ❌ (gerekmedi)
```

React Native seçilseydi Node.js kurulumu gerekiyordu; SwiftUI ile sıfır kurulum.

### Yapı

```
ios/
  OtobusumNerede.xcodeproj      elle yazılmış proje (senkronize klasör grubuyla)
  Info.plist                     yerel ağ (ATS) + konum izinleri
  OtobusumNerede/
    OtobusumNeredeApp.swift      giriş
    Tema.swift                   renkler — pano ve web arayüzüyle aynı dil
    Modeller.swift               JSON karşılıkları
    Servis.swift                 sunucu katmanı, adres ayarlanabilir
    AramaGorunumu.swift          durak ara · yakınımdakiler (CoreLocation)
    DurakGorunumu.swift          ASIL EKRAN · 30 sn'de bir tazelenir
    AyarlarGorunumu.swift        sunucu adresi
arayuz_sunucu.py                 motoru JSON'a çeviren arka uç (port 8790)
arayuz.html                      aynı arayüzün tarayıcı sürümü
```

### ⚠️ Derlemede çıkan iki hata

1. **`Info.plist` çakışması** — senkronize klasörün içinde kaldığı için hem Info.plist
   hem kaynak dosya sayıldı. Klasörün dışına alındı.
2. **`is` ayrılmış kelime** — `calistir(_ is:)` parametre adı Swift'te geçersiz.
   `getirici` yapıldı.

### ⚠️ Simülatörde görülen ürün hatası — düzeltildi

Ekranda **"429 DAKİKA"** yazıyordu. Sebep Bölüm 21'deki bulgunun ta kendisi: 98'in
D yönünde gündüz tarifesi yok, sıradaki kalkış 6,5 saat sonra.

**İki düzeltme:**
- `TARIFE_UFKU_DK = 120` — bu ufkun ötesindeki tarife satırı gösterilmiyor
- **Gözlemden sıradaki geçiş kestirimi**: canlı araç ve yakın tarife yoksa,
  *"20 dk'da bir geçiyor, sonuncusu 12 dk önceydi → sıradaki ~8 dk"*.
  Tarifenin sustuğu yerde tek anlamlı cevap bu.

### Çalışan ekran (simülatör, 16:49)

```
98S · KANUNİ SULTAN SÜLEYMAN · 19/41. durak · rotanın %47'i
  📊 bu saatte ortalama 12 dk'da bir geçiyor
  🚌 0,57 km uzakta · araç B5051                      1 DAKİKA
  🚌 1,19 km uzakta · 22 km/sa · araç B5217           3 DAKİKA
  ⏱  17:00 kalkışı → 17:24–17:37                     41 DAKİKA

98 · FENERTEPE PERONLAR · 19/76. durak · rotanın %28'i
  📊 bu saatte ortalama 20 dk'da bir geçiyor
  🚌 0,95 km uzakta · 21 km/sa · araç A-1853          3 DAKİKA
```

### 🔜 Açık işler

- **Cevap süresi yavaş** (aşağıda ölçüldü) — her durak sorgusu hattaki tüm araçlar
  için yön tespiti çalıştırıyor. Önbellek gerekiyor.
- Sunucu Mehmet'in bilgisayarında; telefon aynı Wi-Fi'de olmalı.
- Uygulama ikonu yok (yer tutucu asset).

---

## 39. ⭐⭐ HIZ: 43 SANİYEDEN 0,17 SANİYEYE (1 Eylül)

### Profil tahminimi çürüttü

Yavaşlığın geometri hesabından geldiğini sanıyordum. Profil başka söyledi:

```
toplam 43,4 sn
  34,9 sn  sqlite execute          ← SORGULAR
  29,2 sn  hatta_atanmis_araclar   ← tek sorgu
   3,8 sn  sqlite3.connect         ← 704 kez bağlantı açılmış
   1,5 sn  rota.yol_uzerinde       ← geometri masum
```

### Dört düzeltme

**1. Bağlantı yeniden kullanımı.** Her yardımcı fonksiyon kendi bağlantısını açıp
kapatıyordu. Tek durak sorgusunda 704 bağlantı. Artık tek bağlantı kilitle
paylaşılıyor (`check_same_thread=False`, WAL kipinde salt okuma — güvenli).
⚠️ İş parçacığı-yerel bağlantı denendi ama sunucu her istek için yeni iş parçacığı
açtığı için işe yaramadı; paylaşılan bağlantıya geçildi.

**2. Araç→hat sorgusu yeniden yazıldı.** Eski sorgu önce HER aracın son atamasını
hesaplayıp sonra hatta göre süzüyordu — `arac_hat` 292 bin satıra çıkınca 29 saniye.
Artık önce hatta göre süzülüyor (indeksli), sonra `NOT EXISTS` ile "daha yeni ataması
var mı" bakılıyor.

**3. İki eksik indeks.**
```
gecis  (durak_kodu, hat, yon, zaman)   ← 35 sn'de kuruldu, 11,6 milyon satır
tarife (hat_kodu, gun_tipi, yon, saat)
```
`gecis` sorgusu `durak_kodu + hat + yon` ile süzüyordu ama indeks yalnızca
`(durak_kodu, zaman)` idi; yoğun duraklarda o durağın TÜM hatları taranıyordu.

**4. Gözlem sorgusundan `strftime` kaldırıldı.** Saat süzmesi SQL'de yapılınca
indeks kullanılamıyor, 11,6 milyon satır taranıyordu. Artık önce tarih aralığı
(7 gün) ile daraltılıyor, saat süzmesi Python'da.

### Sonuç

```
                    ÖNCE      SONRA
Sefaköy (15 hat)   43 sn     0,17 sn
Vefa    (52 hat)    —        0,62 sn
durak arama          —       0,04 sn
```

---

## 40. ⚠️ GÖZLEM KATMANI BAYATTI — sürekli çıkarım eklendi (1 Eylül)

Simülatörde **her hat "gecikti"** diyordu. Sebep:

```
son konum kaydı : 10:35  ✅ güncel
son GEÇİŞ kaydı : 09:00  ⚠️ 1,5 saat eski
```

`gecis` tablosu yalnızca günlük rutin çalışınca (09:00) güncelleniyordu. Gün boyunca
"son geçiş" hep saatler öncesini gösteriyor, gözlem katmanı anlamsızlaşıyordu.

**`gecis_dongusu.sh`** eklendi: `gecisler.py`'yi 10 dakikada bir çalıştırır.

### ⚠️ Artımlı çalışmada bulunan ikinci hata

Kısa pencerede (76 dk) araç→hat eşlemesi de yalnızca o pencerede aranıyordu.
Bir hattın araçlarının çoğu daha önce eşlendiği için hiç taranmıyordu:

```
07:00 → 188.170 geçiş   (tam gün taraması)
09:00 →  49.842 geçiş   (artımlı — dörtte biri)
```

**Düzeltme:** konumlar yeni pencereden alınır ama **eşleme 4 saat geriye bakar**
(`ESLEME_GERIYE_SAAT`). Düzeltmeden sonra Sefaköy'de 98'in geçişleri kesintisiz:
`08:40 09:24 09:40 09:44 09:46 10:04 10:18`

### İki küçük ürün düzeltmesi

- **"gecikti" işareti**: son geçiş ortalama aralıktan uzunsa "şimdi" demek fazla
  iddialı. Ayrı gösteriliyor.
- **Sıralama**: gecikmiş satırlar 0 dk sayıldığı için 1 dakika sonra gelen otobüsün
  önüne geçiyordu. Gelen otobüsler öne alındı, gecikmiş uyarılar sona.

---

## 41. ⭐⭐ TASARIM GERÇEK EKRANDAN ALINDI (1 Eylül)

Mehmet sahadaki akıllı durak ekranının fotoğrafını getirdi (`notlar/durak_ekrani.png`).

⚠️ **İlk temam yanlıştı.** Koyu lacivert zemin + kehribar rozet kullanıyordum; bunu
"durak ekranı böyledir" diye tahmin etmiştim. Gerçek ekran **AÇIK temalı**.

### Gerçek ekranın yapısı

```
mavi degrade başlık   → yön eyebrow + DURAK ADI (beyaz, büyük) + İETT/İBB amblemleri
bilgi çipleri         → 21°C · 01.09.2026 · 08:15
sıradaki seferler     → koyu lacivert hat rozetleri + "1 dk 2 dk 3 dk"
yeşil tablo başlığı   → KAPI NO · HAT KODU · HAT ADI · AKTARMA · VARIŞ
beyaz satırlar        → koyu lacivert yazı, dönüşümlü zemin
turuncu duyuru şeridi → kayan yazı (aşağıya bak — çok önemli)
alt bilgi             → Durak Kodu + QR + reklam + %54 göstergesi
```

Renkler fotoğraftan piksel örneklemeyle alındı (cam yansıması yüzünden soluk çıkan
değerler temizlendi):

```
başlık mavisi   #3F6FB5 → #5B8CD0 degrade
İETT yeşili     #3E9B6A   (sütun başlığı)
duyuru turuncu  #E4813C
hat rozeti      #23324D   (koyu lacivert)
yazı            #1E2A3F · gövde beyaz · sayfa #EEF2F7
```

`Tema.swift` tamamen yeniden yazıldı; uygulama açık temaya geçti.

> **Neden bu doğru karar:** İstanbullu o ekranı zaten tanıyor. Aynı görsel dili
> kullanmak uygulamayı öğrenilecek yeni bir şey olmaktan çıkarıp **tanıdık bir şeyin
> cebe girmiş hâli** yapıyor.

### Mobil uyarlamada değişen tek şey

Gerçek ekranda yeşil tablo başlığı bir kez var ve altında tüm satırlar. İlk mobil
denemede her hat kartına ayrı yeşil başlık koydum — gürültülü oldu. Tek başlığa
düşürüldü; gecikme uyarısı artık kartın tepesindeki **turuncu şerit** ile veriliyor
(ekrandaki duyuru şeridinin karşılığı).

---

## 42. 🔥 FOTOĞRAFTAKİ ASIL BULGU — İPTAL DUYURULARI VAR

Ekranın alt kısmındaki turuncu kayan şeritte şu okunuyor:

```
...acaktır. ◄ İGTOT kalkışlı 09:45 seferi,
YENİBOSNA METRO kalkışlı 08:20 seferi yapıla[mayacaktır]
```

⭐⭐ **Bu, Bölüm 29-33'te günlerce aradığımız ve bulamadığımız veri.**

Akıllı duraklar sefer iptali duyurusunu **kalkış saati ve kalkış yeri düzeyinde**
alıyor. Yani böyle bir akış var; biz SOAP servisinde bulamadık (`GetDuyurular_XML`
hiçbir WSDL'de yok, `GetYolcuBilgilendirme_json` geçitte kapalı).

**Neden bu kadar önemli:** konum verisinden iptal çıkarmaya çalışırken yedi hipotez
denendi, precision %13'te tıkandı ve bunun bir **bilgi sınırı** olduğu görüldü
(Bölüm 33). Duyuru akışı bulunursa tahmin etmeye hiç gerek kalmaz — okunur.

### İzler

- Ekranın sol altında **`Durak Kodu 101321` ve bir QR kod** var. QR muhtemelen o
  durağın web sayfasına gidiyor; aynı duyuru orada olabilir.
- Ekranın altında sürüm bilgisi (`v1.6.1`) ve buton çubuğu var — bir web uygulaması
  olduğuna işaret ediyor, yani bir HTTP uç noktası çağırıyor.

### 🔜 Sıradaki iş — öncelik yüksek

1. QR kodu çözüp hedef adresi bul (fotoğraf yeterince net mi, bakılmalı)
2. O adresin döndüğü veriyi incele — duyuru alanı var mı
3. Varsa `hayalet.py` tahmin yerine bu akışı kullansın

### Tasarım ikinci tur — Mehmet'in düzeltmeleri (1 Eylül)

| istek | yapılan |
|---|---|
| daha koyu mavi | `#3F6FB5` → **`#19386D`**, degrade dikey |
| İBB solda, İETT sağda, beyaz | `Amblemler.swift` — SwiftUI'da çizildi |
| tablolarda gölgelendirme | iki katmanlı gölge (yakın/keskin + uzak/yumuşak), maviye çalan ton |
| üstte yatay hat şeridi | `HatSeridi` — tüm hatlar yan yana: rozet + hedef + kaç dk |

**Amblemler neden çizildi:** fotoğraftaki gerçekleri ~50 piksel ve su damlalarıyla
kaplıydı, varlık olarak kullanılamadı. İBB için lale silueti (`Lale: Shape`),
İETT için oval çerçeve. Resmi şeffaf PNG bulunursa `Amblemler.swift` değiştirilir.

**Gölge kararı:** düz siyah gölge açık temada kirli görünüyor; gölgeler `Tema.mavi`
tonunda ve iki katmanlı (2pt keskin + 10pt yumuşak).

**Şeritte hedef mi tam hat adı mı:** hedef seçildi ("FENERTEPE PERONLAR"), çünkü
durakta duran için önemli olan otobüsün *nereye gittiği*; hattın iki ucu değil.

---

## 43. AMBLEMLER GERÇEK DOSYALARA GEÇTİ (1 Eylül)

⚠️ İlk sürümde iki amblem de SwiftUI'da **çizilmişti** — tahmine dayalıydı ve
gerçeğinden farklıydı. Mehmet resmi logoları verdi, ikisi de gerçek dosyaya bağlandı.

### Yöntem — şablon görsel (template image)

Logolar renkli ve zeminliydi (İBB koyu lacivert/beyaz zemin, İETT kırmızı/şeffaf).
Mavi başlıkta beyaz görünmeleri gerekiyordu. Yapılan:

1. Görsel **"dolu mu boş mu"** bilgisine indirgendi — şeklin kendisi korundu,
   yalnızca alfa kanalı üretildi
2. `Assets.xcassets`'e `template-rendering-intent: template` ile eklendi
3. Renk artık **uygulamadan** geliyor (`amblemRengi` = `#E9EFF6`)

> Şablon görselde şekil dosyadan, renk koddan gelir. Bu yüzden kırmızı İETT logosu
> ve lacivert İBB logosu tek satır değişiklikle aynı tonda beyaz çıkıyor.

**İki kaynak, iki farklı yol:**
- `ibb amblem` (WebP, 1200×675) — **beyaz zeminli**, alfa yok → koyuluktan alfa üretildi
- `IETT amblemm.png` (181×308) — **zaten şeffaf** → alfa olduğu gibi korundu

Kod ikisini de tanıyıp doğru yolu seçiyor (`şeffaf piksel örneklemi` kontrolü).

**İBB'de ek işlem:** logo "İSTANBUL BÜYÜKŞEHİR BELEDİYESİ" yazısını da içeriyordu.
Satır satır koyu piksel yoğunluğu taranıp simge ile yazı arasındaki **28 piksellik
boşluk** bulundu, oradan kesildi. Sonuç: 191×251, yalnızca lale/kubbe simgesi.

⚠️ Masaüstünde iki İETT logosu vardı; `istanbul-elektrik-tramvay-logo-seeklogo.png`
çevresinde halka yazı taşıyor, kullanılmadı. Sade oval olan seçildi.

---

## 44. TASARIM — sahadaki ekranın mobil karşılığı, son hâl (1 Eylül)

### Başlık şeridi

```
[İBB amblemi]      KÜÇÜKÇEKMECE      [İETT amblemi]
              SEFAKÖY MERKEZ
   [📅 1 Eyl 2026] [🕐 14:16] [⛅ 30°C]
```

- Mavi **koyulaştırıldı**: `#3F6FB5` → `#19386D`, degrade dikey
- Amblemler `#E9EFF6` (hafif kırık beyaz — saf beyaz mavi zeminde sert duruyordu)
- Çip simgeleri **koyu turuncu** `#D86614`

### Hava durumu

Sahadaki ekranda sıcaklık gösteriliyor; aynısı eklendi. Kaynak **open-meteo**
(ücretsiz, anahtar istemiyor), durağın **kendi koordinatına** göre soruluyor,
10 dakika önbellekte. Simge WMO hava koduna göre değişiyor — açıkta güneş,
yağmurda bulut. *Hep güneş göstermek yağmurlu günde yanlış olurdu.*

### Yatay hat şeridi

Sahadaki ekranın tepesindeki şeridin karşılığı: tüm hatlar yan yana, rozet + hedef +
kaç dakika. Yolcunun ilk gördüğü şey bu.

⚠️ Şeritte **hedef** yazılıyor (`FENERTEPE PERONLAR`), tam hat adı değil
(`BAKIRKÖY - FENERTEPE`) — durakta duran için önemli olan otobüsün *nereye gittiği*.

### Gölgelendirme

Kartlarda **iki katmanlı** gölge: 2pt keskin + 10pt yumuşak, ikisi de `Tema.mavi`
tonunda. Düz siyah gölge açık temada kirli görünüyordu.

### Kaldırılanlar

- **Durak kodu çipi** → yerine sıcaklık
- **Yeşil sütun başlığı** → kaldırıldı; ekran sadeleşti, kartlar doğrudan başlıyor
- Kart başına tekrar eden yeşil başlık → önce tek başlığa indirildi, sonra tamamen kalktı

Gecikme uyarısı artık kartın tepesindeki **turuncu şerit** ile veriliyor.

---

## 45. DOSYA DÜZENİ — güncel

```
mobil otobüsüm nerede/
├── Otobüs Takip Uygulaması PROJE DURUMU.md   bu dosya
├── PROMPT_uygulama.md                        ilk gün yazılan ürün tanımı
│
├── VERİ BORU HATTI (arka planda çalışanlar)
│   ├── kaydedici.py          ⚙️ dakikada bir tüm şehir + geometrik hat tahmini
│   ├── gecis_dongusu.sh      ⚙️ 10 dk'da bir geçiş çıkarımı
│   ├── sabah_rutini.sh       ⚙️ her gün 09:00 · arşiv + model + doğrulama
│   └── arayuz_sunucu.py      ⚙️ port 8790 · iOS uygulamasının arka ucu
│
├── MOTOR
│   ├── hat_tahmini.py        araç → hat, rota geometrisinden (%93,7)
│   ├── gecisler.py           konum izinden durak geçişleri
│   ├── sure_modeli.py        saatli parça süreleri + kendini ayarlayan pencere
│   ├── rota.py               izdüşüm geometrisi
│   ├── yon_tespit.py         araç hangi bacakta + kendi hızı
│   ├── durakta_ne_var.py     üç kademeli cevap
│   └── hayalet.py            tarifede olup görünmeyen sefer
│
├── ARAÇLAR
│   ├── durak_dizini.py · tarife.py · sureler.py   (tek seferlik çekimler)
│   ├── gunluk.py · hat_analizi.py · gecmis_tahmin.py
│   ├── durum.sh · izle.sh                          (takip ekranları)
│   └── arayuz.html                                 (tarayıcı sürümü)
│
├── ios/
│   ├── OtobusumNerede.xcodeproj
│   ├── Info.plist                    yerel ağ + konum izinleri
│   └── OtobusumNerede/
│       ├── OtobusumNeredeApp.swift · Tema.swift · Modeller.swift
│       ├── Servis.swift              sunucu katmanı
│       ├── AramaGorunumu.swift       durak ara / yakınımdakiler
│       ├── DurakGorunumu.swift       ASIL EKRAN
│       ├── AyarlarGorunumu.swift     sunucu adresi
│       ├── Amblemler.swift           İETT + İBB (şablon görseller)
│       └── Assets.xcassets/          IBBAmblem · IETTAmblem
│
├── notlar/
│   ├── pano.html                     yayımlanmış proje panosu
│   ├── durak_ekrani.png              sahadaki akıllı durak fotoğrafı
│   └── (amblem ara dosyaları)
│
└── veri/                             ~4 GB
    ├── kayit.db      konum geçmişi · geçişler · araç-hat · süre modeli
    ├── dizin.db      duraklar · hatlar · tarifeler · arşiv · hat performansı
    ├── *.log         kaydedici · sabah rutini · geçiş döngüsü · arayüz
    └── rota_yollari.json · guzergahlar.json   (eski projeden)
```

---

## 46. 🔜 SIRADAKİ İŞ — 1 Eylül akşamı itibarıyla

**1. ⭐ İptal duyurusunun kaynağını bul** (Bölüm 42)
Sahadaki ekranın turuncu şeridinde sefer iptalleri kalkış saatiyle yazıyor.
Bu bulunursa yedi hipotezle çözülemeyen problem doğrudan okunarak çözülür.
İzler: durak ekranındaki QR kod · ekranın alt buton çubuğu · `v1.6.1` sürüm bilgisi.

**2. Canlı araç varken tarife satırlarını gizle**
`76O` hattında 2 dakikalık canlı otobüsün altında 44 dakikalık tarife satırı
görünüyor. Yolcu için gürültü. (Birkaç kez gündeme geldi, yapılmadı.)

**3. Gerçek telefonda saha denemesi**
Simülatör gerçek dünyayı göstermiyor. Bugünkü "bayat gözlem" hatası ancak
uygulama açılınca görüldü; sahada başka şeyler çıkacaktır.

**4. Hafta sonu penceresi** (Bölüm 36 açık borcu)
Pencere takvim günü sayıyor; cumartesi/pazar için aynı gün tipinden yeterli veri
toplanamıyor. "Aynı gün tipinden kaç gün" diye sayılmalı.

**5. Uygulama ikonu yok** — yer tutucu asset duruyor.

---

## 47. ⭐⭐⭐ İPTAL DUYURU AKIŞI BULUNDU — tahmin bitti, okuma başladı (1 Eylül, 4. seans)

Bölüm 42'deki fotoğraf bulgusunun izi sürüldü ve **kaynak bulundu.**

### İzin sürülüşü — iki çıkmaz, bir sonuç

| deneme | sonuç |
|---|---|
| **QR kod** (Bölüm 42'nin 1. izi) | ✗ çıkmaz |
| **Beş servisin WSDL'i yeniden** | ✗ duyuru biçimli metot yok |
| **İBB açık veri portalı** | ✅ **bulundu** |

**QR neden çıkmazdı:** macOS Vision ile ham fotoğraftan okundu →
`https://durak.iett.gov.tr/101321`. Ayrı bir React uygulaması; CAPTCHA + oturum +
RSA/AES korumalı, ve döndürdüğü alanlar yalnızca `hatkodu · hatadi · kapino · dakika`.
**Duyuru alanı yok.** Ekrandaki turuncu şerit oradan beslenmiyor.

⚠️ Yeniden taranan beş WSDL'de **`SeferGerceklesme` artık 36 değil 6 metot** yayımlıyor —
geçit tanımı daraltmış. Bölüm 8'in envanteri bu yönüyle **eskimiş.**

> Yan bulgu, kenarda duruyor: `GetKazaLokasyon_json` ve `GetBozukSatih_json` —
> kaza ve bozuk yol konumları. Gecikme açıklamak için ileride işe yarayabilir.

### ⭐ ASIL BULGU — bilinmeyen ALTINCI servis yolu

`data.ibb.gov.tr` (CKAN) İETT'nin yayımladığı **13 veri setini** listeliyor.
İçlerinden biri *"IETT Announcements Web Service"*:

```
https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx
  GetDuyurular_json   ·  PARAMETRESİZ  ·  HTTP 200 · 74 KB
```

**Bölüm 8'de BEŞ servis yolu taranmıştı; bu altıncısı listede hiç yoktu.**
`GetDuyurular_XML` adı da doğruymuş — "eski notlardaki isim yanlış olmalı" tespiti
yanlıştı, biz yanlış kapıları çalmışız.

> **Ders:** metot envanteri WSDL'den çıkarıldı, ama **servis yolu listesi**
> hiç doğrulanmamıştı — nereden geldiği bile belirsizdi. Açık veri portalı
> kataloğun kendisini veriyor; oradan başlanmalıydı.

### Gelen veri

```json
{"HATKODU":"10", "HAT":"Ü.EGT.ARS.HASTANESI - ATASEHIR / BOSTANCI",
 "TIP":"Sefer", "GUNCELLEME_SAATI":"Kayit Saati: 04:04",
 "MESAJ":"ÜMRANIYE EGITIM VE ARASTIRMA HASTANESI dan Saat 14:28 de hareket
          etmesi planlanan seferimiz çesitli nedenlerle yapilamayacaktir."}
```

```
304 duyuru · 157 hat
  Sefer  232   tek sefer iptali — kalkış yeri + kalkış saati taşıyor
  Günlük  72   güzergâh değişikliği, yol kapalı vb.

ayrıştırma: 232/232 · %100   ("<YER> dan Saat HH:MM de ... yapilamayacaktir")
```

### ⭐⭐ DOĞRULAMA — tarifeye dakikası dakikasına oturuyor

```
226 sefer iptali · bugünün tarifesiyle karşılaştırıldı

  birebir tutan          218   %96,5
  tutmayan                 8   (3'ü dizinde olmayan hat: 130S, 14SB, 92S)
```

> **Hizalamaya gerek yok.** Bölüm 24-33'te bu eşleştirmeyi yapabilmek için sıra
> koruyan dizi hizalaması yazıldı, uyarlanabilir tolerans kuruldu, yedi hipotez
> denendi ve precision %13'te tıkandı. Şimdi `(hat, gün tipi, saat)` ile düz bir
> birleştirme yetiyor. **Tahmin edilen şey artık okunuyor.**

### ⚠️ AKIŞ ARŞİV TUTMUYOR — KAYAN PENCERE

```
saat 14:29'da akıştaki iptallerin kalkış saatleri:  14:00 → 16:12
   14:00 →105    15:00 → 95    16:00 → 32
```

Sabahki iptaller akışta **yok, düşmüş.** Yaklaşık "şimdiden ~1,5-2 saat sonrasına"
kadar gösteriyor. **Yoklamazsak veri kalıcı olarak kayboluyor** — konum verisiyle
birebir aynı durum, bu yüzden aynı çözüm.

⚠️ Akışın kendisi birebir aynı kaydı tekrar gönderiyor (89C üç kez ölçüldü);
tekilleştirme şart.

### `duyurular.py` + `duyuru_dongusu.sh`

```
python3 duyurular.py          bir tur yoklar ve yazar
python3 duyurular.py --ozet   kotaya dokunmadan biriken veriyi gösterir
./duyuru_dongusu.sh           10 dakikada bir · saatte 6 istek
```

**`duyuru` tablosu:** `tarih · hat · tip · kalkis_yeri · kalkis_saati · kayit_saati ·
mesaj · ilk_gorulme · son_gorulme · gorulme_sayisi`

- Tekilleştirme `(tarih, hat, tip, kalkış saati, mesaj)` üzerinden, ama satır **ezilmiyor**:
  `ilk_gorulme`/`son_gorulme`/`gorulme_sayisi` tutuluyor. Böylece bir duyurunun akışta
  ne kadar durduğu **ölçülecek** — pencere genişliği tahmin edilmeyecek, veri söyleyecek.
- Ham `MESAJ` de saklanıyor: servis metnini değiştirirse veri kaybolmasın diye.
  Kalıp tutmazsa satır atılmıyor, kalkış alanları boş kalıyor.

### ⭐ Kota paylaşımı — kaydediciye dokunmadan

Her yoklama `yoklama` tablosuna yazılıyor. **kaydedici.py'nin bütçe sayacı zaten o
tablodan okuyor** (Bölüm 20 Hata 2'de öyle düzeltilmişti), dolayısıyla duyuru
harcamasını kendiliğinden görüp kendi hat sorgularını kısıyor. **İki süreç arasına
eşgüdüm kodu yazılmadı.** Şehir görüntüsü korunuyor (`HAT_SORGUSU_YEDEGI`).

> Hat sorgusundan kısmak ucuz: Bölüm 30'da geometrik eşlemenin aynı sürede servisin
> **14 katı** eşleme ürettiği ve kotadan hiç harcamadığı ölçülmüştü.

Kaydedici **yeniden başlatılmadı** — hareket süzgecinin karşılaştırma noktası korunsun diye.

`durum.sh` güncellendi: beş sürecin hepsini ve günlük duyuru sayacını gösteriyor.

### ⚠️ HENÜZ BİLİNMEYEN — dürüstlük payı

1. **Kapsama ölçülmedi.** Şehirde günde ~2.400 iptal oluyor (Bölüm 2.3, %4,6).
   Bu akış hepsini mi veriyor, bir kısmını mı? Cevabı **yarınki arşiv** söyleyecek:
   bugün toplananla 1 Eylül arşivi kıyaslanacak. `gunluk.py`'nin zaten yaptığı iş.
2. **`hayalet.py` henüz bu akışı kullanmıyor.** Hâlâ konumdan çıkarım yapıyor.
3. **Dizin eskimiş olabilir** — 130S, 14SB, 92S dizinde yok (dizin 26 Ağustos'ta çekildi).

---

## 48. ⭐⭐ DUYURU ÜRÜNE BAĞLANDI — motordan telefona (1 Eylül, 4. seans)

Bulmak yetmez; veri tabloda dururken yolcuya bir faydası yok. Aynı seansta
uçtan uca bağlandı: **duyuru → cevap motoru → API → iPhone ekranı.**

### ⚠️ ÖNCE ÇÖZÜLMESİ GEREKEN TUZAK — duyuru YÖN vermiyor

Duyuru `(hat, kalkış yeri, kalkış saati)` veriyor. Ama tarifede aynı saatte
**iki yönde birden** kalkış olabiliyor. Ölçüldü:

```
312 sefer iptali
  237  tarifede tek yöne uyuyor            → net
   65  İKİ YÖNE birden uyuyor (%21)        → belirsiz
   10  tarifede hiç yok
```

Yanlış yönü iptal işaretlemek, yolcuya yanlış söylemek demek — uygulamanın tek
kozu olan güveni yıkar (PROMPT Bölüm 8: *"yanlış alarm sessiz kalmaktan zararlı"*).

**Çözüm:** duyurudaki kalkış yerini o yönün **ilk durağıyla** eşleştir.
Türkçe harfler sadeleştiriliyor (duyuru `IGTOT` yazıyor, durak `İGTOT`).

```
belirsiz 65 vakanın  59'u çözüldü  (%91)
                      6'sı çözülemedi
TOPLAM: 296 / 312  (%94,9) belirli bir kalkışa bağlanabiliyor
```

⭐ Çözülemeyen 6'sı hattın ucundan değil **ara duraktan** kalkan kısa seferler
(`401` → HARAMİDERE, hattın ilk durağı değil). **Onlarda yön İDDİA EDİLMİYOR** —
uydurmak yerine belirsizlik olduğu gibi söyleniyor.

`duyurular.iptal_haritasi()` üç küme döndürüyor: `kesin` · `belirsiz` · `gunluk`.
Dakikada bir önbelleğe alınıyor (kurulum 0,08 sn).

### Bağlanan üç yer

| dosya | ne yapıyor |
|---|---|
| `durakta_ne_var.py` | tarife satırı yerine `⛔ 15:55 kalkışı YAPILMAYACAK — İETT duyurusu` |
| `arayuz_sunucu.py` | `kaynak:"iptal"`, `guven:"kesin"`, `varis:null` |
| `ios/.../DurakGorunumu.swift` | kırmızı satır + üst şeritte `İPTAL` |

**⭐ `varis` bilerek boş:** gelmeyecek otobüsün varış saati olmaz. Ama `dakika`
doluyor — **yalnızca sıralama için**, iptal uyarısı komşu varışların arasında
doğru yerinde görünsün diye.

**⭐ Kırmızı, turuncudan ayrı olmak zorunda:** turuncu "gecikti" demek, kırmızı
"hiç gelmeyecek". Aynı renk olsalar yolcu boşuna bekler. `Tema.kirmizi #C03B36`.

### Doğrulanmış ekran — ESENYURT YOLU, 15:19

```
üst şerit :  142ES 2 dk(yeşil) · 76D 2 dk · 144A İPTAL(kırmızı) · 142 gecikti(turuncu)

76D · BAHÇEŞEHİR
  🚌 0,69 km uzakta · 23 km/sa · araç D-128           2 dk
  🚌 0,85 km uzakta · 22 km/sa · araç M3104           2 dk
  ⊗  15:22 seferi yapılmayacak                      İPTAL
     İETT duyurusu · GÜMÜŞSUYU PERON kalkışlı
```

Xcode derlemesi temiz, simülatörde uçtan uca çalıştığı görüldü.

---

## 49. ⚠️ HIZ GERİLEMESİ — Bölüm 39'un kazanımı erimişti (1 Eylül)

Duyuruyu bağlarken fark edildi: durak sorgusu **1,85 sn** sürüyordu.
Bölüm 39'da 0,17 sn'ye indirilmişti.

**Sebep duyuru DEĞİL** — ölçüldü, duyuru açıkken *daha hızlı* (1,85 sn),
kapalıyken 3,11 sn; çünkü iptal edilen kalkışta pahalı varış hesabı atlanıyor.

### Profil

```
olculmus_sure     3,74 sn / 35 çağrı     ← SCAN sefer (978.821 satır)
hatta_atanmis_...  3,34 sn / 14 çağrı     (indeksli, alt sorgu maliyeti)
rota.yol_uzerinde  0,18 sn                ← geometri yine masum
```

`sefer` tablosu **arşiv biriktikçe** 978 bin satıra çıkmış ve `guzergah`
sütununda indeks yokmuş. Tek durak sorgusu bu tabloyu **35 kez baştan sona
tarıyordu.**

```
CREATE INDEX ix_sefer_guzergah ON sefer (guzergah, plan_saat)    -- 1,1 sn
```

```
                    ÖNCE      SONRA
Sefaköy (15 hat)   1,85 sn   0,150 sn
KATI ATIK (10 hat) 1,05 sn   0,098 sn
Vefa    (52 hat)   0,26 sn   0,023 sn
```

> **Ders:** Bölüm 39'da tam olarak bu hata `gecis` ve `tarife` tablolarında
> düzeltilmişti; `sefer` o zaman küçüktü, gözden kaçtı. **İndeks eksikliği veri
> büyüdükçe ortaya çıkıyor — bir kez temizlemek yetmiyor.** Boru hattı sürekli
> veri biriktirdiği için bu ölçüm periyodik tekrarlanmalı.

---

## 50. ⛔⛔ %50 SAPMA BULUNDU — canlı tahmin ilkel yöntemdeymiş (1 Eylül)

Mehmet "Otobüsüm Nerede"de aynı durakları açıp karşılaştırdı: **bizim verimizde
%50'ye varan sapma var.** Ölçüldü, sebep bulundu, düzeltildi.

### Ölçüm yöntemi — tarafsız

`gecis` tablosunda aracın durağa VARDIĞI an kayıtlı (gerçek). Δ dakika öncesine
dönülüp motorun o an ne diyeceği birebir hesaplandı ve gerçekle kıyaslandı.
Hiçbir modelin tahmini referans olarak kullanılmadı.

### Bulgu — sistematik kayma YOK, DAĞILIM bozuk

```
Δ dk   örnek   ortanca hata   |hata|   BAĞIL hata   ±3dk içinde
 5     1079       +0,6         1,8        %36          %69
10      987       +0,7         3,4        %34          %45
15      907       +0,7         5,5        %37          %30
```

Ortanca hata +0,7 dk — erken ya da geç söylemiyoruz. Sorun **yayılım**: bağıl hata
%35, 15 dakikalık tahminlerin yalnızca %30'u ±3 dk içinde. Mehmet'in gördüğü
%50 sapma bununla uyumlu.

### ⭐ KÖK SEBEP — parça modeli canlı dala hiç bağlanmamış

Canlı dal `kalan mesafe ÷ aracın anlık hızı` kullanıyordu. Bölüm 35'te kurulan
**saatli parça modeli** (bu hatta, bu saatte, bu iki durak arası gerçekte kaç dakika)
yalnızca **tarife** dalına bağlanmış, canlı dala bağlanmayı unutmuşuz.

> **Neden mesafe÷hız kötü:** aracın son 12 dakikada ölçülen hızı **arkasını** ölçüyor;
> önündeki yolun trafiğini bilmiyor. Parça modeli **önünü** biliyor.

Somut vakalar (Sefaköy, 15:34):

| hat | uzaklık | ölçülen hız | ESKİ | YENİ |
|---|---|---|---|---|
| 98 | 7,26 km | 5 km/sa | **87 dk** | **26 dk** |
| 76V | 6,57 km | 8 km/sa | **49 dk** | **17 dk** |
| 98AB | 8,28 km | 5 km/sa | **99 dk** | **33 dk** |

### `canli_varis_dk()` — yeni ortak fonksiyon

Aracın rota üzerindeki yerinden **henüz varmadığı ilk durak** bulunuyor
(`bisect`), oradan hedefe kadar saatli parça süreleri toplanıyor, aradaki kısmi
parça anlık hızla ekleniyor.

⚠️ **Yedek yol da çöküyordu:** parça modeli cevap veremeyince ham `kalan ÷ hız`
kullanılıyordu ve `89S`'de **11,44 km · 2 km/sa → 323 DAKİKA** çıktı (ekranda görüldü).
Otobüs 11 km boyunca 2 km/sa gitmez; o ölçüm bir kırmızı ışık.
**Çözüm — mesafeye göre harmanlama:** ilk 2 km anlık hızla, gerisi şehir ortalamasıyla.
İçinde bulunduğu trafik yakın yolu belirler, uzak yol normale döner.

### ⭐⭐ SONUÇ — motorun tamamı, uçtan uca ölçüldü

```
                ESKİ (ham mesafe÷hız)      YENİ (motor)
Δ dk   örnek   |hata|  ±3dk  en kötü      |hata|  ±3dk  en kötü
 5     1329     1,8    %69    124 dk       1,2    %86     48 dk
10     1234     3,4    %46    183 dk       1,5    %76     50 dk
15     1144     5,3    %32    181 dk       1,9    %66     51 dk
```

**En kötü vaka 181 → 51 dakika.** Vakaların %92'si parça modelinden, %8'i harmanlanmış
yedek yoldan geliyor.

---

## 51. ⭐⭐⭐ GPS KAPALI OTOBÜS — ürünün asıl vaadi nihayet çalışıyor (1 Eylül)

PROMPT Bölüm 2'deki referans senaryo: *"98 · 23:30 · Sefaköy · ekranda hiçbir şey yok,
sefer iptal mi otobüs yolda mı?"* — **motor bunu hiç ele almıyormuş.**

### ⚠️ Bulunan kör nokta

`sonraki_kalkislar()` yalnızca **`saat >= şimdi`** olan kalkışları getiriyordu.
Yani 20 dakika önce kalkmış, yolda olan ama GPS'i susmuş otobüs **hiç hesaba
katılmıyordu.** Sefaköy'de 15:35'te ölçüldü: üç sefer yoldaydı (varış 16, 19, 36 dk
sonra) ve uygulama hiçbirini göstermiyordu.

```
89 → KANUNİ SULTAN SÜLEYMAN
  ÖNCE   ⏱ sıradaki otobüs 94 dakika sonra
  SONRA  📡 15:00 kalkışı · konum bildirmiyor → tahmini 17 dakika
```

### `yoldaki_gorunmeyenler()` — sayarak, tek tek atayarak değil

1. Bu durağa kalkıştan kaç dakikada gelindiği parça modelinden alınır.
2. O kadar geriye bakılıp, varışı **hâlâ gelecekte** olan kalkışlar bulunur (yolda).
3. **İptali duyurulanlar çıkarılır** (Bölüm 47 akışı) — onlar gelmiyor.
4. Görünen araçların tahmini varışlarıyla **sıra bozulmadan** eşleştirilir.
5. Eşleşmeden kalanlar → GPS karanlığı.

⚠️ **Sık seferli hatta iddia yok:** aralık 12 dk'nın altındaysa hangi seferin
görünmediği ayırt edilemiyor — Bölüm 25'te ölçülmüştü, 500T'de yöntem çökmüştü.
Aynı koruma burada da geçerli.

### Arayüz — Mehmet'in düzeltmeleri

| istek | yapılan |
|---|---|
| **şeritte iptal/gecikme YAZMA** | şerit artık yalnızca süre gösteriyor; iptal ve gecikmiş satırları atlayıp ilk GERÇEK varışı seçiyor. Gösterilecek varış yoksa şerit hiç çizilmiyor (boş bant bozuk görünüyordu). |
| **iptali aşağıda kırmızı şeritle anlat** | kartın tepesinde `⊗ 15:28 SEFERİ İPTAL EDİLDİ` — turuncu gecikme şeridinin kırmızı kardeşi. İptal satırı listeden çıkarıldı, üç satırın üçü de gerçek varışlara kalıyor. |
| **GPS kapalı şeritte görünsün** | anten simgesi + mavi renk (yeşil DEĞİL — otobüsü görmüyoruz). Kartta: `15:40 kalkışı · konum bildirmiyor` / `yolda · 15:53 civarı · ölçülmüş sürelerden` |

### Bir de eski borç kapandı — tarife gürültüsü

`98S`'de 15 ve 17 dakikalık iki canlı otobüsün altında **"17:00 kalkışı · 115 dk"**
duruyordu (Bölüm 46 madde 2, iki kez gündeme gelip yapılmamıştı).
Kural: kaç gerçek varış (canlı/GPS kapalı) varsa tarife o kadar geri çekilir —
2+ gerçek varış varsa tarife hiç gösterilmiyor.

---

## 52. ⭐ MODEL SAAT BAŞI TAZELENİYOR — "her geçen gün daha iyi" artık gerçek (1 Eylül)

Mehmet'in tespiti: *"her geçen gün topladıgımız dataları toplayıp her saat aralıgında
a durağından b durağına ne kadar sürede gittiğini sürekli hesaplayıp baz al"*.

### ⚠️ Bulunan boşluk — zincirin son halkası donuktu

```
ham konum      dakikada 1   ✅ taze
geçiş çıkarımı 10 dk'da 1   ✅ taze
duyuru         10 dk'da 1   ✅ taze
SÜRE MODELİ    GÜNDE 1      ⛔ 24 saat donuk
```

Ölçüldü: 1 Eylül 15:50'de model hâlâ **31 Ağustos** verisiyle çalışıyordu.
O gün çıkarılmış **1.346.218 geçişin hiçbiri** tahmine girmiyordu.

> Veri akıyordu ama tahmin onu görmüyordu. "Her geçen gün daha sağlam" iddiası
> bu haliyle günde bir kez, sabah 09:00'da doğru oluyordu.

### `model_dongusu.sh`

Saat başı (12. dakikada, rutinlerle çakışmasın diye) `sure_modeli.py kur` çalışır.

```
maliyet: 2 dk 11 sn  ·  674 hat · 850.055 parça-saat  ·  saatin %3'ü
kotadan istek harcamıyor — tamamen yerel hesap
```

`kur()` zaten **kayan pencere** kullanıyordu (son N gün, şimdiden geriye), yani
çalıştırıldığı anda o günkü veriyi de alıyor. Eksik olan tek şey onu çalıştırmaktı.

**Model damgası eklendi:** `durum` tablosuna `sure_kurulum` ve `sure_veri_sonu`
yazılıyor, `durum.sh` gösteriyor. Bu damga olmadan modelin bayatladığı fark edilmiyordu.

```
süre modeli    : ✅ 15:57 kuruldu (1 dk önce) · veri 15:47'e kadar
```

### ⭐⭐ BÖLÜM 36'NIN BULGUSU TERSİNE DÖNDÜ — veri biriktikçe iyileşiyor

Sabah rutini altı pencereyi dün üzerinde deniyor:

```
 3 gün → ortanca hata 4,60 dk
 5 gün → ortanca hata 3,43 dk   ← seçildi
 7 / 10 / 14 gün → 3,43 dk  (aynı — elimizde toplam 6 günlük veri var)
```

**31 Ağustos'ta (Bölüm 36) 2 günlük pencere 3 günlüğü yeniyordu** — "daha çok veri
daha kötü" çıkmıştı. Şimdi tersi. Sebep: ilk günlerin (27 Ağustos) hat atamaları
geriye dönük üretilmişti ve %6 hata payı taşıyordu; o gürültü artık azınlıkta.

> **Mehmet'in varsayımı ölçülerek doğrulandı** ve mekanizma bunu kendisi seçiyor.
> ⚠️ 5-7-10-14 aynı çıkıyor çünkü 5 günlük pencere zaten tüm veriyi kapsıyor.
> Ayrım veri biriktikçe çıkacak; haftalık desen için en az 2-3 hafta gerekiyor.

### Arka planda çalışan altı süreç

| süreç | sıklık | ne yapar |
|---|---|---|
| `kaydedici.py` | dakikada 1 | 6.911 aracın konumu + geometrik hat tahmini |
| `gecis_dongusu.sh` | 10 dk | konumdan durak geçişi çıkarır |
| `duyuru_dongusu.sh` | 10 dk | sefer iptali duyuruları |
| `model_dongusu.sh` | **saat başı** | süre modelini tazeler ⭐ yeni |
| `sabah_rutini.sh` | 09:00 | arşiv + pencere ayarı + doğrulama |
| `arayuz_sunucu.py` | sürekli | iOS uygulamasının arka ucu |

`./durum.sh` altısını da gösteriyor.

---

## 53. ⭐⭐⭐ GPS KARANLIĞI DOĞRULANDI — ve ilk parça kusuru bulundu (1 Eylül)

Bölüm 51'de yazılan `yoldaki_gorunmeyenler()` hiç sınanmamıştı. İki soru ayrı ayrı
ölçüldü: **sefer gerçekten yapıldı mı** ve **tahmini varış saati tuttu mu.**

### Doğrulama altyapısı — `gps_izleyici.py`

⚠️ **Tahmin verildiği anda YAZILMAZSA sonradan doğrulanamaz** (`yoklama` tablosu
dersinin aynısı, Bölüm 7). İddialar artık `gps_tahmin` tablosuna kaydediliyor:
`gps_dongusu.sh` 10 dakikada bir tarıyor (775 hat · 12 saniye · kotadan istek yok),
`gunluk.py` 5/5 adımı ertesi sabah arşivle kıyaslıyor.

⭐ **`--gecmis` kipi:** konum, eşleme ve geçişler geriye dönük durduğu için geçmiş
bir günde o gün ne iddia edeceksek birebir üretilip AYNI GÜNÜN arşiviyle
kıyaslanabiliyor. Yarını beklemeye gerek kalmadı.

### ⚠️ İlk sürümde mantık hatası — sayma kuralı atlanmıştı

İlk tarama 347 iddia üretti ve içinde `522 · yolda 6 sefer · görünen 9 araç` gibi
saçmalıklar vardı: dokuz araç görünürken altı seferin hiçbiri karanlıkta olamaz.
Sebep, doğrudan sıra eşleştirmesi yapılması; kestirilen kalkış saatleri gürültülü
olunca tolerans içinde eşleşemeyip sefer boşta kalıyordu.

**Düzeltme (Bölüm 33 dersi):** adet SAYMAKLA bulunur (`yolda − görünen`),
sıra eşleştirmesi yalnızca HANGİLERİ olduğunu seçer. 347 → 76 iddia, mantık ihlali 0.

### ⭐⭐ SORU 1 — sefer gerçekten yapıldı mı? (31 Ağustos, 2.868 iddia)

```
2.765 iddia arşivde bulundu
  ✅ %95,2  sefer YAPILDI    → "otobüs geliyor" dedik, geldi
  ❌ %4,8   sefer yapılmadı  → boşuna beklettik
```

Tek başına bu sayı yanıltıcı olurdu. Asıl ölçü, temel oranla kıyas:

```
iddia ettiğimiz 236 hattın TÜM seferleri : %6,08 yapılmadı   ← temel oran
bizim "yolda" dediklerimiz               : %4,85 yapılmadı

                                            temelin 0,80 KATI
```

> ⭐ **GPS karanlığındaki sefer, ortalama bir seferden DAHA GÜVENİLİR.**
> "Görünmüyor" ile "iptal" ayrı olgular — Bölüm 34'te savunulan konum ölçüyle
> doğrulandı. Alt kırılımlarda ayırt edici sinyal yok (hat tamamen körken bile
> %4,1 yanlış — yani daha iyi), dolayısıyla bu özelliklerle daha ince ayrım
> yapılamaz. Yöntem olduğu haliyle doğru.

### ⛔⛔ SORU 2 — varış saati tuttu mu? İLK PARÇA KİRLİ ÇIKTI

Gerçek referans: **arşiv, seferi yapan aracın kapı numarasını veriyor.** O aracın
`gecis` tablosundaki gerçek durak geçişleri tahminin karşısına konuldu.

```
81.696 gerçek durak geçişi
  TOPLAM hata          ortanca +0,2 dk · |hata| 5,9 dk · ≤3dk %27
    yol süresi hatası  ortanca +1,2 dk · |hata| 5,8 dk
    kalkış gecikmesi   ortanca +0,5 dk · %91'i 3 dk içinde   ← SUÇLU DEĞİL
```

**Hata rota boyunca BÜYÜMÜYOR** — %0'da 5,6 dk, %90'da 6,2 dk. Birikmiyorsa
başta doğuyor demektir. Tek sefer adım adım izlendi:

```
50AT · plan 23:10 · gerçek kalkış 23:11
   durak  2 · gerçek +1,4 dk · model  8,7 dk · fark +7,3
   durak  3 · gerçek +3,3 dk · model 10,8 dk · fark +7,5
   durak 15 · gerçek +15,6 dk · model 22,9 dk · fark +7,3   ← hata hiç değişmiyor
```

### ⭐ KÖK SEBEP — peron beklemesi ilk parçaya yazılıyor

```
parça 1→2 : ortanca 4,77 dk     ← komşularının 4 KATI
parça 2→3 : ortanca 1,15 dk
parça 3→4 : ortanca 1,07 dk
hatların %79'unda ilk parça, komşularının 2 katından uzun
```

`gecis` tablosunda 1→2 geçişi yalnızca sefere ÇIKAN araçları içermiyor: peronda
bekleyen, tur arası dinlenen araçların geçişleri de aynı kovaya düşüyor.
Bölüm 16'da gözlenmişti (*"23:20 → 23:30 0,00 km'de duruyor — peronda BEKLİYOR"*)
ama modele yansıdığı fark edilmemişti.

### Düzeltme — ölçülerek seçilen harmanlama

Dört seçenek aynı vakalarda denendi; **hangi biçimi olduğu fark etmedi**
(p10 da geometrik hesap da 4,4), hepsi ortancayı yendi. Ağırlık ölçüyle seçildi:

```
ağırlık   |hata|   ≤3dk   sapma
 şu anki   5,9 dk   %27   +0,2
 0,15      4,2      %42   −2,8
 0,45      4,4      %38   −1,6   ← seçildi
 0,60      4,7      %36   −1,1
```

⚠️ **0,45 seçildi çünkü hatanın yönü de önemli:** kalan −1,6 dk sapma tahmini biraz
ERKEN yapıyor. Yolcu için güvenli yön bu — otobüsü kaçırmaktansa birkaç dakika
fazla beklemek yeğdir.

### Uçtan uca sonuç (motorun kendisiyle ölçüldü)

```
                   ÖNCE      SONRA
ortanca hata      +0,2 dk   −1,6 dk
|hata|             5,9 dk    4,4 dk
±3 dk içinde        %27       %39
±5 dk içinde        %44       %54
```

**Canlı araç tahmini etkilenmedi** (Δ=15'te 1,9 → 1,8 dk) — düzeltme yalnızca
1. duraktan başlayan hesaba giriyor.

⚠️ **Asıl çözüm veri düzeyinde:** `gecisler.py` peronda bekleyen aracı sefere
çıkmış saymamalı. Daha büyük bir iş; şimdilik model düzeyinde düzeltildi.

⚠️ Bu ölçümde bir kayırma var: süre modeli 31 Ağustos'u da içeriyor, yani modeli
o günü "görmüş" halde sınadık. Yarınki canlı doğrulama kayırmasız olacak.

---

## 54. ⚡ PİL BİTTİ — 2 saat 6 dakikalık kesinti (2 Eylül sabahı)

MacBook fişte bırakılmadı. Sistem günlüğü ve `yoklama` tablosu birebir örtüşüyor:

```
07:09:03   pil uyarısı seviye 2 · %10
07:46:18   pil uyarısı seviye 3 · %2 · "14 dakika ömür"
07:54:08   ⬅ KAYDEDİCİNİN SON KAYDI
07:54:34   "Entering Sleep state due to 'Low Power Sleep' · Batt %1"
09:56:32   "Wake from Hibernate · due to acattach · Using AC"   ⬅ fişe takıldı
10:00:08   ⬅ akış geri geldi (ilk uyanış isteği DNS hatası aldı, 180 sn susup toparladı)
```

**Gece boyunca sorun yoktu:** her saat 93-94 istek, %100 başarı, 01:00-07:00 kesintisiz.

⭐ **Süreçler ölmedi, dondu ve kaldıkları yerden devam etti** — Bölüm 31'de öngörülen
davranış doğrulandı. Beş döngünün beşi de elle müdahale olmadan geri geldi.
`yoklama` tablosu o iki saati "biz bakamadık" diye kaydediyor; analiz iptal sanmayacak.

⚠️ **Sabah rutini 09:00'da koşamadı** (makine uykudaydı), elle çalıştırıldı.
İlk denemede arşiv `HTTP 503` verdi — geçici sunucu hatası, tekrarda indi (52.596 kayıt).
**Ders:** `gunluk.py` arşiv adımında tekrar denemeli; şu an tek denemede pes ediyor.

---

## 55. ⭐⭐⭐ İKİ KAYIRMASIZ DOĞRULAMA — 1 Eylül sonuçları (2 Eylül)

Dün geriye dönük ölçülen sayılar kayırmalıydı (model o günü görmüştü). Bunlar gerçek.

### A) GPS KARANLIĞI — dünkünden de iyi

```
925 iddia · 894'ü arşivde bulundu
  ✅ %97,0  sefer GERÇEKTEN yapıldı
  ❌ % 3,0  yapılmamış

iddia ettiğimiz 185 hattın TÜM seferleri : %5,58 yapılmadı   ← temel oran
bizim "yolda, geliyor" dediklerimiz      : %3,02 yapılmadı

                                           temelin 0,54 KATI
```

> ⭐ GPS'i kapalı sefer, ortalama bir seferin **yarısı kadar** iptal riski taşıyor.
> Geriye dönük ölçümde 0,80 kat çıkmıştı; kayırmasız ölçümde 0,54. İddia sağlam.
> "Görünmüyor" ile "iptal" ayrı olgular — Bölüm 34'ün konumu iki kez doğrulandı.

### B) DUYURU AKIŞI — ve ⭐ GERİ ALMA BULGUSU

```
toplanan sefer iptali duyurusu : 1.328
arşivdeki gerçek iptal/yarım   : 2.424   (50.307 sefer içinde)

İSABET  : duyurulan 1.325'in 748'i gerçekten olmadı  →  %56,5
KAPSAMA : 2.424 gerçek iptalin 748'i duyurulmuştu    →  %30,9
```

Bölüm 33'te konumdan çıkarımla %13 isabette tıkanılmıştı; duyuru akışı **4,3 kat** iyi.
Ama %43,5 yanlış hâlâ yüksekti. Sebep arandı ve bulundu:

### ⭐⭐ AKIŞTAN DÜŞEN DUYURU = GERİ ALINMIŞ SEFER

Duyuru sabah 04:05'te giriliyor; sefer sonradan telafi edilirse akıştan **düşüyor**.
`duyuru` tablosunda `ilk_gorulme`/`son_gorulme`/`gorulme_sayisi` tutulduğu için
bu ölçülebildi:

```
duyurunun durumu          sayı    İSABET
kalkışa kadar durdu       1094    %66,0
12-45 dk önce düştü         77    %13,0   ← geri alınmış
45+ dk önce düştü          154    %10,4   ← geri alınmış

görülme sayısına göre:  1-3 kez %39,1 · 4-10 kez %50,7 · 11+ kez %75,1
```

> **Düşen duyuruya bakıp "iptal" demek, on vakanın dokuzunda yanlış.**
> 1. seansta "ilk_gorulme/son_gorulme'yi tut, pencereyi veri söylesin" diye
> konulan alanlar burada karşılığını verdi.

### Süzgeç seçenekleri — ölçülerek seçildi

```
süzgeçsiz (eski)           1325 iddia · isabet %56,5 · kapsama %30,9
kalkışa kadar durdu        1094 iddia · isabet %66,0 · kapsama %29,8  ← SEÇİLDİ
11+ kez görüldü             454 iddia · isabet %75,1 · kapsama %14,1
kalkışa kadar VE 6+ kez     697 iddia · isabet %70,6 · kapsama %20,3
```

İsabet **9,5 puan** artıyor, kapsamadan yalnızca **1,1 puan** gidiyor. Neredeyse bedava.
11+ kez süzgeci 9 puan daha verirdi ama kapsamanın yarısını götürüyor — alınmadı.

### Bulunan hata — `iptal_haritasi()` geri alınanları da kullanıyordu

Fonksiyon o günün **tüm** duyurularını okuyordu. `TAZELIK_DK = 25` eklendi:
yalnızca son 25 dakikada akışta görülen duyurular ürüne giriyor
(yoklama aralığının 2,5 katı — bir tur kaçsa ya da makine donsa yanlışlıkla
"geri alındı" sayılmasın).

```
bugün toplanan sefer duyurusu : 481
şu an akışta duran            : 231   ← ürüne giren
geri alınmış                  : 250   (yarısı!)
```

⚠️ Geçmiş gün sorgulanırsa (doğrulama) süzgeç uygulanmıyor — o gün akış zaten bitmiş.

### Nerede duruyoruz

```
iptal iddiası:  isabet %66 · kapsama %30
```

Hâlâ "kesin iptal" diye gösterilecek düzeyde değil (üç iddiadan biri yanlış),
ama Bölüm 33'ün %13'ünden beş kat iyi. **Ürün kararı gerekiyor:** iptal satırı
bu haliyle mi gösterilsin, yoksa 11+ kez süzgeciyle (isabet %75, kapsama %14) mi?

---

## 56. ⛔⛔ DİSK DOLDU, KAYDEDİCİ ÖLDÜ — ve indeksler suçlu çıktı (3 Eylül)

```
03:11   disk doldu · kaydedici "database or disk is full" almaya başladı
03:15   ⬅ KAYDEDİCİ ÖLDÜ
10:13   ⬅ yeniden başlatıldı
KAYIP: 7 saat konum verisi
```

Makine yeniden başlamadı (45 gündür açık), güncelleme kurulmadı, pil bitmedi.
**Sorun tamamen diskti.** Gece yalnızca küçük duyuru yazımları geçebildi.

### ⭐ KÖK SEBEP — indeksler veriden pahalı

```
filo_konum   veri 1,08 GB  +  3 indeks 2,20 GB  = 3,3 GB
gecis        veri 0,74 GB  +  5 indeks 3,33 GB  = 4,1 GB
```

İki indeks **tamamen ölü** çıktı:

| indeks | neden ölü | boyut |
|---|---|---|
| `ix_filo_arac (kapino, zaman)` | `UNIQUE (kapino, zaman)` kısıtı SQLite'ta **zaten aynı indeksi kuruyor** — tam kopya | **0,78 GB** |
| `ix_gecis_durak (durak_kodu, zaman)` | kodda `durak_kodu`'yu **tek başına** süzen hiçbir sorgu yok; durakta_ne_var, hayalet, sure_modeli hepsi `hat+yon` ile soruyor → `ix_gecis_durak_hat` karşılıyor | **0,59 GB** |

⚠️ **Sadece düşürmek yetmedi — kod onları geri kuruyordu.**
`kaydedici.veritabani_kur()` ve `gecisler.tablo_kur()` içindeki
`CREATE INDEX IF NOT EXISTS` satırları her açılışta yeniden yaratıyordu.
Nitekim `ix_gecis_durak` düşürüldükten 20 dakika sonra geri gelmişti.
İki `CREATE` satırı da koddan kaldırıldı.

Sorgu planları tek tek doğrulandı, hiçbiri taramaya düşmedi. Uygulama
**hızlandı**: Sefaköy 0,150 → **0,042 sn** (bakılacak indeks azaldı).

### ⚠️ İkinci sızıntı — WAL sınırsız büyüyordu

`kayit.db-wal` **770 MB**'a şişmişti: sürekli okuyucu olduğu için checkpoint
tamamlanamıyordu. Boşaltıldı (770 MB → 5 MB) ve kalıcı sınır kondu:
`PRAGMA journal_size_limit = 256 MB`.

### ⭐⭐ ASIL YAPISAL HATA — `gecis` HİÇ BUDANMIYORDU

`filo_konum` 10 günde budanıyordu ama `gecis` hiç. Günde **0,44 GB**
(veri + dört indeks) büyüyordu, sonsuza kadar.

**Ne kadar geriye gerek var — ölçüldü, tahmin edilmedi:**
```
sure_modeli.DENENEN_PENCERELER   en fazla 14 gün
durakta_ne_var.GOZLEM_GUN                 7 gün
pencere_ayarla (hedef gün + pencere)     15 gün
→ 21 günden eski ham geçiş bugün HİÇBİR sorguya girmiyor
```

`GECIS_SAKLAMA_GUN = 28` kondu (kaydedici `buda()` içinde, her gece 04:00).

⭐ **Neden 21 değil 28:** Mehmet'in hedefi *"her geçen gün daha iyi tahmin"*.
Sınırı ihtiyacın tam üstüne koymak o kapıyı kapatırdı — model daha uzun
geçmişin işe yarayıp yaramadığını **hiç sınayamazdı**. 28 gün saklama,
21 günlük pencerenin denenmesine izin veriyor.
Buna göre `DENENEN_PENCERELER`'e **21** eklendi.

> ⚠️ Silinen sayfalar dosyayı küçültmez (auto_vacuum kapalı) ama yeni veri
> onları **yeniden kullanır** — dosya büyümeyi durdurur. Amaç bu.

### Temizlik — Mehmet'in onayıyla

Yeniden üretilebilir geliştirici artıkları silindi: iOS DeviceSupport (4,5 GB),
DerivedData (1,1 GB), Spotify/Google/JetBrains/pip önbellekleri.
**Kazanç 13,2 GB.** Disk %99 → **15 GB boş**.

### Sonuç

```
disk        : 15 GB boş
veritabanı  : 1,37 GB yeniden kullanılabilir boş sayfa
gecis       : 28 günde budanacak (şu an 8 günlük veri var, silinecek yok)
WAL         : 256 MB ile sınırlı
uygulama    : 0,042 sn
```

---

## 57. ⭐⭐⭐ LAUNCHD — süreçler artık macOS'a emanet (3 Eylül)

### Neden

Üç günde ÜÇ ayrı sebeple veri kaybedildi ve üçünün de ortak kökü aynıydı:
süreçler `nohup ... &` ile elle başlatılıyordu, öldüklerinde kimse fark etmiyordu.

```
1 Eyl gece   pil bitti                → 2 sa  6 dk
2 Eyl öğlen  döngüler sessizce durdu  →     70 dk
3 Eyl gece   disk doldu, süreç öldü   → 7 sa
```

⚠️ Mehmet haklı olarak düzeltti: *"ben hep sana söylüyordum sen başlatıyordun."*
Sorun komut yazmak değildi — **sistem yalnızca biz konuşurken ayaktaydı.**
Bir kesinti ile bir sonraki konuşma arasındaki her dakika kayıptı.

### ⛔ İKİ BAŞARISIZ DENEME — ve gerçek sebep

**1. Boşluk tuzağı.** Proje klasörünün adında boşluk vardı ("mobil otobüsüm nerede").
`ProgramArguments` boşluktan bölününce yol üç parçaya ayrıldı → hepsi `çıkış 127`.

**2. Göreli yol.** `WorkingDirectory` spawn anında uygulanmıyor →
`can't open input file: gecis_dongusu.sh`. Çözüm: her servis
`/bin/zsh -c "cd '<proje>' && exec ..."` — tek parça komut, bölünecek şey yok.

**⭐ ASIL SEBEP — proje MASAÜSTÜ'ndeydi.** macOS Masaüstü'nü gizlilik için koruyor:

```
launchd servisi için:
   ev dizini (~)       okunabiliyor  ✅
   ~/Desktop içeriği   OKUNAMIYOR    ⛔   (stat serbest, open yasak)
```

Bu yüzden `zsh` betiği açamıyordu (127), `python3` de `.py` dosyasını (78).
**Kodda hiçbir hata yoktu, sırf konum yüzündendi.**

⚠️ Teşhis iki kez yanlış yola saptı: önce TCC'yi `ls` ile test ettim (yalnızca
`stat` yapar, izin verilir) ve "erişim var" sandım; sonra `~/.zshrc` okumayı
denedim ama o dosya zaten yoktu. **Doğru test `open`/`read` denemekti.**

### Çözüm — klasör taşındı

```
ESKİ  /Users/mehmetkucukbirer/Desktop/mobil otobüsüm nerede
YENİ  /Users/mehmetkucukbirer/otobus-takip
```

Masaüstü'ne **sembolik bağ** bırakıldı: klasör Finder'da hâlâ görünüyor ve eski
yolu kullanan her şey çalışmaya devam ediyor. Aynı diskte olduğu için taşıma anlık.
Kodda gömülü **10 yol** güncellendi (9 dosya).

⚠️ `mv` komutu güvenlik süzgecine takıldığı için Mehmet elle çalıştırdı.

### `launchd_kur.sh` — yedi servis

| servis | ne yapar | tetik |
|---|---|---|
| `otobus.kaydedici` | caffeinate + kaydedici.py | RunAtLoad + KeepAlive |
| `otobus.gecis` · `duyuru` · `model` · `gps` | döngüler | RunAtLoad + KeepAlive |
| `otobus.arayuz` | iOS arka ucu | RunAtLoad + KeepAlive |
| `otobus.sabah` | `gunluk.py` | **StartCalendarInterval 09:00** |

```
./launchd_kur.sh          kur ve başlat
./launchd_kur.sh durum    ne çalışıyor
./launchd_kur.sh durdur   hepsini kaldır
```

⭐ **Sabah rutini ayrıca kazandı:** `while` döngüsü yerine takvim işi. 3 Eylül
09:00'da makine uykudaydı ve rutin HİÇ çalışmadı; launchd kaçırılan takvim işini
makine uyanınca çalıştırır.

### Doğrulama — iddia değil, ölçüm

```
altı servis de PID aldı, son-çıkış 0
akış normal, kayıtlar geliyor

KeepAlive sınavı:
   kaydedici öldürüldü (PID 43499)
   launchd geri getirdi (PID 43513)  ✅
```

---

## 58. ⭐ DİSK GÖZCÜSÜ — sistem kendini kurtarıyor (3 Eylül)

### Neden launchd yetmedi

launchd ölen süreci geri getiriyor (Bölüm 57). Ama **disk doluysa geri gelen
süreç de yazamaz** — aynı hatayla yine ölür, launchd yine kaldırır, sonsuz döngü.
Bu sabahki senaryo tam olarak buydu; kaydedici günlüğe `database or disk is full`
yazdı ama **kimse bakmadığı için sabaha kadar öyle kaldı.**

> Ders: uyarı yazmak yetmiyor. Kimsenin bakmadığı bir uyarı, uyarı değildir.
> Kurtarma sürecin **içinde** olmalı.

### `disk_gozcusu()` — iki kademe

```
UYARI_GB = 5.0    altına inince günlüğe belirgin uyarı
ACIL_GB  = 3.0    altına inince ACİL BUDAMA
DISK_KONTROL_TUR = 10    (10 turda bir = 10 dakikada bir bakılır)
```

Acil budamada saklama süreleri **geçici olarak yarıya** iniyor:
`filo_konum` 10 → 5 gün, `gecis` 28 → 14 gün. Silinen yer `wal_checkpoint(TRUNCATE)`
ile diske geri veriliyor.

⭐ **Bilinçli takas:** eski veriyi kaybediyoruz ama sistem yaşıyor. Alternatifi
tüm akışın durması — bu sabah öyle oldu ve **7 saat** kaybettik. Eski konum verisi
zaten türetilmiş durumda (geçişler çıkarılmış); akan veri daha değerli.

⚠️ **Günde en fazla bir kez** acil budama yapılıyor. Disk hâlâ doluysa her turda
silmeye çalışıp elimizdeki veriyi eritmesin diye.

### Doğrulama — sahte veritabanıyla, gerçek veriye dokunmadan

```
1) disk 20 GB (bol)      → hiçbir şey yapılmadı            ✅
2) disk  4 GB (uyarı)    → uyarı yazıldı, silme yok        ✅
3) disk 1,5 GB (kritik)  → 100+100 eski satır silindi      ✅
4) aynı gün ikinci kez   → SİLMEDİ, uyarıyla geçti         ✅
```

---

## 59. ⛔⛔ ÜÇ KATMANLI ÇÖKÜŞ VE ONARIMI — 3 Eylül, tam gün

Bu bölüm bir günde çıkan **beş ayrı arızayı** kaydediyor. Hepsi birbirini
tetikledi; teker teker bakınca hiçbiri anlaşılmıyordu.

### Zincir

```
disk doldu → kaydedici öldü → 7 sa veri kaybı
   ↑
WAL 4,4 GB'a şişti  +  gecis hiç budanmıyordu  +  iki ölü indeks
                                    ↓
                         launchd'ye taşındı
                                    ↓
                    launchd'nin 256 dosya sınırı → sunucu çöktü
                                    ↓
                    "Sunucuya ulaşılamadı" (telefonda görünen)
```

### 1. Disk doldu, kaydedici öldü (7 saat kayıp)

```
03:11  disk doldu · "database or disk is full"
03:15  ⬅ KAYDEDİCİ ÖLDÜ
10:13  ⬅ elle yeniden başlatıldı
```
Günlüğe hata yazdı ama **kimse bakmadığı için sabaha kadar öyle kaldı.**

### 2. ⭐ İki ölü indeks — 1,37 GB

| indeks | neden ölü | boyut |
|---|---|---|
| `ix_filo_arac (kapino, zaman)` | `UNIQUE (kapino, zaman)` kısıtı SQLite'ta **zaten aynı indeksi kuruyor** | 0,78 GB |
| `ix_gecis_durak (durak_kodu, zaman)` | kodda `durak_kodu`'yu **tek başına** süzen hiçbir sorgu yok | 0,59 GB |

⚠️ Düşürmek yetmedi: `veritabani_kur()` ve `tablo_kur()` içindeki
`CREATE INDEX IF NOT EXISTS` satırları her açılışta geri kuruyordu.
`ix_gecis_durak` silindikten 20 dk sonra geri gelmişti. İki `CREATE` da kaldırıldı.

Yan kazanç: durak sorgusu **0,150 → 0,042 sn** (bakılacak indeks azaldı).

### 3. ⭐ `gecis` hiç budanmıyordu

`filo_konum` 10 günde budanıyordu, `gecis` hiç. Günde **0,44 GB**, sonsuza kadar.

Ne kadar geriye gerek var — **ölçüldü**:
```
sure_modeli.DENENEN_PENCERELER  en fazla 14 gün
durakta_ne_var.GOZLEM_GUN                7 gün
→ 21 günden eski ham geçiş hiçbir sorguya girmiyor
```
`GECIS_SAKLAMA_GUN = 28` kondu. ⭐ 21 değil 28: model daha uzun geçmişin işe
yarayıp yaramadığını **sınayabilsin** diye. `DENENEN_PENCERELER`'e 21 eklendi.

### 4. ⭐ WAL sınırsız büyüyordu — 4,4 GB

Sürekli okuyucu (döngüler + sunucu) olduğu için otomatik checkpoint
tamamlanamıyor, WAL sınırsız şişiyordu.

⚠️ **`journal_size_limit` BAĞLANTI BAŞINA ayarlanır, dosyada saklanmaz.**
2 Eylül'de elle ayarlanmıştı; o bağlantı kapanınca ayar da gitti. Artık
`veritabani_kur()` içinde, `wal_autocheckpoint` da 1000 → 400 sayfaya sıklaştırıldı.

Tam boşaltma için tüm servisler kısa süre durduruldu: **4,4 GB → 0**, disk 2,7 → 7,0 GB.

### 5. Disk gözcüsü — sistem kendini kurtarıyor

launchd ölen süreci geri getirir ama **disk doluysa geri gelen süreç de yazamaz.**
Kurtarma sürecin İÇİNDE olmalı:
```
UYARI_GB = 5.0   günlüğe uyarı
ACIL_GB  = 3.0   ACİL BUDAMA: saklama süreleri geçici yarıya iner
```
Sahte veritabanıyla dört senaryo sınandı (bol/uyarı/kritik/aynı gün ikinci kez) ✅

### ⭐⭐ 6. LAUNCHD — ve iki tuzağı

Üç günde üç kayıp (pil 2sa6dk · sessiz durma 70dk · disk 7sa), ortak kök:
süreçler elle başlatılıyordu.

**Tuzak A — Masaüstü okunamıyor.** launchd servisleri `~/Desktop` içeriğini
**okuyamıyor** (stat serbest, open yasak). Kodda hata yoktu, sırf konum yüzünden
`çıkış 127` / `78` alınıyordu.
→ Proje `~/otobus-takip`'e taşındı, Masaüstü'ne sembolik bağ bırakıldı.
   Kodda gömülü **10 yol** güncellendi.

**Tuzak B — 256 DOSYA SINIRI.** Ölçüldü:
```
giriş kabuğunda : 1.048.576 dosya
launchd altında :       256 dosya   ⛔
```
Sunucu her istekte bağlantı + rota dosyası + soket açıyor; 256'ya dayanınca
`OSError: [Errno 24] Too many open files` ile çöküyordu.
**Elle `nohup` ile başlatılırken hiç yaşanmadı — sorun launchd'ye geçince çıktı.**
→ plist'lere `SoftResourceLimits: NumberOfFiles 8192` eklendi (256 → 8192 doğrulandı).

### 7. Sunucunun üç ayrı çökme sebebi

| sebep | belirti | çözüm |
|---|---|---|
| 256 dosya sınırı | `Too many open files` | plist `SoftResourceLimits` |
| `BrokenPipeError` | telefon isteği iptal edince süreç ölüyordu | `_json`'da yutuluyor + `DayanikliSunucu.handle_error` |
| **ön ısıtma portu bloke ediyordu** | port hiç açılmıyor, "Sunucuya ulaşılamadı" | ısıtma arka plan iş parçacığına alındı |

⚠️ **Üçüncüsü benim kendi düzeltmemin yarattığı sorundu.** İlk açılış 34 sn
sürüyordu diye ön ısıtma ekledim; ısıtmayı portu açmadan ÖNCE yaptım ve ısıtma
bazen 135 sn sürdü — o boyunca port hiç açılmadı. **Çözmeye çalıştığım sorunun
daha kötüsünü yarattım.** Artık port hemen açılıyor, ısıtma paralel koşuyor.

Ön ısıtma kapsamı da genişletildi: 673 hattın parça önbelleği **1,4 sn**'de
doluyor (ölçüldü). Bunsuz her yeni durak ilk açılışta ~20 sn sürüyordu.

### Şu anki düzen

```
veri toplama       ⏸ DONDURULDU (Mehmet'in isteği — mentör sunumu için)
arayüz sunucusu    ✅ doğrudan çalışıyor (launchd DEĞİL) · 0,07–0,31 sn
veri               3 Eylül 14:22'ye kadar
veritabanları      ✅ ikisi de quick_check temiz
disk               7,0 GB boş
```

⚠️ **launchd altında sunucu hâlâ kararsız.** Dosya sınırı düzeltildi ama sorun
tam çözülmedi; şimdilik sunucu doğrudan çalıştırılıyor. Diğer altı servis
launchd'de kalabilir, sorun yalnızca arayüzde.

### Temizlik

13,2 GB geri kazanıldı (iOS DeviceSupport 4,5 · DerivedData 1,1 · Spotify 2,8 ·
Google 2,3 · JetBrains 0,8 · pip/python 0,4). Hepsi yeniden üretilebilir önbellek;
Mehmet'in onayıyla silindi.

---

## 60. ⭐⭐⭐ ARTIMLI MİMARİ — ham veriyi sakla-işle-at (3-4 Eylül)

### Mehmet'in fikri

> *"geçmiş verilerden veri elde ettiğimiz zaman geçmiş verileri silsek, o değerin
> üstüne yeni verileri ekleyip bir hesaplama yapsak nasıl olur"*

Doğru fikir ve tam olarak akış işleme mimarisi. O ana kadar tersi yapılıyordu:
`sure_modeli.kur()` her saat ham `gecis` tablosundan **sıfırdan** hesap yapıyordu,
bu yüzden ham veriyi tutmak zorundaydık. Ham veri günde 0,44 GB büyüyor ve
3 Eylül'de diski doldurup sistemi 7 saat öldürdü (Bölüm 59).

### ⭐ Ham veride ne kadar tekrar var — ölçüldü

```
ham gecis          15.011.980 satır · 3,58 GB (veri + 4 indeks)
içindeki bilgi     12.908.870 süre değeri · 2.130.074 kovada
```

Bilgi ham veriden çok daha kompakt: her satır bir geçiş, ama **model için değerli
olan iki ardışık geçiş arasındaki SÜRE.**

### Depolama seçenekleri — 60.000 gerçek kovayla ölçüldü

```
A · gözlem başına ayrı satır + indeks    405 bayt/kova
B · kova başına 1 satır · BLOB paketli    43 bayt/kova   ← 9,4 kat küçük
```

**B seçildi.** Her gözlem BLOB içinde **4 bayt**:
```
2 bayt  süre, desisaniye   (parça sınırı 25 dk = 15.000 ds · uint16'ya sığar)
2 bayt  gün numarası       (2026 başlangıçlı · 2079'a kadar yeter)
```

⚠️ **Gün numarası neden tutuluyor:** `pencere_ayarla()` "kaç günlük geçmiş en iyi
tahmini veriyor" diye ölçüyor (2/3/5/7/10/14/21 gün). Gözlemin tarihi olmasa o
mekanizma çalışmaz ve *"her geçen gün daha iyi"* iddiası çökerdi.
**Havuz, mevcut pencere mantığını bozmuyor — aynı mantığı ham veri olmadan sürdürüyor.**

### Paketleme doğrulaması

2.000 rastgele kovada gidiş-dönüş testi yapıldı: **hepsi doğru.**
En büyük çözünürlük kaybı **0,04 saniye** — ham verinin zaman damgası zaten saniye
çözünürlüğünde olduğu için bu ölçüm hassasiyetinin altında. **Kayıpsız sayılır.**

```
  9 gözlem →  36 bayt BLOB
 60 gözlem → 240 bayt
120 gözlem → 480 bayt   (kova sınırı)
```

### ⚠️ Kova sınırı — kayan pencere, kayıp değil

Kova başına en fazla **120 gözlem**; taşınca en eskiler atılıyor.
Bu bir kayıp değil, zaten var olan tasarım: model hâlihazırda 3-5 günlük pencere
kullanıyor, eski gözlemler şu an da hesaba girmiyor.
Ölçüldü: kovaların %99'unda 20'den az gözlem var, en kalabalık kovada 277.
Sınır sayesinde havuz boyutu **üst sınıra bağlanıyor** — sonsuz büyümüyor.

### `parca_havuz.py` — artımlı besleme

```
python3 parca_havuz.py doldur      ham gecis'ten artımlı besle
python3 parca_havuz.py ozet        havuzun durumu
```

⚠️ **Artımlı ve mükerrer-korumalı:** işlenen son an `durum.havuz_islenen`'de tutuluyor.
Sınırda kalan parçayı kaçırmamak için okuma penceresi `MAX_PARCA_DK + 5` dakika
geriye taşıyor; aynı `(süre, gün)` çifti ikinci kez eklenmiyor.

İlk dolum (9 günlük tüm geçmiş): **13.272.891 gözlem · 2.130.074 kova**
İkinci çalıştırma (artımlı): **+735.484 gözlem · 326.430 kova** ✅ mekanizma çalışıyor

### ⭐⭐ SONUÇ — 33 KAT KÜÇÜLME

```
ham gecis (veri + 4 indeks)    3,58 GB
parca_havuz (aynı bilgi)       0,11 GB
```

### ⭐ KAYIPSIZLIK DOĞRULAMASI

`sure_modeli.kur()` havuzdan besleyecek şekilde yeniden yazıldı. Eski model
(ham veriden) yedeklenip yenisiyle karşılaştırıldı:

```
ortak kova                        319.528
birebir aynı (<0,02 dk = 1,2 sn)  295.946   %92,6
ortanca fark                      0,0000 dk (0,00 saniye)
0,5 dk'dan büyük fark                 873   %0,27
```

**Ortanca fark tam sıfır.** Kalan farklar algoritmadan değil, iki kurulum arasında
geçen sürede havuza yeni veri eklenmesinden — yeni model 371.865 kova kapsıyor,
eskisi 321.196.

---

## 61. ~~🔜 SIRADAKİ İŞ~~ — 4 ve 7 Eylül'de büyük kısmı kapandı

> ⚠️ **Bu liste artık geçmiş.** Güncel iş listesi **Bölüm 64**'te.
> Aşağıdaki maddelerin durumu:
> **1 ✅** (Bölüm 63.5 · 28→14) · **2 ⏳** (hâlâ duruyor, Bölüm 64 madde 2) ·
> **3 ✅** (Bölüm 62.2) · **4 ⏳** (Bölüm 64 madde 3) · **5 ⏳** (Bölüm 64 madde 4) ·
> **6 ✅** kök sebep çözüldü (Bölüm 62.5), launchd'ye geri konması Bölüm 64 madde 6 ·
> **7** uygulama ikonu ✅ (Bölüm 62.4), gerisi Bölüm 64 madde 7

**1. ⚠️ HAM `gecis` BUDAMASINI DEVREYE AL.** Havuz kuruldu ve doğrulandı ama
`GECIS_SAKLAMA_GUN` hâlâ 28. Süre modeli artık ham veriye ihtiyaç duymuyor;
`gecis`i kullanan diğerleri (gözlem katmanı, hayalet, gps_izleyici, doğrulama)
yalnızca son 7 güne bakıyor. **8 güne indirilebilir** → ~2,4 GB kazanç.
Ölçülüp indirilmeli.

**2. `parca_sure_ESKI` yedek tablosu silinmeli** — doğrulama bitti, yer kaplıyor.

**3. Havuz beslemesini döngüye bağla.** Şu an elle çalıştırılıyor;
`model_dongusu.sh` içinde `sure_modeli.py kur`'dan ÖNCE çalışmalı.

**4. Peron beklemesini veri düzeyinde ayıkla** (Bölüm 53) — varış tahminindeki
−1,6 dk sapma bundan.

**5. `hayalet.py` hâlâ duyuruyu kullanmıyor** (Bölüm 55, isabet %66).

**6. launchd + arayüz sunucusu.** Beş servis launchd'de sorunsuz; arayüz
`-10 (SIGBUS)` ile çöküyor, doğrudan çalıştırılıyor. `ProcessType: Interactive`
ve dosya sınırı eklendi ama sorun çözülmedi.

**7. Devam eden borçlar:** dizin eskimiş (130S, 14SB, 92S) · gerçek telefonda
saha denemesi · uygulama ikonu · gün tipi mi gün gün mü sorusu.

---

## 62. ⭐⭐⭐ UYGULAMA GERÇEK BİR ÜRÜNE DÖNDÜ (4 Eylül, 5. seans)

Bir günde iki cephe: arka uçta Bölüm 61'in borçları, ön yüzde uygulamanın kendisi.

### 62.1. ⭐ Pencere ayarlayıcı havuza taşındı — B, A'dan koptu

Bölüm 61 madde 1 (`gecis` budaması) bir ön koşula takılıydı: `sure_modeli.kur()`
havuzdan besleniyordu ama **`pencere_ayarla()` hâlâ ham `gecis`ten okuyordu** ve
`DENENEN_PENCERELER` 21 güne kadar gidiyordu. Yani ham veriyi kısaltmak,
"21 günlük geçmiş daha mı iyi?" sorusunu sormayı imkânsız kılardı.

Ortada iki ayrı gün sayısı olduğu netleşti:

| | ne | o günkü değer |
|---|---|---|
| **A** | `GECIS_SAKLAMA_GUN` — ham veri kaç gün **tutulur** | 28 |
| **B** | `sure_pencere` — model kaç günlük geçmişle **kurulur** | 3 |

`pencere_ayarla()`'nın model kurma kısmı havuza taşındı; cevap anahtarı (hedef
günün gerçek seferleri) ham veride kaldı — havuzda araç kimliği yok, sefer
eşleştirilemez.

**Kayıpsızlık doğrulaması** — aynı gün, iki kaynak:

```
pencere    ham (eski)   havuz (yeni)   fark
  2 gün      3,05 dk      3,07 dk     +0,02
  3 gün      3,05         3,05         0,00   ← ikisinde de kazanan
  5 gün      3,05         3,05         0,00
  7 gün      3,23         3,25        +0,02
 10/14/21    3,26         3,29        +0,03
```

Aynı 1.712 tahmin, aynı kazanan, en büyük sapma **1,8 saniye** — ölçüm
hassasiyetinin altında. Kaynağı: havuz aynı `(süre, gün)` çiftini iki kez
saklamıyor (artımlı beslemenin mükerrer koruması).

Yan kazanç: **179 sn → 39 sn** (7 pencere × 25 hat = 175 tam tarama yerine
50 havuz okuması).

⚠️ **Kova sınırı yanlılığı ölçüldü, ihmal edilebilir:** havuzda kova başına en
fazla 120 gözlem var. Sınıra dayanan 4.023 kova (tümünün **%0,19**) ve yarısı
yalnızca son 5 günü kapsıyor. Ama o kovalar zaten 120 gözlemle doymuş; uzun
pencerenin katacağı bir şey yok. Farkı seyrek kovalar yaratıyor (havuzun %93'ü,
1–19 gözlem) ve orada sınır hiç devreye girmiyor.

### 62.2. Havuz beslemesi döngüye bağlandı (Bölüm 61 madde 3)

`model_dongusu.sh` artık her saat şu sırayla çalışıyor:

```
parca_havuz.py doldur --sessiz   →   sure_modeli.py kur
```

⚠️ **Sıra zorunlu:** model havuzdan besleniyor, havuz elle dolduruluyordu. Yani
"saat başı tazeleme" fiilen *"en son elle çalıştırdığım ana kadar tazeleme"*
demekti.

⚠️ **İki adım AYRI bekçiyle:** besleme çökerse model yine kurulsun — eski havuzla
kurulan model, hiç kurulmayandan iyidir. Bekçi deseni bir kabuk fonksiyonuna
alındı (`bekcili`), test edildi.

⚠️ `--sessiz` kipi TEK SATIR özet bırakıyor, tamamen susmuyor: sessizce çalışan
bir adım çöktüğünde fark edilmez — 3 Eylül'de kaydedici tam böyle ölmüştü.

Ölçüldü: besleme 83 sn (2 saatlik veri) · kurulum ~131 sn. Doğrulandı — 12:12'den
itibaren her saat: `+65.401`, `+80.345`, `+78.810`, `+73.075` gözlem.

### 62.3. ⭐⭐ AYNI ADLI DURAKLAR AYRILDI — "hangi yön?"

Mehmet'in tespiti: *"durakları yazıyoruz ama hangi durak hangi yönde anlaşılmıyor,
sefaköy bir sürü durak var ama hangi yönde belli değil"*.

Arama "sefaköy" için dört ÖZDEŞ satır döndürüyordu — aynı ad, aynı ilçe, farklı kod.
Oysa **veri ayrımı zaten taşıyordu**:

```
122621 → hatların HEPSİ G yönünde (Bakırköy'e doğru)
122622 → hatların HEPSİ D yönünde (Beylikdüzü'ne doğru)
```

Durak kodunun son hanesi de bunu kodluyor (…1 / …2) ama "1" yolcuya bir şey
söylemez. Söyleyen tek şey hattın **nereye gittiği**. `hat_durak.yon_adi` alanı
eklendi:

```
SEFAKÖY · Küçükçekmece · 18 hat  → KANUNİ SULTAN SÜLEYMAN YÖNÜ
SEFAKÖY · Bakırköy    ·  6 hat  → BAKIRKÖY YÖNÜ
SEFAKÖY · Bakırköy    ·  6 hat  → AVCILAR MRK.ÜNV.KMP. YÖNÜ   (metrobüs)
SEFAKÖY · Küçükçekmece ·  6 hat  → CEVİZLİBAĞ YÖNÜ            (metrobüs)
```

⚠️ `yon_adi` kaynak veride kirli — aynı hedef hem `"BAKIRKÖY "` hem `"BAKIRKÖY"`
geliyor. Temizlik SQL'de değil Python'da yapılıyor; `GROUP BY` onları ayrı sayardı.

⚠️ Özet **tek sorguyla** üretiliyor (durak başına ayrı sorgu değil) ve
`yakin_duraklar`'da kırpmadan SONRA çağrılıyor — 12 durak için, kutudaki
yüzlercesi için değil.

**Not:** İETT'nin kendi uygulaması da aynı ayrımı yapıyor ("HALKALI YOLU /
ATAKENT 2.ETAP YÖNÜ"). Yani çözüm doğrulanmış bir kalıp.

### 62.4. Giriş ekranı, arama sayfası, favoriler

Düzen İETT'nin kendi uygulamasından, renkler bizim temamızdan. Gerekçe Tema.swift'in
aynısı: İstanbullu o yerleşimi zaten biliyor.

⚠️ **Sahte buton yok.** Örnekte dört kısayol var (Değerlendir · Kare Kod ·
İstanbulkart · Canlı İzle) — bizde hiçbiri yok. Yerine gerçekten çalışan üç şey
kondu: Yakınımdaki Duraklar · Favori Duraklar · Durak Ara.

- **Arka plan:** gece Boğaziçi fotoğrafı, `saturation(0.5)` + mavi degrade +
  ince siyah kat. Amaç fotoğrafı göstermek değil, karakter vermek —
  okunabilirlik görselin önünde.
- **Favoriler:** `UserDefaults`, telefonda kalıyor, sunucuya gitmiyor. Çalışmayan
  bir kalp koymaktansa gerçekten çalıştırmak hem dürüst hem faydalı.
- **Uygulama amblemi** (Bölüm 61 madde 7 kapandı): mavi zemin · sarı konum
  işareti · beyaz otobüs. Pillow/Inkscape kurulu olmadığı için Xcode'un Swift'iyle
  CoreGraphics'ten çizildi, 1024×1024. Yeniden üretilebilir.

⚠️ **Bir SwiftUI tuzağı:** `Image(...).scaledToFill()` bir `ZStack`'in İÇİNE
konunca, 500×750 oranındaki fotoğraf ZStack'i 603pt'ye çıkardı; sonraki
`.frame(height: 292)` ORTADAN kırptı ve başlık ekran dışında kaldı. Fotoğraf
`.background` katmanına alınınca boyutu içerik belirledi.

### 62.5. ⛔⛔ SUNUCUNUN SESSİZCE ÖLMESİ — kök sebep bulundu

Mehmet: *"bu sunucu neden sürekli sessizce ölüyo, xampp gibi alternatif bir çözüm
yok mu"*. Cevap: macOS'taki karşılık zaten launchd ve zaten kullanılıyor. Sorun
altyapıda değil, kodda:

```
ThreadingHTTPServer  →  her istek ayrı iş parçacığında
        +
tek SQLite bağlantısı, tüm iş parçacıklarınca paylaşılıyor
        ↓
iki istek çakışınca aynı bağlantıda eşzamanlı execute()
        ↓
SQLite'ın dahili durumu bozuluyor  →  SIGBUS, sessizce
```

Kod, koruduğunu sanıyordu ama **kilit yalnızca bağlantıyı KURARKEN tutuluyordu**;
sorgularda değil. `check_same_thread=False` Python'un uyarısını susturur, veri
yarışını değil. Bölüm 61 madde 6'daki `-10 (SIGBUS)` tam olarak buydu — ve aynı
hata ÜÇ dosyada vardı (`arayuz_sunucu`, `durakta_ne_var`, `yon_tespit`).

Eski yorum thread-local'dan *"her seferinde yeniden kuruluyordu"* diye vazgeçmiş.
**ÖLÇÜLDÜ:** bağlantı açmak dizin.db'de **0,069 ms**, kayit.db'de **0,143 ms**.
Bir durak cevabı ~170 ms — yani kaçınılan maliyet binde bir. O binde bir için
sessiz çökme riski alınmış.

Düzeltme: iş parçacığı başına bağlantı. Doğrulama: **60 eşzamanlı istek**, sunucu
ayakta. Ertesi gün ölçüldü: **7 saat 56 dakika kesintisiz** çalışma.

### 62.6. Gezinme hatası — iki biçim bir yığında

Mehmet: *"durak adı yazıyorum tıklıyorum benden bir daha durak adı yazmamı istiyor,
geri tuşuna basınca bu sefer yazdığım durağın bilgilerine gidiyor"*.

Sebep: aynı `NavigationStack`'te iki farklı gezinme biçimi karışıyordu —
`navigationDestination(isPresented:)` (bayrak) ve `navigationDestination(for:)`
(değer). Yığına bir değer itilince bayrak tabanlı hedef yeniden değerlendiriliyor
ve arama ekranı SIFIRDAN kuruluyordu; asıl durak ekranı onun altına giriyordu.

⚠️ İlk denemede yalnızca çift `for:` tanımı kaldırıldı — **hata sürdü**. Kök
sebep biçim karışıklığıydı. Çözüm: tek biçim — `Rota` enum'u, tek `[Rota]` yığını,
kökte tek hedef.

### 62.7. Sunucu adresi: sabit IP → Bonjour adı

Uygulama "sunucu çalışmıyor" diyordu; sunucu gayet çalışıyordu. Bilgisayar fişten
çıkıp başka ağa bağlanınca IP `10.100.35.107` → `192.168.1.119` olmuştu.

Varsayılan adres `http://Mehmet-MacBook-Air-2.local:8790` yapıldı — mDNS adı, ağ
ve IP değişse de sabit. Eski sabit IP'yi bir kez otomatik temizleyen kontrol
eklendi, yoksa kayıtlı eski değer kalıcı olarak yanlış cevap verirdi.

### 62.8. İzleme araçlarına arayüz sunucusu eklendi

`durum.sh` ve `izle.sh` arayüz sunucusunu **hiç göstermiyordu** — sessizce ölen
şey tam da oydu. Eklenen satır süreç var mı diye değil, **cevap veriyor mu** diye
bakıyor: süreç ayakta kalıp cevap vermeyi bırakabilir.

---

## 63. ⭐⭐⭐ ÇIKARIM KAYBININ KÖKÜ VE BEKLEME METRİĞİ (7 Eylül, 6. seans)

### 63.1. ⛔⛔ Şüphe: "76 hattı 1 dk'da bir geçiyor"

Ekranda `76 · bu saatte ortalama 1 dk'da bir geçiyor · son geçiş 42 dk önce`
yazıyordu — kendi içinde çelişkili. Mehmet: *"uygulamada tüm her şey doğru bir
şekilde gösteriliyor mu test et"*.

**Önce hat atamasından şüphelenildi, atama temiz çıktı.** 76'ya atanan 591 aracın
servisteki gerçek kimliği:

```
76      500 araç (%84,6)  ← doğru
76D      73 araç (%12,4)
HT48     12 · 76O 2 · diğer 4
```

**Sonra veri kalitesi ölçüldü** ve asıl bulgu çıktı — günlük geçiş sayısı çöküyordu:

```
gün      geçiş(76/D)   araç   geçiş/araç
29 Ağu      1404        363      3,9
30 Ağu      1528        392      3,9
31 Ağu      1475        452      3,3
 1 Eyl       978        410      2,4   ← kırılma
 2 Eyl       590        281      2,1
 3 Eyl       385        250      1,5
 4 Eyl       355        224      1,6
```

### 63.2. ⭐ Kök sebep: artımlı çıkarım izi parçalıyor

En açıklayıcı ölçü **verim** — aynı ham veriden ne kadar geçiş çıkarılabildiği:

```
gün        filo_konum     gecis      verim    filo
28 Ağu      2.250.951   1.852.215    0,823   6.731
29 Ağu      2.894.745   2.279.453    0,787   6.869
30 Ağu      2.712.545   2.236.947    0,825   6.911
31 Ağu      3.002.676   2.349.763    0,783   6.902
 1 Eyl      3.625.846   2.074.349    0,572   6.911   ← kırılma
 2 Eyl      2.813.444   1.462.337    0,520   6.870
 3 Eyl      2.186.674     990.188    0,453   6.774
 4 Eyl      2.308.507   1.083.432    0,469   6.735
```

Üç şey birden görünüyor: **filo sabit** (araç kaybı yok) · **1 Eylül'de ham konum
EN YÜKSEK** ama geçiş düşük · **verim 0,80 → 0,50**.

Yani veri kaybolmuyor — **ham veri diskte duruyor ama çıkarım onu göremiyor.**

Kırılma günü 1 Eylül, Bölüm 40'ın günü: geçiş çıkarımı *günde bir tam tarama*dan
*10 dakikada bir artımlı*ya geçmişti. Bölüm 40 kaybın bir kısmını fark edip
**eşlemeyi** 4 saat geriye taşımış, ama **izi taşımamış**. İki kayıp doğdu:

**1. `MIN_IZ = 3` elemesi.** 10 dakikalık pencerede araç başına ortalama 3,6 konum
düşüyor, eşik 3. Ölçüldü:

```
pencere başına konum   pencere
  1 kayıt                 591   ⛔ eleniyor
  2 kayıt                  44   ⛔ eleniyor
  3–5 kayıt                54
  6+ kayıt               1077
→ pencerelerin %36'sı TAMAMEN eleniyor
```

Tam gün taramasında aracın izi tek parça olduğu için bu eşik hiç devreye
girmiyordu.

**2. Pencere sınırı.** `zaman > baslangic` yüzünden her pencerenin ilk adımı,
bir öncekinin son ölçümünü göremiyor. Günde 144 pencere = araç başına 144 kayıp adım.

Bölüm 40'ın kendi ölçümü de bunu söylüyordu ama sebep izde değil eşlemede aranmış:
`07:00 → 188.170 geçiş (tam gün)` · `09:00 → 49.842 (artımlı — dörtte biri)`.

### 63.3. ⭐⭐ Çözüm ve kontrollü doğrulama

`parca_havuz.py` aynı sorunu zaten çözmüştü — okuma penceresini geriye taşıyor.
Aynı desen `gecisler.py`'ye uygulandı: **`IZ_GERIYE_DK = 30`**.

Mükerrer riski yok: `INSERT OR IGNORE` + `UNIQUE (hat, yon, durak_kodu, kapino,
zaman)` üst üste binen pencereleri sessizce yutuyor.

**Kontrollü test** — aynı 10 dakikalık pencere, iki yöntem, 120 hat örneklemi:

```
YAMASIZ (iz = yalnız pencere)    2.971 geçiş · 511 araç işlendi · 226 elendi (%31)
YAMALI  (iz 30 dk geriye)       13.555 geçiş · 729 araç işlendi ·   8 elendi (%1)
```

**4,6 kat** artış — Bölüm 40'ın ölçtüğü orana (188K/49K ≈ 4 kat) birebir oturuyor.
Tur süresi 2 dk 19 sn (döngü 10 dk, bekçi sınırı 15 dk).

⚠️ **Verim rakamı henüz doğrulanmadı:** yama 14:25'te uygulandı, o saatin çoğu
yamasızdı ve sonraki saat dolmamıştı. Kontrollü test kesin kanıt veriyor; günlük
verimin 0,50'den ne kadar yükseldiği **bir sonraki seansta ölçülmeli.**

### 63.4. ⭐⭐ "X dk'da bir geçiyor" YANILTICIYDI — bekleme metriği

Mehmet: *"saat bazında bak, hangi hat saatlerinin verisi sağlamsa ona göre işlem yap"*.

Önce saatlik veri sağlamlığı ölçüldü — **sistem çoğu saat %85–100 uyanık**, en
zayıf 09:00 (%58). Gün bazlı normalleştirme de fark yaratmadı (1,08 → 1,11 dk).
Yani **veri sağlamdı; sorun metrikteydi.**

Ekrandaki sayı **ortanca aralık**tı. Ama otobüsler düzenli değil, **konvoy** halinde
geliyor (76'da: %25'lik dilim 0,5 dk · ortanca 1,1 · %90'lık dilim 3,8). Ve yolcu
durağa **rastgele** gelir; uzun boşluğa denk gelme olasılığı daha yüksektir, çünkü
boşluk daha uzun sürer. Kuyruk teorisinde **inceleme paradoksu**:

```
E[W] = E[X²] / (2·E[X])        X = ardışık geçiş aralıkları
```

Her aralık kendi uzunluğuyla ağırlıklanıyor. Ölçüldü (Sefaköy):

```
hat    ortanca (ekranda)   gerçek bekleme
76          1,1 dk             2,6 dk      ← 2,4 kat
89A        13,0               14,2
146        12,8               14,6
98         19,5               19,3
73H        21,8               17,6
```

Fark yalnızca **sık geçen hatlarda** büyük — orada da zaten en çok yanıltıyor.

```
eski:  "bu saatte ortalama 1 dk'da bir geçiyor"
yeni:  "ortalama 2 dk beklersin"
```

⚠️ `aralik_dk` **değişmedi** — "sıradaki geçiş" hesabı ona dayanıyor
(`aralik_dk - son_gecis_dk`). `bekleme_dk` ayrı bir alan. İkisi farklı sorular,
ikisi de gerekli.

⚠️ İlginç yan sonuç: çoğu hatta bekleme ortancadan **küçük** (89B: 23 → 15) —
düzenli bir hatta yolcu ortalama yarım aralık bekler. 76'da ise **büyük** (1 → 2),
çünkü konvoy. Formül ikisini de doğru yakalıyor.

### 63.5. `GECIS_SAKLAMA_GUN` 28 → 14 (Bölüm 61 madde 1 kapandı)

28'in gerekçesi, `pencere_ayarla()`'nın 21 günlük pencereyi sınayabilmesiydi.
O işlev 4 Eylül'de havuza taşındı (62.1) ve bağ koptu. Kalan tek gerçek kısıt:

```
durakta_ne_var.GOZLEM_GUN        7 gün   ← en uzunu
hayalet · gunluk · hat_analizi   1 gün
parca_havuz beslemesi           30 dakika
```

8 gün ihtiyacı tam karşılardı; **14 seçildi** — emniyet payı bırakıyor ve haftalık
desenleri elle incelemeye izin veriyor (Mehmet'in kararı).

⚠️ 63.3'teki yama üretimi 4,6 kat artırdığı için tablo daha hızlı büyüyecek:
`14 gün ≈ 7,7 GB` (28 olsaydı ≈ 15,4 GB). Disk 75 GB boş.

Veri o an 12 günlüktü, yani sınır **ileriye dönük** çalışacak — bugün hiçbir şey
silinmedi. Kaydedici yeni ayarla yeniden başlatıldı.

---

### 63.6. ⭐⭐ Yamanın doğrulaması — tuttu ama tavan başka yerde (8 Eylül)

Aynı saatler karşılaştırıldığında (5-7 Eylül yamasız vs 8 Eylül yamalı):

```
saat    yamasız   YAMALI    değişim
05:00    0,099    0,362    +264%
06:00    0,284    0,524     +85%
07:00    0,298    0,435     +46%
09:00    0,602    0,517     −14%
10:00    0,471    0,542     +15%
ORT      0,351    0,476     +36%
```

**Yama tuttu: +%36.** Ama 0,80'e ulaşmadı ve iki ölçüm bunun nedenini gösterdi:

**1. Geriye taşımayı artırmak işe yaramıyor — 15 dakikada doyuyor:**

```
geriye     geçiş   elenen araç
  0 dk      1889       104
 15 dk      4798         5
 30 dk      4807         4    ← şu anki ayar
 60 dk      4807         4
120 dk      4807         4
```

`IZ_GERIYE_DK = 30` doğru ayar; o yol sonuna kadar kullanılmış.

**2. Asıl kısıt ham verinin kendisinde.** Araç başına konum kaydı (06:00-22:00):
`1 Eyl 466 · 2 Eyl 364 · 3 Eyl 276 · 4 Eyl 400 · 5 Eyl 405 · 6 Eyl 344 · 7 Eyl 204`.
Ağustos'ta bu sayı ~750'ydi. İz seyreldikçe ondan çıkarılabilecek geçiş de azalıyor.

⚠️ **Yani 0,80 ulaşılabilir bir hedef değilmiş** — daha sık konum kaydının olduğu
bir dönemin oranıydı. `durum.sh` eşikleri (≥0,70 yeşil) bu ölçüme göre
gözden geçirilmeli, yoksa gösterge sürekli boş yere alarm verir ve zamanla kimse
bakmaz — ki bu tam olarak 1 Eylül'de yaşanan şeydi.

### 63.7. ⭐⭐⭐ KESİNTİLİ SAAT DİLİMLERİ ELENİYOR (8 Eylül)

Mehmet'in tespiti:

> *"verinin düzgün toplanmadığı günler, sadece düzgün toplanan saatler için işlem
> yapacaksın. 13.00-15.00 arası güzel veri toplanmış, işlem yaparsın; ama
> 17.00-23.00 kesik kesik toplanmışsa o zaman geçen günkü veri kalacak, bir günde
> o kadar çok fark olmaz."*

⚠️ **Kesinti veriyi yalnızca EKSİLTMİYOR, YANILTICI veri üretiyor.** 17:05'te bir
geçiş kaydedilip kaydedici susarsa ve 17:50'de yeniden kaydederse, sistem
"45 dakikada bir geçiyor" der. Gerçekte 5 dakikada bir geçiyordu — sadece kayıt
yoktu. Yani kesintili dilimler aralığı YUKARI çekip yolcuya "otobüs seyrek" diye
yanlış bilgi veriyordu.

**Kalite ölçüsü:** kaydedici uyanıkken dakikada bir tur atar → saatte 60 tur
beklenir. Bu ölçü otobüs sayısından bağımsız (gece de tur atılır, sadece hareketli
araç az olur). Eşik 45 tur = %75 kapsama.

Son 7 günün 192 gün-saat dilimi:
```
sağlam (≥45 tur)    138   %72
kısmi  (20-44)       16    %8
kesintili (<20)      38   %20   ← her beş dilimden biri kirli
```

⚠️ **İki ucun sağlam olması yetmiyor:** 16:00 ve 18:00 sağlam ama 17:00 kesintili
olabilir; o durumda 16:55 → 18:05 arası 70 dakikalık YAPAY bir aralık üretilir.
`_aralik_saglam()` iki geçiş arasındaki HER dilimi kontrol ediyor.

⚠️ `son_gecis_dk` süzme ÖNCESİNDEN alınıyor: "son geçiş ne zamandı" sorusunun
cevabı, o dilimin kalitesinden bağımsız olarak gerçek son gözlemdir.

**ÖLÇÜLEN ETKİ** (Sefaköy · beklenen bekleme süresi):
```
hat     süzgeçsiz   süzgeçli   değişim
76        2,5 dk     1,9 dk     −24%
89A      13,5       10,8        −20%
98       19,8       16,3        −17%
73H      19,5       17,5        −10%
89S      11,6       10,9         −7%
146      10,6       11,1         +4%
98AB     16,4       16,4          0%
```

Sistem "20 dakika beklersin" diyordu, gerçek 16 dakikaymış. Gözlem sayısı
429 → 343'e düştü ama eşiklerin (4 gözlem / 3 aralık) çok üstünde.

---

### 63.8. ⭐⭐⭐ SEFER BAZLI TAHMİN — ölçüldü, KAZANDI, henüz eklenmedi (8 Eylül)

Mehmet'in fikri:

> *"15 dk'da bir geçiyor gibisinden değil. Bugün 13:00'daki aracın GPS'i kapalı ama
> sefer saati görünüyor ve biz anlık canlı konumlarda bu otobüsü göremiyoruz.
> Yarın 13:00'da aynı hattın GPS'i açık olabilir — buradaki verileri toplayıp
> 'bu saatte GPS açıkken bu kadar dakikada geliyordu' demek."*

**İki yöntemin farkı:**

```
PARÇA MODELİ (şu anki)
kalkış ──2dk──▶ D2 ──1,5dk──▶ D3 ──2dk──▶ … ──▶ Sefaköy
       └────── 16 ayrı tahmini topla = 20 dk ──────┘
       ⚠️ 16 tahminin hatası BİRİKİYOR

SEFER BAZLI (Mehmet'in fikri)
geçmiş 7 günde 13:00'te kalkanlar Sefaköy'e kaç dakikada geldi?
   → 19, 21, 20, 22, 18 dk → ortanca 20 dk
   ✅ tek ölçüm, zincir yok
```

**Veri yeterli mi — ölçüldü (98/D · Sefaköy · son 7 gün):** 210 eşleşen sefer,
her kalkış saati için 4-24 gözlem. Ve saatlik desen çok belirgin:

```
06:00  14,3 dk    13:00  20,1 dk    18:00  41,5 dk   ← akşam zirvesi
10:00  17,0 dk    16:00  29,2 dk    23:00  14,6 dk
```

Sabah 14 dk, akşam 41 dk — **3 kat fark.**

**KAYIRMASIZ SINAV** — model önceki 6 günden kuruldu, DÜN üzerinde sınandı,
25 rastgele hat×durak, 140 tahmin:

```
                  ortalama    ortanca
SEFER BAZLI       6,9 dk      2,4 dk    ← Mehmet'in fikri
PARÇA MODELİ      7,7 dk      4,5 dk    ← şu anki sistem
```

**Ortanca hata neredeyse yarıya iniyor.** Hat bazında örnekler:
`141M 2,1 vs 7,9` · `MR11 0,9 vs 2,4` · `29Ş 6,5 vs 9,8`
(131YS, 336H, 78F'de parça modeli önde — her hatta üstün değil.)

Gözlem eşiğine göre de sınandı; **her eşikte sefer bazlı kazanıyor**, tek gözlemle bile:

```
eşik    tahmin   SEFER    PARÇA
1+       188     2,5 dk   3,0 dk
3+       181     2,6      2,9
6+       145     2,4      2,8
```

⚠️ **NEDEN İKİSİ DE GEREKLİ:** sefer bazlı yöntem, o durak için geçmiş kayıt yoksa
hiçbir şey söyleyemez. Parça modeli hattın genel verisinden yine tahmin üretir.
Önerilen kademe:

```
sefer bazlı veri var mı (≥3 gözlem)?
   ├─ EVET → onu kullan           (daha doğru)
   └─ HAYIR → parça modeline düş   (her zaman cevap verir)
```

⭐ **Yan fayda:** sefer bazlı tahmin YOLCUYA SÖYLENEBİLİR bir cümle üretiyor —
*"13:00 kalkışı buraya geçmişte 20 dakikada geldi (12 ölçüm)"*. Parça toplamı
açıklanamaz. PROMPT Bölüm 4.3'teki "açıklanabilir kural, kara kutu değil"
ilkesine uyuyor.

⚠️⚠️ **HENÜZ KODA EKLENMEDİ.** Ölçüm ve karar hazır; uygulama bir sonraki seansın işi.

### 63.9. ⚠️ "Otobüsüm Nerede" uygulamasını kırma önerisi — reddedildi

Mehmet'in mentörü, gerçek uygulamayı tersine mühendislikle çözüp proxy ile
oradan canlı veri çekmeyi önerdi. Üç sebeple yapılmadı:

1. **İhtiyaç yok.** Dakikada bir 6.911 aracın konumu zaten resmi açık uç noktadan
   çekiliyor. Canlı gösterimde eksik yok.
2. **Erişim kontrolünü atlatmak anlamına geliyor.** Uygulamanın gömülü anahtarını
   kullanmak, o anahtarın sahibi gibi davranmak demek; kota da onlardan yenir.
   Açık veri çekmekle kapalı bir istemcinin kimliğini kullanmak farklı şeyler.
3. **Kırılgan.** Uygulama güncellenince, anahtar dönünce ya da sertifika sabitleme
   eklenince çalışmaz.

⭐ **Ama işaret ettiği gerçek eksik doğru:** araç–hat eşleşmesi. Şu an geometriden
çıkarılıyor, %93,7 isabetli (Bölüm 30). Meşru yol henüz denenmedi — PROMPT
Bölüm 5.2'deki üç metot WSDL'de tanımlı ama hiç sınanmadı:
`GetPlanaUyum_json` · `GetSeferZayi_json` · `GetOtsPlanlananKm_json`

---

## 64. 🔜 SIRADAKİ İŞ — 9 Eylül itibarıyla

**1. ~~SEFER BAZLI TAHMİNİ KODA EKLE~~** ✅ Yapıldı — **Bölüm 65**.
Kapsama: Sefaköy 7/9, Halkalı Marmaray 8/8 tahmin sefer bazlı.
⏳ Kalan: bir hafta veri biriktikten sonra kayırmasız sınav TEKRARLANMALI —
ölçüm 140 tahminle yapılmıştı, canlı davranış doğrulanmadı.

**1b. ~~Yamanın verimini doğrula~~** ✅ Yapıldı (63.6): saat bazında +%36.
⚠️ Ama `durum.sh` göstergesi hâlâ ≥0,70 eşiğiyle her gün ⛔ yanıyor (9 Eylül'de
0,50). 63.6'da ölçüldü ki 0,80 ulaşılabilir değil — **eşikler gerçekçi değere
çekilmeli**, yoksa sürekli alarm veren gösterge görmezden gelinir (1 Eylül dersi).

**2. `parca_sure_ESKI` yedek tablosu silinmeli** — doğrulama bitti (eski Bölüm 61
madde 2, hâlâ duruyor).

**3. Peron beklemesini veri düzeyinde ayıkla** (Bölüm 53) — varış tahminindeki
−1,6 dk sapma bundan.

**4. `hayalet.py` hâlâ duyuruyu kullanmıyor** (Bölüm 55, isabet %66).

**5. Aykırı tahmin:** `HT20` için 3,54 km → 46 dakika (4,6 km/sa) ölçüldü;
diğer hepsi 11–25 km/sa bandında. Tek örnek, ama bakılmalı.

**6. Arayüz sunucusu launchd'ye geri konabilir.** SIGBUS'ın kök sebebi 62.5'te
çözüldü; `otobus.arayuz.plist` hiç kurulmamış durumda, tanım `launchd_kur.sh`'ta
duruyor.

**7. ⭐ Denenmemiş üç servis metodu** (PROMPT 5.2) — araç–hat eşleşmesini
geometrik tahminden (%93,7) kesin bilgiye çıkarabilir:
`GetPlanaUyum_json` · `GetSeferZayi_json` · `GetOtsPlanlananKm_json`
Bunlar WSDL'de tanımlı, resmi uç noktalar; hiçbiri sınanmadı (bkz. 63.9).

**8. Devam eden borçlar:** dizin eskimiş (130S, 14SB, 92S) · gerçek telefonda
saha denemesi · gün tipi mi gün gün mü sorusu · `filo_konum`'da sistem saatinden
ileri zaman damgaları (araçların kendi saati kullanılıyor olabilir).

---

## 65. ⭐⭐⭐ SEFER BAZLI TAHMİN DEVREDE (9 Eylül)

Bölüm 63.8'de ölçülüp kazandığı kanıtlanan yöntem koda eklendi:
`durakta_ne_var.sefer_bazli_varis()`.

### Nasıl çalışıyor

Aynı aracın (`kapino`) kalkış durağından geçişi ile hedef duraktan geçişi
eşleştiriliyor; aradaki fark o seferin gerçek süresi. Kalkış SAATİNE göre
kovalanıp ortanca alınıyor.

⚠️ **Tek SQL ile.** Ölçüm sırasında N+1 sorgu kullanılmıştı (her sefer için ayrı
sorgu) — istek başına yüzlerce sorgu demekti. JOIN'e çevrildi; iki mevcut indeks
bunu ucuzlatıyor: `ix_gecis_durak_hat` (kalkış tarafı) · `ix_gecis_arac` (varış).

Ölçülen maliyet: ilk çağrı **10-103 ms**, önbellekten **0,1-0,2 ms**
(30 dakikalık önbellek).

### ⚠️ Aykırı temizliği — tur atan araç sorunu

İlk denemede MR40 için aralık **30-179 dk** çıktı. Sebep: araç kalkış durağından
geçtikten sonra hedef duraktan İKİNCİ TURDA geçerse eşleşme o turu ölçüyor.
Kalkış geçişi kaçmışsa (GPS boşluğu) da aynı sonuç doğuyor.

Ortancanın 2,5 katından uzun süreler eleniyor. Sonuç: **30-35 dk** (19 gözlemden
16'sı kaldı).

### ⚠️ Güven yalnızca gözlem sayısına bakmıyor

İlk sürüm `n >= 6` diyordu. Ama 89S'te 6 ölçüm vardı ve aralık **17:18-18:59**
(1 sa 41 dk) çıktı — o hattın süresi gerçekten oynak. "Orta güven" demek yolcuyu
yanıltırdı (PROMPT Bölüm 2: *"asla emin olmadığı şeyi emin gibi söylemez"*).

**Yayılma eşiği ÖLÇÜLEREK kondu** (214 tahminlik örneklem):

```
yayılma = (üst - alt) / ortanca
   %25: 0,27   ORTANCA: 0,42   %75: 0,73   %90: 1,30
```

Eşik **0,8** (ortancanın iki katı) → tahminlerin ~%77'si "orta" güven alıyor,
oynak hatlar dışarıda kalıyor. Kural: `n >= 5 ve yayılma <= 0,8`.

Sonuç doğru ayrışıyor:
```
89A   17:37–17:41  (4 dk pencere)   → orta
MR50  18:05–18:24  (19 dk)          → orta
MR51  18:33–19:04  (31 dk)          → düşük
```

### Kademe

```
sefer bazlı veri var mı (≥3 gözlem)?
   ├─ EVET → onu kullan · alt/üst sınır da ÖLÇÜMDEN (p10-p90)
   └─ HAYIR → parça modeline düş · alt/üst uydurma yüzde payından (%12/%22)
```

⭐ Sefer bazlı yolda alt/üst sınır **ölçülmüş** değerler; parça modelinde ise
sabit bir yüzde payı. Bu yüzden sefer bazlı aralık daha dürüst.

**Kapsama** (9 Eylül ölçümü): Sefaköy 7/9 · Halkalı Marmaray 8/8 tarife tahmini
sefer bazlı üretiliyor. Kalanlar parça modeline düşüyor.

---

## 66. ⭐⭐ EKRAN YOLCU DİLİNE ÇEVRİLDİ (9 Eylül)

Mehmet'in tespiti: *"halkalı marmaray durağına tıklıyorum, durakları gösteren
listede hangi yöne gittiği falan gözükmüyor"*.

Uygulama baştan sona gezildi. Kök sorun: **ekran geliştirici için yazılmıştı.**
Alanlar doğruydu ama yolcunun sorusuna cevap vermiyordu.

| ekranda yazan | yolcu için anlamı | yapılan |
|---|---|---|
| `GÜMRÜK` | "yön" olduğu belli değil | `→ GÜMRÜK YÖNÜ` |
| `32/33. durak · rotanın %96'i` | hiçbir şey | ayrıntılı kipe |
| `araç A-1100 görünüyor` | araç kodu ilgilendirmiyor | `otobüs görünüyor` |
| `24 km/sa` | karar değiştirmiyor | ayrıntılı kipe |
| `0.0 km uzakta` | araç durakta ama sıfır yazıyor | `durakta` · `850 m uzakta` |
| `ortalama 28 dk beklersin` + altta `3 dk` | çelişkili görünüyor | bağlama göre değişiyor |

### ⚠️ Silmek yerine anahtara bağlandı — `Tercihler.swift`

Araç kodu, anlık hız ve durak sırası **geliştirirken gerekiyordu**: 4-8 Eylül
doğrulamalarında (Bölüm 62-63) tahminler bu alanlarla ham veriye karşı sınandı.
Ayarlar'a "Ayrıntılı gösterim" anahtarı kondu, **varsayılan kapalı** — uygulamayı
ilk açan yolcu sade ekranı görür.

### ⚠️ "Beklersin" cümlesi bağlama göre değişiyor

```
canlı araç YOKSA  → "ortalama 28 dk beklersin"        (tahmin)
canlı araç VARSA  → "bu hat ortalama 28 dk arayla geçer"  (bilgi)
```

İkisi çelişmiyordu — biri hattın istatistiği, diğeri şu an görünen araç — ama yan
yana okununca yolcu hangisine inanacağını bilemiyordu.

### ⚠️ Mesafe 50 metreye yuvarlanıyor

`847 m uzakta` demek GPS'in veremeyeceği bir kesinlik iddiasıdır; `850 m` dürüst.
150 m altı mesafe değil DURUM bildiriyor: `durakta`.

### Baştan sona test — hepsi çalışıyor

```
✅ giriş ekranı · arama (yön ile) · durak ekranı
✅ favoriler (kalp, kalıcı)
✅ yakınımdaki duraklar — konum Sefaköy'e ayarlanıp sınandı:
     SEFAKÖY · KANUNİ SULTAN SÜLEYMAN YÖNÜ    6 m
     SEFAKÖY · AVCILAR MRK.ÜNV.KMP. YÖNÜ     52 m
     SEFAKÖY · BAKIRKÖY YÖNÜ                 74 m
     SEFAKÖY · CEVİZLİBAĞ YÖNÜ               88 m
   → dört ayrı durak, hangisinin nereye gittiği net
✅ ayarlar (sunucu adresi + yeni anahtar)
✅ GPS'siz tahmin: "16:48 kalkışı · konum bildirmiyor · 17:05 civarı"
```

⚠️ Ayarlar'daki açıklama hâlâ IP'den bahsediyordu; Bonjour adresine göre
güncellendi (Bölüm 62.7).

---

## 67. ⭐⭐⭐ ARAÇ DETAYI VE TRAFİK İNDEKSİ (10 Eylül)

Mehmet: *"sefaköy ht20 otobüsü 10 dk'ya gelicek, üstüne tıklayınca anlık olarak
hangi duraktan nereye hareket ediyor onu göster + olarak ibb açık veri portalında
trafik durumu var onu da göster"*

### 67.1. Araç detayı — `/api/arac` + `AracGorunumu.swift`

Durak ekranındaki "5 dk" tek başına bir İDDİA. Bu ekran o iddiayı DAYANAĞIYLA
gösteriyor; yolcu tahmine kendi güvenini kurabiliyor:

```
Bu otobüs nerede?          otobüs M3021
   konumu az önce alındı
   şu an 42 km/sa ile gidiyor
   İstanbul trafiği: yoğun (49/100)

YOLU
 ● ÇOCUK SİTESİ          5 dk önce geçti   11:34
 ● ATAKÖY GEÇİT          4 dk önce geçti   11:35
 ● ŞİRİNEVLER            3 dk önce geçti   11:36
🚌 otobüs şu an burada
 ○ KÜLTÜR ÜNİVERSİTESİ                     0.1 km
 ○ FİDANLIK                                1.3 km
 ○ KÜÇÜKÇEKMECE ADALET SARAYI              1.9 km
 ● SEFAKÖY · senin durağın                 3.1 km
```

Veri kaynakları: `filo_konum` (son konum) · `gecis` (geçtiği duraklar, saatleriyle) ·
`rota.yol_uzerinde()` (rota üzerindeki ilerleme) · `rota.durak_mesafeleri()`
(önündeki duraklar). Hepsi zaten vardı, birleştirilmemişti.

⚠️ **Konumun YAŞI gösteriliyor** ("az önce" / "4 dk önce alındı"): 1 dakikalık
konumla 6 dakikalık konum aynı şey değil, yolcu bunu bilmeli.

⚠️ **Yalnızca CANLI satır tıklanabilir.** Tahmin satırında gösterilecek bir araç
yok; tıklanabilir yapmak boş söz vermek olurdu. Dokunulabilirlik `›` oku ile
belli ediliyor — yoksa kimse denemez.

### 67.2. ⚠️ Trafik indeksi — iki hafta boyunca ölçülüp unutulmuş

`TrafficIndex` 26 Ağustos'ta ölçülmüştü (PROMPT 4.4): trafik indeksi ile sefer
süresi arasında **Spearman 0,759 · p = 0,00002**. Anlamlı çıkmış, not edilmiş,
**koda hiç girmemişti.**

```
https://api.ibb.gov.tr/tkmservices/api/TrafficData/v1/TrafficIndex → {"Result":49}
```

⚠️⚠️ **AYNI UÇ NOKTA İKİ FARKLI BİÇİM DÖNDÜRÜYOR** — 10 Eylül'de bulundu:
```
curl ile      → {"Result":49}                        (JSON)
Python urllib → <ResponseTrafficIndex xmlns=...>     (XML)
```
İlk sürüm XML'i `json.loads`'a veriyordu; hata yutuluyor ve trafik ekranda
sessizce "—" görünüyordu. Çözüm: `Accept: application/json` başlığı + yine XML
gelirse `<Result>` etiketinden okuyan yedek.

⚠️ **Bu sayı TAHMİNE GİRMİYOR.** Şehir geneli tek değer (0-100), yol bazlı değil
— yol bazlı canlı trafik açık veride yok (Bölüm 6/4: TrafficDensity, RoadTraffic,
Announcement → 404). Tahmin zaten otobüslerin kendi ölçülmüş hızından geliyor ve
o çok daha doğrudan bir sinyal. Trafik çipi yalnızca BAĞLAM veriyor:
*"20 dakika normalden uzun mu?"* sorusunun cevabı.

Gösterildiği yerler: durak ekranı başlığında çip (hava durumunun yanında) ·
araç detayında satır. Eşikler: `<40 akıcı` · `40-64 yoğun` · `≥65 çok yoğun`.
5 dakikalık önbellek; servis ulaşılamazsa uygulama yine çalışıyor.

---

## 68. ⭐⭐ SEFER TABLOSU VE TARİH SEÇİCİ (10-11 Eylül)

Mehmet: *"tüm sefer saatleri gözükücek tamam mı tablo şeklinde hangileri çıktıysa
bittiyse başka bir renk yoldakiler başka renk gps kapalı olanlar başka renk"*
ve ardından *"geçmiş günlere de bakabileyim, tarih seçici ekle"*.

### 68.1. Tablo neden yalnız tarifeye dayanamıyor

Ölçüldü (10 Eylül): **98/D tarifesinde bu durak için gün boyu 6 kalkış var ama
16 araç geçti** (Bölüm 21'deki bozuk tarife). Yalnız tarifeyi listeleseydik
günün üçte ikisi ekranda hiç görünmezdi. Tablo İKİ KAYNAĞI birleştiriyor:
tarife satırları + tarifede karşılığı olmayan gerçek geçişler. Eşleştirme
penceresi `ESLESME_DK = 45` (kalkış saati ile durağa varış arasında yol süresi
var, pencere geniş tutuldu).

### 68.2. Beş durum

```
gecti      ✓ o saatte gerçekten araç geçti (gözlemlendi)
yolda      🚌 şu an canlı görünen araç
gps_yok    📡 tarifede var, saati geçmiş, araç hiç görünmedi  → HAYALET SEFER
bekleniyor ⏳ tarifede var, saati henüz gelmemiş
veri_yok   — o saatte BİZ kayıt yapamamışız (kaydedici uykuda/çökmüş)
```

⚠️⚠️ `veri_yok` ile `gps_yok` ayrımı kritik. Kaydedici o saatte çalışmıyorsa
otobüs geçmiş ama görülmemiş olabilir; ona "GPS yok" demek YANLIŞ ALARM olurdu
(PROMPT Bölüm 8). Kalite ölçüsü Bölüm 63.7'deki ile aynı: saatte ≥45 tur.

### 68.3. Tarih seçici ve ⛔ GÜN TİPİ HATASI (11 Eylül'de bulundu)

Geriye **14 gün** gidiliyor (`kaydedici.GECIS_SAKLAMA_GUN` ile aynı; daha
geriye gitmek boş tablo gösterirdi).

İlk sürümde tarife gün tipi `DNV.gun_tipi(an)` ile — yani **BUGÜNDEN** —
hesaplanıyordu. Tarih seçiciyle geçmişe bakılınca hep bugünün tarifesi
geliyordu. Ölçüm:

```
141M/D hafta içi (I) : 63 kalkış
141M/D cumartesi (C) : 60 kalkış
141M/D pazar     (P) : 60 kalkış
```

Cuma günü pazara bakınca 3 fazla satır çıkıyor ve bunlar **"GPS kapalı"
(hayalet sefer) diye işaretleniyordu** — o gün öyle bir sefer hiç
planlanmamışken. Ürünün asıl vaadi hayalet tespiti olduğu için bu en pahalı
hata türü. Düzeltme sonrası pazar: 63 → 60 satır, sahte alarm 16 → 13.

Ders: **seçilen güne ait her hesap o günün kendisinden yapılmalı**, "şimdi"den
değil.

### 68.4. "Yolda" satırı artık kendi tarife satırına oturuyor (11 Eylül)

Önce yoldaki araç tabloya AYRI bir satır olarak ekleniyordu ve o satırın saati
VARIŞ saatiydi. Sonuç: 09:30 seferi tabloda iki kez görünüyordu — bir kez
tarifeden "bekleniyor", bir kez varış saatinde "yolda". Sefer kimliği
(Bölüm 69) geldikten sonra aracın hangi kalkışa ait olduğu bilindiği için
yoldaki araç kendi tarife satırını işaretliyor.

Doğrulandı (11 Eylül, 89/D HALKALI YOLU): `3 geçti · 1 yolda · 7 bekleniyor ·
1 veri yok`, "10:35 · yolda · 1.1 km · 3 dk" satırı tarifedeki 10:35 kalkışının
üstünde.

---

## 69. ⭐⭐⭐ SEFER KİMLİĞİ — "bu hangi seferin otobüsü?" (11 Eylül)

Mehmet: *"tahmini yapılan seferin hangi saat dakikadaki otobüs olduğunu
öğreneyim"*.

### 69.1. Boşluk neredeydi

| satır türü | kalkış saati |
|---|---|
| tarife | ✅ vardı |
| gps_kapali | ✅ vardı |
| iptal | ✅ vardı |
| **canli** | ❌ **yoktu** |

İronik: EN ÇOK GÜVENDİĞİMİZ satır, hangi sefer olduğunu söylemeyen tek satırdı.

### 69.2. Üç kademe — `sefer_kimligi()` (arayuz_sunucu.py)

```
1. TARİFE  araç kalkış durağından geçti, saat tarifeye oturdu (±10 dk)
           → "09:30 seferi"
2. ÖLÇÜM   geçti ama tarife tutmadı (98 gibi bozuk tarifeler)
           → "09:34 kalkışlı · tarifede yok"
3. HESAP   kalkış hiç görülmedi → varış saatinden geriye hesap
           → "≈09:45 seferi · sefer saati tahmini"
4. hiçbiri tutmadı → ALAN BOŞ (uydurmuyoruz)
```

⚠️⚠️ **`SEFER_ESLESME_DK = 10` penceresi neden var** — ölçüldü (10 Eylül
verisi, kalkış durağı geçişi ile en yakın tarife kalkışı arasındaki fark):

```
141M/D → ortanca  +3 dk · %100'ü ±10 dk içinde
HT20/D → ortanca  +2 dk · %100'ü ±10 dk içinde
98/D   → ortanca +310 dk · %0'ı  ±10 dk içinde      ← tarifesi bozuk
```

Pencere olmasaydı "en yakın tarife" seçilir ve 98'de yolcuya **457 DAKİKA**
şaşan bir sefer saati gösterilirdi. Pencere, bozuk tarifeyi sessizce
reddetmeyi sağlıyor.

### 69.3. ⛔ HATA 1: eski turun kalkışı gösteriliyordu

İlk sürüm "kalkış durağından EN SON geçiş"i alıyordu. Ama araçlar gün içinde
defalarca tur atıyor ve kaydedici her turun kalkışını göremiyor. Ölçüldü
(11 Eylül 09:47):

```
15B/C-252  kalkış durağından yalnız 06:55'te geçmiş, 09:43'te hâlâ yolda
98/A-1847  "01:00 kalkışlı" görünüyordu — aradan 8 sa 43 dk geçmiş
320/C-480  "06:47" — 3 saat önce
```

Çözüm — **TUR KONTROLÜ**: kalkıştan bu yana geçen süre, o durağa kadar
ölçülmüş seyahat süresinin `TUR_TOLERANS = 1.8` katı + `TUR_PAY_DK = 25`
dakikasını aşarsa kalkış reddediliyor (ve 3. kademeye düşülüyor). Yolcuya üç
saat önce kalkmış bir seferin numarasını vermek, hiç vermemekten kötü.

### 69.4. ⛔ HATA 2: aynı sefer iki araca veriliyordu

89A'da arka arkaya gelen iki otobüsün ikisi de "09:45 seferi" çıktı. Geri
hesap kademesi yakın araçlarda aynı kalkışa düşebiliyor. Liste durağa
yakınlığa göre sıralı olduğundan **kalkışı ilk talep eden alıyor, sonraki
susuyor**.

### 69.5. 3. kademenin payı ölçüldü

Geri hesapla bulunan kalkış ile gerçek kalkış arasında: **ortanca +3,6 dk ·
%54'ü ±5 dk · %81'i ±10 dk**. Tarife kalkışları 10-20 dk aralıklı olduğu için
±10 dk'lık pencere beşte bir ihtimalle KOMŞU SEFERİ gösterirdi. Bu yüzden:
`HESAP_ESLESME_DK = 5` **ve** `HESAP_USTUNLUK = 2.0` — en yakın kalkış,
ikinciden belirgin yakın olmalı; iki kalkış arasında ortada kalan hesap
belirsizdir, susuluyor. (Aynı desen `hat_tahmini.tahmin_et`teki USTUNLUK.)

### 69.6. Ekranda nerede

Sefer saati üst şeritteki çipte **YAZMIYOR** — kısa bir denemede eklendi ama
şeridi kalabalık yaptı (Mehmet'in kararı, 11 Eylül). Çipin işi tek: "kaç
dakikaya gelecek". Saat şurada:

- durak kartındaki varış satırında: `10:32 kalkışlı · 800 m uzakta`
- canlı araç ekranının başlığında: `10:32 seferi · otobüs A-1846`
- tahmini konum ekranının başlığında: `10:35 seferi nerede?`

---

## 70. ⭐⭐⭐ GPS KAPALI SEFERİN TAHMİNİ KONUMU — BANT (11 Eylül)

Mehmet: *"tahmini yapılan aracın da konumu gösterilsin"*.

Canlı araçta konum ÖLÇÜLÜYOR (`arac_detay`). GPS kapalıyken araç görünmüyor;
elde yalnız kalkış saati ve ölçülmüş parça süreleri var. Kalkıştan bu yana
geçen süre ikili aramayla durak sırasına çevriliyor (`sefer_konumu()`).

### 70.1. ⚠️⚠️ İKİ SINIR ÖLÇÜLDÜ — ikisi de yolcuya söyleniyor

**Kapsama %34.** 1495 hat-yön çiftinin yalnız 503'ünde ölçülmüş parça süresi
var. 141M ve HT20'de HİÇ yok; 13, 89A, 15B, 522'de var. Veri yoksa ekran
"konum hesaplanamıyor" deyip **sebebini söylüyor**, uydurma konum göstermiyor.

**Sapma ortanca 4 durak.** Tahmin edilen sıra ile aracın gerçekten görüldüğü
sıra arasında (10 Eylül verisi, tek turluk gerçek izler):

```
89A  → ±1-2 durak   (iyi)
13   → ±4-6 durak
522  → sürekli +9 durak  (kötü)
örnek 10 · ortanca 4 durak · %40'ı ≤2 durak · en kötü 9
```

### 70.2. Bu yüzden TEK DURAK değil BANT

"Otobüs şu an ŞURADA" demek yolcuyu ortalama dört durak yanıltmak olurdu —
Mehmet'in kuralına ters (*yanlış alarm, sessiz kalmaktan daha zararlı*).
`KONUM_PAY_DURAK = 4` ile bant veriliyor ve **payın kendisi ekranda yazıyor**:

```
10:35 seferi nerede?
  ((•)) bu otobüs konum bildirmiyor

  Şu an tahminen bu aralıkta
  ZEYTİNBURNU  ↔  BAHÇELİEVLER
  ⏱ 10:35 kalkışından bu yana 10 dk geçti
  ⚠ ±4 durak pay var — otobüs görünmediği için konum ölçülmüyor,
    ölçülmüş sürelerden hesaplanıyor

BU ARALIKTAKİ DURAKLAR
  ● ZEYTİNBURNU
  ● ABDURRAHMAN NAFİZ GÜRMAN MAH.
  ● KOCATEPE                          en olası
  ...
  ● SEFAKÖY · senin durağın
```

Ayrıca `hedef_gecilmis_olabilir`: yolcunun durağı bandın gerisinde kaldıysa
"bu otobüs durağını geçmiş olabilir" uyarısı çıkıyor.

Yeni dosyalar: `sefer_konumu()` + `/api/sefer` · `SeferKonumGorunumu.swift` ·
`Rota.seferKonum` · `SeferKonumu`/`SeferDuragi` modelleri.

---

## 71. ⚠️⚠️ ŞİŞKİN GEÇİŞ SAYILARI — geometrik hat atamasının sınırı (11 Eylül)

Sefer tablosunda 76 hattı **dün 334 satır** gösterdi; 09:54, 09:55, 09:56,
09:57 diye dakika dakika. Bir hat dakikada bir geçmez.

### 71.1. Tanı

Kayıtlar **mükerrer değil** — 334 geçiş, 202 ayrı araç, en çok tekrar eden
araç 4 kez (makul tur aralıklarıyla). Sorun hat ATAMASINDA:

```
10 Eylül · hat başına ayrı araç sayısı
  76     250 araç        ← aykırı
  76D    245 araç        ← aykırı
  HT48    83 araç
  16D     73 araç
  251     47 araç
  ...normal hatlar 39-83 bandında
```

Kaynağa bakınca kesinleşti:

```
76 hattına atama kaynağı (10 Eylül)
  İETT servisi (kaynak='servis')  :   4 araç
  geometrik tahmin ('geometri')   : 238 araç
```

`hat_tahminleri()` (kaydedici.py) hareketli araçların hattını GEOMETRİDEN
çıkarıyor — kotaya dokunmadan boşluğu doldurmak için. Kodda "%6,3 yanlış atama
payı" notu var ve ölçüm bunu doğruluyor: **336 hattan 21'i etkilenmiş = %6**.
Ama bu %6 en yoğun koridorlarda toplanıyor; 76 uzun ve merkezi bir güzergâh
olduğu için komşu hatların araçlarını kendine çekiyor.

### 71.2. Etkisi yalnız görsel değil

Durak ekranında 76 için **"ortalama 2 dk beklersin"** yazıyor. Ölçüm:

```
76/D SEFAKÖY · 10 Eylül
  330 aralık · ortanca 0,8 dk · ortalama 1,3 dk
  inspection paradox ile yolcu beklemesi 1,6 dk
  aralıkların 195'i (≈%59) BİR DAKİKANIN ALTINDA
```

Fiziksel olarak imkânsız. Yani şişkin atama **tahmini de bozuyor**.

### 71.3. Karar (11 Eylül, Mehmet): şimdilik kalsın

Etkilenen 21 hat: `10E 11A 12A 137 14A 14B 16D 29D 303A 30D 36ES 4 418 500T
76 76D 79B 79K 8E DT2` (+1). **Temiz hatlar: 89, 89A, 13, 15B** — gösterim ve
doğrulama için bunlar kullanılmalı.

🔜 Kalıcı çözüm adayı: PROMPT 5.2'deki **denenmemiş üç servis metodu**
(`GetPlanaUyum_json` · `GetSeferZayi_json` · `GetOtsPlanlananKm_json`) —
araç-hat eşleşmesini geometrik tahminden kesin bilgiye çıkarabilir.

---

## 72. ⭐⭐ ARAYÜZ SUNUCUSU LAUNCHD'DE + AĞ DAYANIKLILIĞI (11 Eylül)

### 72.1. Sunucu artık yedinci launchd servisi

Bölüm 64.6'daki "geri konabilir" maddesi kapandı. `otobus.arayuz.plist`
kuruldu; iki ayar Bölüm 59'da öğrenilen derslerin doğrudan karşılığı:

```xml
<key>ProcessType</key><string>Interactive</string>
   → yoksa launchd arka plan işi sayıp DİSK ERİŞİMİNİ KISITLIYOR;
     7 GB'lık veritabanına giden istekler 60 sn'ye takılıyordu
<key>SoftResourceLimits</key><dict><key>NumberOfFiles</key><integer>8192</integer></dict>
   → varsayılan 256 sınırı "OSError: [Errno 24] Too many open files" ile çökertiyordu
```

Doğrulama: `kill -9` ile öldürüldü, launchd **kendiliğinden geri getirdi**
(yeni PID). Sorgular 0,27-0,55 sn; Bonjour adı üzerinden 0,31 sn. Eski
"launchd altında kararsız" notu artık geçersiz — kök sebep olan SIGBUS
Bölüm 62.5'te çözülmüştü.

Not: `launchd_kur.sh` altı servisi birden kurar ve önce hepsini durdurur;
yalnız arayüz eklenirken çalışan kaydediciyi boşuna kesmemek için plist elle
aynı şablonla yazıldı.

### 72.2. ⛔ KAYDEDİCİ 8 SAAT ÖLÜ KALDI (10→11 Eylül gecesi)

`kaydedici.log`:
```
16:59:07  [bütçe  7/95]  şehir: 6911 araç · 3310 hareketli
17:01:55  şehir: HATA The read operation timed out
   ↳ 1 tur üst üste hata · 180 sn susuluyor
19:20:40  şehir: HATA <urlopen error [Errno 8] nodename nor servname
   ↳ 2 tur üst üste hata · 300 sn susuluyor
00:05:02  şehir: HATA <urlopen error [Errno 8] nodename nor servname
   ↳ 3 tur üst üste hata · 600 sn susuluyor
```

Ağ kesildi → DNS çözülemedi → üstel geri çekilme 600 sn'ye çıktı ve orada
takılı kaldı. Son geçiş kaydı 16:59. Ağ döndüğünde servis kendini
toparlayamadı; `launchctl kickstart -k` ile düzeldi.

🔜 **Açık borç:** geri çekilme bir üst sınırda sonsuza kadar beklememeli;
ağ döndüğünde hızlı yeniden deneme yapılmalı.

### 72.3. IP DEĞİŞTİ — ve uygulama artık kendi kendine toparlanıyor

Aynı gece laptop uyandığında IP **192.168.1.119 → 10.100.35.189** oldu (4
Eylül'de ters yönde yaşanmıştı, Bölüm 62). Telefonda kayıtlı adres bir IP ise
uygulama "sunucu çalışmıyor" der — oysa sunucu ayakta.

`Servis.getir()` artık: kayıtlı adrese ulaşılamazsa **bir kez `.local`
varsayılanını dener**, başarılıysa adresi kalıcı olarak düzeltir. Tek deneme,
sonsuz döngü yok. Bonjour adı ağ değişse de sabit kaldığı için kurtarıcı.

---

## 73. ⛔⛔ BİR AYLIK BOŞLUK — veri neden toplanamadı (4 Ekim)

Staj bitti, 11 Eylül – 4 Ekim arası projeye ara verildi. Dönüşte Mehmet:
*"veri düzgün toplayamadık şimdi biraz toparlıcaz"*.

### 73.1. Belirti

```
gecis tablosu · günlük üretim
  17 Eylül  1.512.243
  22 Eylül  1.828.065
   1 Ekim         494     ← çöküş
   3 Ekim         443
```

Ham konum akışı SAĞLAMDI (6.921 araç, dakikada bir yazılıyor). Çöken şey
ham veriden geçiş ÇIKARIMIYDI.

### 73.2. Kök sebep zinciri

Araç–hat eşleşmesi çökmüştü:

```
arac_hat · günlük ayrı araç
  24 Eylül  4.109
  25 Eylül    332     ← %92 düşüş
   3 Ekim    172
```

Nedeni ölçüldü: `hat_tahmini` bir aracın son `IZ_DK=28` dakikalık konumlarına
bakıp güzergâhını çıkarıyor ve en az `MIN_IZ=4` nokta istiyor. Gerçek ölçüm:

```
A-001   iz uzunluğu=2   tahmin=None
A-002   iz uzunluğu=2   tahmin=None
A-004   iz uzunluğu=2   tahmin=None
```

Ve kaydedici günlüğünde saatlerce boşluklar:
`18:57` → `19:40` (hata) → **`23:52`**.

Gündüz kesiti aynı şeyi gösterdi:
```
08:00  konum      0 · hat eşleşen  0 · geçiş   0     ← Mac uykudaydı
12:00  konum  5.983 · hat eşleşen  0 · geçiş   0
15:00  konum  9.808 · hat eşleşen  3 · geçiş 220
```
Saatte ~180.000 konum beklenirken 5-12 bin: kaydedici 60 tur yerine ~2 tur
atabilmiş.

**Zincir:** Mac uyuyor → kayıt kesintili → iz parçalanıyor → `MIN_IZ` eşiği
geçilemiyor → hat atanamıyor → geçiş çıkarılamıyor.

⚠️ Bu, Bölüm 63'teki "iz parçalanması" sorununun aynısı — orada artımlı geçişe
alırken yaşanmıştı, burada uyku yüzünden.

### 73.3. Çözüm ve ders

`caffeinate -i` YETMİYOR: yalnız boşta kalma uykusunu engelliyor, kapak
kapanınca Mac yine uyuyor. Kalıcı ayar Mehmet tarafından yapıldı:
**Sistem Ayarları → Batarya → Seçenekler → "Ekran kapalıyken otomatik uykuyu
engelle"** (fişteyken).

⚠️ **VERİ KAYBOLMADI, ÜRETİLEMEDİ.** Ham konumlar duruyor; sistem kesintisiz
çalışmaya başlayınca izler uzuyor ve zincir kendiliğinden toparlanıyor.

---

## 74. ⭐⭐⭐ ERİŞİM ANAHTARI (4 Ekim)

Sunucu internete açılacağı için (Bölüm 75) kimlik doğrulaması zorunlu hale
geldi. O ana kadar tek koruma "yalnız ev ağından erişilebilir olmak"tı.

### 74.1. Üç tasarım kararı, üç gerekçe

**Anahtar DOSYADA, kodda değil.** `veri/anahtar.txt`, izin `0600`. Kaynak koda
gömülen sır, kodu gören herkesin sırrıdır.

**Anahtar BAŞLIKTA, adreste değil.** `X-Anahtar` başlığı. Sorgu dizesine
konsaydı (`?anahtar=...`) o adres sunucu günlüklerine, tarayıcı geçmişine ve
ara sunucu kayıtlarına düşerdi.

**Karşılaştırma `hmac.compare_digest` ile.** Normal `==` ilk farklı karakterde
durur; binlerce denemede cevap süreleri ölçülerek anahtarın ne kadarının doğru
olduğu sızdırılabilir (zamanlama saldırısı). Bu fonksiyon sabit sürede çalışır.

### 74.2. ⚠️⚠️ NEDEN "YEREL AĞ MUAF" KURALI YOK

Cazip ama YANLIŞ olurdu: **cloudflared sunucuya `127.0.0.1` üzerinden
bağlanır**, yani tünelden gelen istek YEREL GÖRÜNÜR. Localhost muaf tutulsaydı
korumanın tam da koruması gereken yol muaf kalırdı.

`/saglik` ucu muaf — ama veri döndürmüyor, yalnız "çalışıyor" diyor. Tünelin
ayakta olup olmadığı anahtarsız öğrenilebilsin diye.

### 74.3. Sınama

```
anahtarsız istek   → 401
yanlış anahtar     → 401
doğru anahtar      → 200
/saglik (muaf)     → 200
```
Hem yerelden hem tünel üzerinden doğrulandı.

### 74.4. iOS tarafı

Ayarlar'a `SecureField` ile **Erişim Anahtarı** alanı eklendi. 401 gelince
mesaj ham `401 Unauthorized` değil, NE YAPILACAĞINI söylüyor. Ve yetki
hatasında yedek adres DENENMİYOR — adres doğru, sorun anahtarda; yedeğe düşmek
gerçek sebebi gizlerdi.

---

## 75. ⭐⭐⭐ CLOUDFLARE TÜNELİ — ayrı ağlardan erişim (4 Ekim)

Mehmet: *"telefon mac ayrı iplerdeyken uygulama çalışıcak hale getiricez"* ve
*"cloudflare mac evdeyken ben telefonla dışarıdayken kullanabilir miyim"*.

### 75.1. Neden tünel, port yönlendirme değil

Mac'in IP'si (`10.100.35.189`) ÖZEL bir adres — internette yok, NAT arkasında.
Klasik çözüm modemde port açmaktır ama bu Mac'i doğrudan internete koyar ve
adres tarayan botlar bulur.

Tünel tersini yapıyor: **bağlantıyı Mac BAŞLATIYOR** ve hattı açık tutuyor.
Modem bunu normal bir internet çıkışı sayıyor. Dışarıdan içeri kapı açılmıyor.
Yan faydası: router ayarı ve sabit IP gerekmiyor, kurumsal ağ engellerini de
aşıyor (443 üzerinden çıkıyor).

### 75.2. Kurulum — NEREDE DURUYOR

```
binary   /Users/mehmetkucukbirer/otobus-takip/arac/cloudflared   38 MB · v2026.9.3
servis   ~/Library/LaunchAgents/otobus.tunel.plist   (SEKİZİNCİ launchd servisi)
günlük   veri/tunel.log
```

⚠️ `/usr/local/bin`'e DEĞİL proje içine kuruldu: oraya yazmak `sudo` isteyecekti.
Homebrew kurulu değil, binary doğrudan Cloudflare'in resmi deposundan indirildi.
launchd mutlak yolla çağırdığı için konumun önemi yok.

### 75.3. ⚠️ ÜCRETSİZ TÜNELİN ADRESİ HER BAŞLANGIÇTA DEĞİŞİYOR

Sabit adres için Cloudflare hesabı + alan adı gerekiyor (~$10/yıl). Onun yerine
**otomatik adres keşfi** kuruldu:

- Sunucuda `/api/tunel` ucu güncel adresi döndürüyor (`tunel_adresi()`)
- Telefon EV AĞINDAYKEN (`.local` ile bağlıyken) bu adresi öğrenip saklıyor
- Dışarıdayken sakladığı adrese düşüyor

iOS'ta aday adres listesi, en olasıdan en son çareye:
```
1. bu oturumda çalıştığı görülen adres
2. kullanıcının ayarladığı adres
3. .local      (ev ağı · IP değişse de sabit)
4. tünel       (internet · yavaş, yalnız ayrı ağda gerekli)
```

Tazeleme 10 dakikada birden sık yapılmıyor — adres yalnız tünel yeniden
başlayınca değişir.

**Tek açık:** Mac yeniden başlar ve eve uğranmadan dışarı çıkılırsa telefondaki
adres ölü olur. Sabit adrese geçilirse bu da kapanır — ama **4 Ekim'de Mehmet
"şimdilik gerek yok" dedi**, bu açıkla yaşanıyor.

### 75.4. ⛔ GÜNLÜKTE ADRES BİRİKMESİ — 530 hatasının sebebi

İlk denemede istekler 530 döndü. Sebep: günlükte İKİ adres birikmişti (elle
başlatılan tünel + launchd servisi) ve eski olanı seçiliyordu. Çözüm plist'te:
```
: > veri/tunel.log && exec arac/cloudflared tunnel --url http://127.0.0.1:8790
```
Servis her başladığında günlük sıfırlanıyor, günlükte hep TEK adres kalıyor.

### 75.5. Doğrulama

```
/saglik              → 200
/api anahtarsız      → 401
/api doğru anahtar   → 200 · 0,31-0,72 sn
```
Ve 4 Ekim'de **gerçek telefonda, Wi-Fi kapalı, yalnız 4G ile çalıştığı
doğrulandı.**

### 75.6. ℹ️ Yanlış teşhis notu

Tünel adresi uygulamada görünmeyince `@Observable` + `didSet` ikilisinin
çalışmadığı sanıldı ve saklama açık `set` bloğuna taşındı. Gerçek sebep başkaydı:
doğrulama komutu (`simctl spawn defaults read`) uygulamanın sandbox'ını değil
simülatörün kendi domain'ini okuyordu. Özellik baştan beri çalışıyormuş.
Değişiklik zararsız ve niyeti daha okunur kıldığı için bırakıldı.

---

## 76. ⭐⭐⭐ GÖZCÜ SERVİSİ — aynı arıza üçüncü kez olmasın (4 Ekim akşamı)

### 76.1. Olay

4 Ekim 18:46'da ağ koptu (IP `10.100.35.189` → `192.168.1.119`, ağ değişmiş).
İnternet kısa sürede döndü ama sistem **üç saat** ölü kaldı:

```
saat    konum    hat-eşleşen   geçiş
15:00  171.911       2.161    103.481   ✅ gündüz kusursuz
17:00  174.364       2.198    104.692   ✅
18:00   81.715       1.475     49.704   (yarıda koptu)
19:00        0           0          0   ⛔
20:00        0           0          0   ⛔
21:33  — elle yeniden başlatıldı —
```

⚠️ Dikkat: gündüz rakamları Bölüm 73'teki uyku ayarının İŞE YARADIĞINI
kanıtlıyor. Sorun uyku değil, ağ kesintisinden sonra TOPARLANAMAMAK.

### 76.2. İki ayrı kilitlenme

**KAYDEDİCİ — geri çekilme tavanında kilitleniyor.** Hata üstüne hata alınca
bekleme katlanıyor: 180 → 300 → 600 → 1800 sn. Tavana çıkınca orada kalıyor:

```
19:06  HATA nodename nor servname   ↳ 5 tur üst üste hata · 1800 sn susuluyor
21:10  HATA nodename nor servname   ↳ 9 tur üst üste hata · 1800 sn susuluyor
```

Ağ beş dakikada dönse bile 30 dakika uyuyor; uyanıp yine hata alırsa 30 dakika
daha. Bu borç Bölüm 72.2'de yazılmıştı, ikinci kez ısırdı.

**TÜNEL — kaydı silinince geri gelemiyor.**
```
ERR Register tunnel error: "Unauthorized: Tunnel not found"
```
Ücretsiz hızlı tünel geçicidir; bağlantı uzun süre kopunca Cloudflare kaydı
siliyor. cloudflared yeniden bağlanmayı deniyor ama **süreç ÖLMÜYOR**, bu
yüzden launchd'nin `KeepAlive`'ı da devreye girmiyor. Sonsuza kadar boşa
deniyor. Tek çare dışarıdan yeniden başlatmak (yeni adres alır).

### 76.3. Çözüm — `gozcu_dongusu.sh` (DOKUZUNCU servis)

5 dakikada bir iki şeye bakıyor:

| kontrol | eşik | müdahale |
|---|---|---|
| `filo_konum` son kayıt yaşı | 10 dk | `kickstart otobus.kaydedici` |
| tünel `/saglik` cevabı | ≠ 200 | `kickstart otobus.tunel` |

⚠️⚠️ **ÜÇ TASARIM KARARI:**

**1. Önce internet kontrolü.** Ağ gerçekten yoksa yeniden başlatmanın faydası
yok — sadece günlüğü şişirir ve servisleri boşuna sarsar. İnternet yoksa gözcü
hiçbir şeye dokunmuyor, bekliyor.

**2. Tünel kontrolü YEREL sunucuya değil TÜNEL ADRESİNE yapılıyor.** 4 Ekim'de
tam bu oldu: yerel sunucu gayet ayaktaydı, kopuk olan tüneldi. Yerele baksaydık
arızayı hiç göremezdik.

**3. Gözcünün gözcüsü launchd.** Gözcü diğer servisleri `kickstart` ile
başlattığı için onlardan bağımsız olmalı; kendi ölürse `KeepAlive` geri getirir.

**Kazanım:** en kötü senaryoda kesinti 3 saat yerine **15 dakika** (5 dk periyot
+ 10 dk eşik).

### 76.4. Toparlanmanın fizik sınırı

Kesintiden sonra duraklar hemen dolmuyor ve bu normal: hat tahmini bir aracın
son `IZ_DK=28` dakikalık izine bakıp en az `MIN_IZ=4` nokta istiyor. Kaydedici
yeniden başladığında iz sıfırdan birikiyor, pencere dolana kadar ~20 dakika
geçiyor. Ölçüm (21:33'te yeniden başlatma sonrası):

```
21:33  hat tahmini +0
21:36  hat tahmini +10
21:38  hat tahmini +25
21:40  hat tahmini +35
```

⚠️ Darboğaz İŞLEM GÜCÜ DEĞİL: ölçüldü, tahmin araç başına 24,7 ms ve
`TAHMIN_PER_TUR=220` turun 60 saniyesine rahat sığıyor. Darboğaz iz uzunluğu —
hızlandırılamaz, beklenir.

---

## 77. ⭐⭐⭐ SUNUCU HIZI — rota ızgarası + izdüşüm önbelleği (7 Ekim)

Mehmet: *"gün içinde uygulamayı kullanmak istediğimde sunucu yavaş çalışıyor"*.

### 77.1. Ölçüm — gece değil, GÜNDÜZ yüküyle

Gece ölçülen süre (0,19 sn) yanıltıcıydı: şehirde 500 hareketli araç var,
gündüz 5.600. Motor zaman parametresi aldığı için dünkü gündüz verisiyle
gerçek yük ölçülebildi (`durakta_ne_var(kod, an=...)`):

```
08:30  SEFAKÖY  1,18 sn · 14 hat · 10 canlı
14:00  SEFAKÖY  1,46 sn · 14 hat · 15 canlı
18:00  SEFAKÖY  1,28 sn · 14 hat · 22 canlı
```
Tünel gecikmesiyle telefonda 2-3 sn hissediliyordu.

ℹ️ Yan bulgu: gündüz SEFAKÖY **14 hat** gösteriyor. Bölüm 76'dan sonraki
denetimde "durakların %52'si boş" görünmesi GECE ETKİSİYMİŞ — doğrulandı.

### 77.2. Kök sebep — profil

```
durakta_ne_var                     0,190 sn
  canli_araclar → hattaki_araclar  0,513 sn / 3 istek   (%90)
    yon_bul → _bacak_puani
      yol_uzerinde                 5.606 çağrı
        _parca_izdusum           468.667 çağrı   ← burası
```

`rota.yol_uzerinde` her noktayı rotanın BÜTÜN parçalarıyla (ortalama 84)
tek tek kıyaslıyordu. Saf Python döngüsü; gündüz araç sayısı 10 kat → milyonlarca
izdüşüm.

### 77.3. Çözüm 1 — ızgara (`rota.py`)

Rota `HUCRE_M = 250` m'lik hücrelere bölünüyor; her hücre, sınır kutusu ona
değen parçaların indekslerini tutuyor (`_izgara`, hat-yön başına bir kez).
Sorguda önce noktanın hücresine, sonra komşu halkaya bakılıyor.

⚠️⚠️ **SONUÇ BİREBİR AYNI — yaklaşık değil.** Bu fonksiyon geçiş çıkarımında
(`gecisler.py`) ve yön tespitinde de kullanılıyor; yön tespiti sapmaların
ORTALAMASINI alıyor. Küçük bir fark geçiş verisini kaydırırdı.

Kesinlik kanıtı: nokta P, (cx,cy) hücresinde. r halkasına kadar bakıldıysa
bakılmamış her parçanın sınır kutusu karenin DIŞINDA; o parçanın her noktası
P'ye r·H'den KATI olarak uzak. En iyi sapma ≤ r·H ise durmak güvenli. Eşitlikte
en küçük indeks seçiliyor — eski döngü de ilk minimumu tutuyordu.

**Doğrulama: 62.623 noktada eski ↔ yeni birebir karşılaştırıldı, sıfır fark.**
```
gerçek durak çağrıları        44.728 nokta · fark 0
rastgele (çoğu rotadan uzak)  15.000 nokta · fark 0
rota çizgisinin tam üstü       2.895 nokta · fark 0   (eşitlik uç durumları)
```

⚠️ İlk testte ızgara DAHA YAVAŞ çıktı (0,7x) — çünkü test noktaları şehrin
rastgele yerlerindendi, çoğu rotadan uzaktı. Gerçek çağrılarda araçların %86'sı
kendi rotasına 250 m'den yakın. **Ders: hızlandırmayı gerçek iş yüküyle ölç.**

### 77.4. Çözüm 2 — izdüşüm önbelleği (YALNIZ sunucuda)

`arayuz_sunucu.py` açılırken: `rota.yol_uzerinde = lru_cache(maxsize=100_000)(...)`.
Uygulama 30 sn'de bir yeniliyor, bir aracın iz noktaları ardışık isteklerde
büyük ölçüde aynı kayıtlar. Aynı girdi → aynı çıktı, sonuç kesin.

⚠️ `rota.py`'nin kendisine KONMADI: geçiş çıkarımı şehrin tamamını tarıyor,
orada isabet düşük olur ve sadece bellek yerdi. Tüm çağıranlar
`rota.yol_uzerinde(...)` biçiminde çağırdığı için sunucudaki atama hepsine ulaşıyor.

Ayrıca: `yol` ve `durak_mesafeleri` önbellekleri 256 → 2048 (1.495 hat-yön çifti
var, 256 gündüz çalkalanıyordu). Ön ısıtmaya tüm ızgaralar eklendi (1.300
hat-yön, 0,35 sn).

### 77.5. Sonuç

```
gündüz yükü, ısınmış sunucu     eski      yeni
yeni konumlarla                 0,73 sn   0,31 sn   → 2,3x
aynı veriyle yenileme           0,72 sn   0,04 sn   → 18x
canlı HTTP (gece)                         0,02-0,25 sn
```
Kazanım SUNUCU tarafında — telefondaki eski uygulama sürümü de faydalanıyor.

---

## 78. ⭐⭐⭐ ARAMADA AYIRT EDİCİLİK (7 Ekim)

Mehmet: *"durakların konumu hangi durak olduğu aramada çok ayırt edici değil"*.

### 78.1. Sorunun boyutu

**13.196 durağın 11.539'u (%87) adını başka bir durakla paylaşıyor.**
"ATATÜRK CADDESİ" 33, "SİTELER" ve "FATİH CADDESİ" 27'şer ayrı durak.

### 78.2. ⚠️⚠️ Sezgi yanlış çıktı — ilçe işe yaramıyor

Hangi bilginin ayırt ettiği ölçüldü (aynı görünen durak sayısı):

| gösterilen | karışan |
|---|---|
| sadece ad | %87,4 |
| ad + ilçe | %80,8 ← neredeyse hiç fark yok |
| ad + ilçe + hatlar | %59,1 |
| ad + tüm yönler | %1,5 |

İlçe ayırmıyor çünkü aynı adlı duraklar çoğunlukla **aynı caddenin karşılıklı
iki tarafı**: aynı ilçe, aynı hatlar. Onları ayıran tek şey hangi yöne
gittikleri. Ama tüm yönler tek satıra sığmıyor.

### 78.3. Ayırt edici yön — tek satırda neredeyse tam ayrım

Eski ekran İLK yönü (en çok hattın gittiği) gösteriyordu. Karşılıklı iki durak
çoğu zaman ortak bir yön paylaşıyor (ikisinden de geçen bir ring hattı) — ilk yön
o ortak yön olunca ikisi ekranda ÖZDEŞ görünüyordu.

Yeni: **aynı adlı kardeşlerde BULUNMAYAN yön başa alınıyor**
(`_ayirici_yon_sirasi`).

| tek satırda gösterilen yön | karışan |
|---|---|
| ilk yön (eski) | %5,6 · 742 durak |
| **ayırt edici yön** | **%1,7 · 227 durak** |
| tüm yönler (referans) | %1,5 |

⚠️ Kardeşler GLOBAL hesaplanıyor (aynı adlı TÜM duraklar), yalnız sonuç
listesindekiler değil: 25 sonuç sınırında bir kardeş kesilmiş olabilir; global
olarak benzersiz olan yön sonuç listesinde de benzersizdir.

### 78.4. Kalan %1,7 için — konum

- **İlçe** Türkçe karakterle (`ILCE_DUZELT`: `Bakirköy`→`Bakırköy`,
  `Bagcilar`→`Bağcılar`, `Sisli`→`Şişli` … 16 ilçe). Kaynak İETT verisi bozuk
  geliyor; düzeltme gösterim katmanında.
- **Hatlar** doğal sırayla (89, 89A, 98, 141M) — en fazla 6, fazlası `+N`.
  Ayırt edicilikte zayıf ama yolcunun en iyi tanıdığı bilgi.
- **Uzaklık**: telefon konumu gönderirse her sonuca eklenir ve aynı uzunluktaki
  adlar (yani kardeşler) EN YAKINDAN uzağa sıralanır. ⚠️ Konum varken SQL'de
  400 satır alınıp Python'da sıralanıyor: `LENGTH` sırasıyla 25'te kesilseydi
  33 kardeşten en yakını kesilmiş olabilirdi.
- Ad içindeki çift boşluk tekleniyor (`SEFAKÖY  MERKEZ` kaynak veride kirli).

### 78.5. iOS tarafı

```
SEFAKÖY                                     yanında  ♥
KANUNİ SULTAN SÜLEYMAN YÖNÜ                 ← mavi, kalın: asıl ayırt eden
Küçükçekmece · 73B 73F 73H 76 76V +12       ← nerede + hangi hatlar
```

⚠️ **Arama izin penceresi AÇMIYOR.** Konum yalnız "Yakınımdaki Duraklar"
izni ÖNCEDEN verilmişse kullanılıyor (`Konumcu.izinliyseKonum`): yolcu durak
adı yazarken "konumuna erişebilir miyiz?" çıkması işi bölerdi. Konum sayfa
açılırken BİR KEZ alınıyor, her harfte değil (GPS 1-3 sn sürer); 10 dakikadan
taze son bilinen konum varsa o anında kullanılıyor.

Uzaklık biçimi: `yanında` (<40 m) · `850 m` · `3,9 km` · `12 km`.

---

## 79. ⭐⭐⭐ DURAN ARAÇ "CANLI YAKLAŞAN" DEĞİLDİR (7 Ekim)

Mehmet: *"bu saatte yolda otobüs olması imkansız ama uygulama tek tük otobüs
gösteriyor, bunlar duran ama GPS açık otobüsler olabilir — yanlış bilgilendirme"*.

### 79.1. Kök sebep

Kaydedici duran araçları da 10 dk'da bir yazıyor (`DURAN_ARAC_NABZI_DK`) —
"peronda bekleyen" ile "GPS'i sönmüş"ü ayırmak için. Veri tarafında DOĞRU karar.
Ama durak ekranı bu nabız kayıtlarını yaklaşan otobüs sanıp "17 dk sonra" diyordu.

```
gece  01:54   140 "canlı" araç → 123'ü son 30 dk'da <120 m, hız 0  (%88 YANLIŞ)
sabah 08:15   206 "canlı" araç →  15'i son 20 dk'da <150 m          (%7)
akşam 18:00   254 "canlı" araç →  17'si                              (%7)
```
Gündüz de vardı, sadece gece göze batıyordu.

### 79.2. Kural — `DURAN_ESIK_M = 150`

İzdeki (son 20 dk, `IZ_PENCERESI_DK`) yer değiştirme 150 m'den azsa araç canlı
yaklaşan SAYILMAZ. Ek sorgu yok: iz zaten yön tespiti için çekiliyor; ölçü
`yon_tespit.hattaki_araclar` sonucuna eklendi. Gizlenen araç bilgi kaybı değil:
o hat için tarife/gözlem kademesi devralıyor.

### 79.3. ⚠️⚠️ Doğrulama — gizlenen araç gerçekten GELDİ Mİ?

`gecis` tablosundan, 6 Ekim verisiyle ("geldi" = gösterilen dakika + 20 dk içinde
o duraktan geçti):
```
gece   01:50   gizlenen 29 → geldi  0   ✅ ortanca 120 dk'dır yerinde duruyorlarmış
sabah  08:15   gizlenen 21 → geldi 11   gündüz son durakta kalkış bekleyenler
akşam  18:00   gizlenen 21 → geldi  6
```
Gündüz gizlenip yine de gelenlerde eski ekranın dakikası **−25…+15 dk** şaşıyordu.
Ve gizlenen aracın hattı ekrandan KAYBOLMUYOR: 42 gündüz vakasının 40'ında hat
başka kaynakla görünmeye devam etti (25 başka canlı araç · 9 tarife · 4 GPS-kapalı
· 2 gözlem).

Denenip REDDEDİLEN ayırıcılar: "durma süresi" ve "yakın tarife kalkışı" — park ile
kalkış beklemeyi temiz ayırmadı (tarifesi olan duran araçların bile %62'si gelmedi).

⚠️⚠️ **EŞİĞİ YÜKSELTME.** 300 ve 400 m denendi: sabah 150 m → 21 gizli (11 geldi),
300 m → 25 gizli (15 geldi). Eklenen 4 aracın 4'ü de gerçekten gelmişti; gece
hiçbir kazanç yok. Yavaş trafik 150-400 m bandında, park 150 m altında.

### 79.4. ⛔ İlk sürümün hatası — "ilk-son" yerine "EN UZAK" (aynı akşam düzeltildi)

İlk sürüm izin ilk ve son noktasını kıyaslıyordu. 20 dk içinde gidip başladığı yere
dönen gerçek otobüsü (son durakta dönüş, ring güzergâh) duruyor sanıyordu:
```
55T  B-1756   ilk-son 102 m · ama arada 1.518 m uzaklaşmış · dakikada bir kayıt
KM12 C-325    ilk-son  57 m ·                    1.592 m
63   B-1821   ilk-son  27 m ·                      732 m
```
Ölçü artık `en_uzak_m` — izdeki en uzak noktanın son konuma uzaklığı. Duran araç
hiç uzaklaşmaz, dönen araç uzaklaşıp gelir. Gerçek varışlarla:
```
sabah  gizlenen 21 → 17 · bunlardan gelen 11 → 8   (3 otobüs kurtarıldı)
akşam  gizlenen 21 → 19 · bunlardan gelen  6 → 5
gece   29 → 29 · gelen 0 → 0                        (GPS sıçraması sorun yaratmadı)
```

### 79.5. Sonuç (canlıda, 7 Ekim)

```
gece  02:08   "canlı" 140 → 15   (yol alan 10 · park 123 → 1)
gündüz 16:58  778 "canlı" araç, %96,5'i gerçekten yol alıyor
```

ℹ️ Açık soru: gündüz gösterilen gerçek hareketli araçların da ~%20'si durağa
gelmiyor (yön hatası ya da güzergâh değişimi olabilir) — ayrı bir doğruluk konusu.

---

## 80. 🔧 KONTROL TURU — dört düzeltme (7 Ekim akşamı)

Mehmet: *"her şeyi düzgün çalışıyor mu diye kontrol et, bir sıkıntı varsa düzelt"*.

### 80.1. ✅ Sağlam bulunanlar
- Dokuz servis ayakta · `kayit.db` (9,7 GB) ve `dizin.db` **quick_check: ok**
- Gözcü tüneli üç kez onarmış (6.10 00:26 · 7.10 06:44 · 7.10 09:31)
- Erişim yolları ve anahtar koruması doğru · kaydedici bir DNS takılmasından 3 dk'da
  kendini toparladı

### 80.2. ⛔ "1.442 dk" — iptal satırı yarına kayıyordu
Denetim `BA-2 · DEĞİRMEN PLAJI → 1.442 dk` buldu. Tarifedeki 17:03, saat 17:03'ü
birkaç saniye geçince YARINA kaydırılıyordu; iptal anahtarı (hat, yön, saat) tarih
taşımadığı için BUGÜNÜN iptal duyurusu YARININ aynı saatli seferine iliştiriliyordu.
İptal satırında ufuk yokluğu kasıtlıydı ("gelmeyeceğini bilmek değerli") — birkaç
saat için doğru, 24 saat için anlamsız. **`IPTAL_UFKU_DK = 360`**: gece yarısını
aşan yakın iptaller (23:50'de 00:10 seferi) korunur. 211 aktif iptal yerinde kaldı.

### 80.3. ⛔ Aynı hat iki kart olarak görünüyordu
Bazı güzergâhlar bir duraktan AYNI TURDA İKİ KEZ geçiyor (döngülü güzergâh, ring
hat): şehirde **87** (durak, hat, yön) çifti birden fazla sırada (BA-5/G DEĞİRMEN
PLAJI'nda 5. ve 11. durak; MK12/G'de 1 ve 42). Motor her sıra için kart açıyordu,
tarife tahmini durak koduna göre yapıldığı için iki kart AYNI dakikaları gösteriyordu.
`_ayni_hat_kartlarini_birlestir`: varışlar tek kartta, aynı araç/kalkış tekrarında
EN YAKINI tutuluyor. Kart üretimine dokunulmadı — çıktının sonunda birleştirme.

### 80.4. ⛔ Bazı durak istekleri 6,2 sn sürüyordu — HAVA DURUMU
Ölçüldü: 3 sn'den uzun süren 23 isteğin **23'ünde** hava bilgisi boş (zaman aşımı);
kısa sürenlerin 2/97'sinde. Aynı anda birden çok bölge sorulunca open-meteo
yavaşlıyor ve durak cevabı süs niteliğindeki bir sıcaklığı `timeout=6` bekliyordu.
Trafikte risk daha büyüktü: hata durumunda önbelleğe HİÇBİR ŞEY yazmıyordu — servis
aksarsa HER istek 8 sn bekleyecekti.

İkisi de **bekletmeyen önbelleğe** çevrildi (`_arka_planda`): önbellekte varsa (bayat
bile olsa) hemen döner, yoksa None döner ve değeri arka planda getirir. Aynı anahtar
için ikinci istek açılmaz. Hata durumunda eski başarılı değer korunur. Trafik ön
ısıtmada senkron dolduruluyor.
```
500 durak · 6 paralel · soğuk önbellek     önce     sonra
3 sn'den uzun istek                         ~23       0
en yavaş                                  6,3 sn   1,8 sn
ortanca                                   0,35 sn  0,07 sn
```
Uygulamada değişiklik gerekmedi: `hava`/`trafik` opsiyonel, boşken çip görünmüyor.

### 80.5. ℹ️ Bildiğimiz ama dokunmadığımız
- **Bir kez "database disk image is malformed"** (eski kod sürümünde, `durak_ara`
  içinde, `dizin.db`). Dosyalar sağlam. `dizin.db` salt okunur DEĞİL: sabah rutini
  İETT sefer arşivini `sefer` tablosuna ekliyor (2,6 M satır, büyüyor) — o yazmayla
  sunucunun okumasının çakışması muhtemel. Tekrarlarsa: `dizin.db`'yi WAL'a almak.
- **Duyuru döngüsü `database is locked`** — tüm günlükte 27 kez (00, 02, 03, 12-14
  saatlerinde). `timeout=90` aşılıyor; başka bir süreç uzun yazma kilidi tutuyor. O
  turun duyuruları 10 dk sonraki turda yakalanıyor — etkisi görünmez.

---

## 81. 🧭 SUNUCU NEREDE ÇALIŞMALI — karar: Mac'te kalıyor (8 Ekim)

Mehmet: *"bu sistem neden düzgün çalışmıyor, sürekli bir sorun çıkıyor — evde
kullanmadığım eski bir Android tablet var, sunucu olarak kullanabilir miyiz"*.

### 81.1. "Sürekli sorun" iki farklı türden
- **Ortamdan gelenler** (dizüstünde sunucu olmanın bedeli): Mac uykusu (Bölüm 73),
  IP değişimi (72.3), ağ kesintisinde kaydedici kilidi (76), ücretsiz tünelin
  kopması (76, 80).
- **Mantık hataları** (en baştan beri vardı, denetledikçe bulundu): duran araç
  (79), 1.442 dk, çift kart, hava bekletmesi (80), gün tipi (68)… Bunlar
  kararsızlık değil İLERLEME işareti — bulundukları için artık yoklar.

### 81.2. Ölçülen kaynak ihtiyacı (Mac M2, 8 Ekim)
```
disk          ~10 GB veri (budamayla sınırlı) + ~3 GB pay (ACIL_GB) + WAL
geçiş döngüsü ortalama 104 sn · en uzun 5.158 sn (86 dk!) · periyot 600 sn
model döngüsü 115-138 sn · periyot 3.600 sn
bellek        kaydedici ~200 MB · diğerleri küçük
diske yazma   günde ~2,5 GB (4,1 M konum + 2,3 M geçiş, indeksler dahil)
```
Eski tablet için asıl engel İŞLEMCİ: ARM çekirdek 5-15 kat yavaşsa geçiş döngüsü
10 dk periyoda yetişemez, sürekli geride kalır. Ayrıca 7/24 şarjdaki yıllanmış
batarya şişebilir (güvenlik). Root arka plan öldürmeyi çözer, bunları çözmez.
Daha iyi adaylar: Windows masaüstü (sabit, güçlü, bataryasız) ya da Raspberry Pi 5.
"Dış kütüphane yok" kararı (yalnız Python + SQLite) taşımayı kolaylaştırırdı.

**Karar (Mehmet): tablet ve PC şimdilik elendi, sunucu Mac'te kalıyor.**

---

## 82. ⭐⭐⭐ ADRES PANOSU — dışarıdaki telefon yeni tünel adresini kendisi buluyor (8 Ekim)

Mehmet: *"her IP değişikliğinde neden otomatik olarak kullanamıyoruz anlamadım"*.

### 82.1. Asıl sorun IP değil, tünel adresi
- Evde: telefon Mac'i `.local` ADIYLA buluyor → IP değişimi zaten otomatik.
- Dışarıda: tünel Mac'ten dışarı açıldığı için IP önemsiz, kısa kopuşta kendini bağlar.
- AMA uzun kopuşta Cloudflare ücretsiz tünelin kaydını siliyor; gözcü yeniden
  başlatıyor ve tünel YENİ, RASTGELE bir adres alıyor (6-7 Ekim'de 3 kez).
  Dışarıdaki telefon eski adresi tutuyor; yenisini Mac'e sorması gerek ama Mac'e
  ulaşmak için de yeni adres lazım. **Tavuk-yumurta.** Evdeki `.local` döngüyü
  kırdığı için "eve gelince düzeliyordu".

### 82.2. Seçenekler ve karar
| | ücret | adres | kurulum | not |
|---|---|---|---|---|
| Tailscale | ücretsiz | hiç değişmez | Mac+telefona uygulama, VPN açık | sadece senin cihazların; tünel kopması biter |
| **Adres panosu** | ücretsiz | değişir, telefon dışarıdan öğrenir | hiçbir şey | anahtarı olan herkes kullanabilir; kopuşta birkaç dk kesinti |
| ngrok sabit ad | ücretsiz | değişmez | hesap | trafik kotası |
| Cloudflare + alan adı | ~$10/yıl | değişmez | hesap + alan adı | ücretli |

**Mehmet panoyu seçti** (kurulumsuz, başkaları — mentör — da kullanabilir).

### 82.3. Tasarım — `pano.py`
Mac her yeni adresi ntfy.sh'ta **gizli adlı bir konuya** asıyor (`veri/pano_konu.txt`,
izin 0600, `otobus-<24 onaltılık>`). Telefon tüm adresler düşerse panoya bakıyor.

⚠️⚠️ **İLANLAR İMZALI.** ntfy konuları herkese açık YAZILABİLİR: adı öğrenen biri
sahte adres asarsa telefon oraya gider ve **X-Anahtar'ını ORAYA gönderir** — tek
korumamız sızar. Her ilan: `{"adres", "zaman", "imza"}`,
`imza = HMAC-SHA256(anahtar, "adres|zaman")` onaltılık. Telefon imzası tutmayanı
yok sayıyor; `zaman` sonPanoZamani'ndan eskiyse de (tekrar saldırısı) reddediyor.
Adres bilmek yine de yetmiyor: sunucu anahtarsız isteği 401'liyor.

⚠️ **ntfy 12 saat saklıyor** (ölçüldü: expires − time = 43.200 sn). Adres uzun süre
değişmezse pano BOŞALIR → aynı adres `YENILEME_SAAT = 6`'da bir yeniden asılıyor.

⚠️ **Sağlıksız adres asılmıyor** (`/saglik` 200 olmalı). Bu kontrol sınamada işe
yaradı: `kickstart` sonrası `veri/tunel.log` bir an ESKİ hâlinde kalıyor, eski
adresi okuyan bir betik ölü adresi asabilirdi.

**Akış:** gözcü her turda `python3 pano.py` çalıştırıyor (değişiklik yoksa
"güncel", ilan yok). Tüneli kendisi yeniden başlattıysa 45 sn bekleyip hemen asıyor.
`/api/tunel` artık `{"adres", "pano"}` döndürüyor — telefon evdeyken panonun adını
da öğreniyor (koda gömülü değil, değişebilsin).

**Telefon (`Servis.swift`):** aday adresler (aktif → ayar → .local → tünel) düşerse
`panodanAdres()` → en yeni GEÇERLİ ilan → `tunelAdres` güncellenir → bir kez daha
denenir. CryptoKit `HMAC<SHA256>`.

### 82.4. Doğrulama
- **Python imzası Swift'te doğrulandı** — ayrı bir Swift betiğiyle, gerçek panodan
  gerçek ilan üzerinde; yanlış anahtarla imzalanmış sahte ilan reddedildi.
- Tünel yeniden başlatıldı → `pano.py` → "asıldı"; ikinci çağrı → "güncel".
- Simülatörde: uygulama evdeyken pano adını ve güncel tünel adresini öğrendi
  (elle konan ölü adresin üstüne yazdı).

### 82.5. ⛔ Bulunan hata — ölü tünel HTML döndürüyor, uygulama pes ediyordu
Ölü bir tünel adresi bağlantı hatası değil, **Cloudflare'in HTML hata sayfasını
(HTTP 530)** döndürüyor. Uygulama bunu JSON diye çözmeye çalışıyor, `DecodingError`
atıp `getir` HEMEN vazgeçiyordu — sıradaki adrese ve PANOYA hiç geçmeden. Yani pano
tam ihtiyaç anında devreye girmeyecekti. Düzeltme (`istek()`): **JSON olmayan cevap
= bu adres bizim sunucu değil** → `URLError` → sıradakine geç. Sunucumuz her cevabı
JSON döndürüyor (200, 404, 401 doğrulandı). Kafe Wi-Fi giriş sayfalarına (200 + HTML)
da aynı koruma işliyor.

### 82.6. Gerçek telefon sınaması (8 Ekim 17:41)
Telefon başka bir Wi-Fi'de (Mehmet'in hücresel verisi kapalı), elindeki tünel adresi
ölü (530), tünel yeni adresle yeniden başlatıldı, pano güncellendi → **veri geldi.**
Tünel sayacında 17:41:32'de bir istek görüldü (gözcü kontrolü de olabilir).
✅ **Geçerli sınama** — Mehmet doğruladı: iki Wi-Fi FARKLI modemlerden. Telefon Mac'in
ağında değildi (`.local` erişilemez), elindeki tünel adresi ölüydü (530) — veriyi
yalnız panodan yeni adresi öğrenerek getirebilirdi. Pano yolu ve 82.5 düzeltmesi
gerçek koşulda birlikte doğrulandı.

### 82.7. ~~🔜 Karar bekleyen~~ — bildirim: ntfy seçildi, kuruldu → Bölüm 84
Mehmet: *"anahtar değiştiğinde güncel anahtarı bana WhatsApp'tan mesaj olarak
göndersin"*. Erişim anahtarı HİÇ değişmiyor → "adres" kastedildiği varsayıldı.
Anahtarı göndermemesi önerildi (tek koruma; üçüncü servisten geçen mesajda durmamalı).
Seçenekler: **ntfy uygulaması** (önerilen — pano zaten ntfy'de, abone ol → anlık
bildirim; hesap/numara yok) · **CallMeBot** (WhatsApp; Mehmet bir kez mesaj atıp
anahtar alır; numara üçüncü servise gider) · resmi WhatsApp API (kişisel kullanım
için ağır). Not: uygulama adresi artık kendi bulduğu için mesaj yalnız bilgi amaçlı.

---

## 83. ~~📌 SİSTEMİN ŞU ANKİ HÂLİ~~ — Bölüm 85'e taşındı (8 Ekim akşamı)

---

## 84. ⭐⭐ BİLDİRİM + GİT — adres değişince telefona haber, değişiklikler görünür (8 Ekim akşamı)

### 84.1. Bildirim — karar: ntfy uygulaması (82.7 kapandı)
Mehmet ntfy'yi seçti (kurulumsuz, hesap/numara yok). Telefona ntfy uygulaması kuruldu,
**ayrı bir gizli konuya** abone olundu.

**Neden panodan AYRI konu?** Pano imzalı JSON taşıyor (bildirimde okunmaz) ve aynı
adresi 6 saatte bir yeniden asıyor (82.3) → panoya abone olmak günde 4 anlamsız
bildirim demek. Bildirim konusu: `veri/bildirim_konu.txt` (0600,
`otobus-bildirim-<24 onaltılık>`) — panonun adından bağımsız, birini bilen ötekini bilmiyor.

**`pano.py` değişikliği:**
- `_gizli_ad()` — konu adı üretimi ortak; `konu()` + yeni `bildirim_konu()`
- `bildir()` — okunur mesaj: "Tünel yeni adres aldı: <adres> … bir şey yapman
  gerekmiyor". **JSON olarak** yayınlanıyor: HTTP başlıkları Türkçe harf taşımıyor
  (`Title: Otobüs` → latin-1 hatası).
- `gerekiyorsa_as()` — panoya astıktan sonra **yalnız `son.adres != adres` ise** bildiriyor;
  6 saatlik tazeleme sessiz. Bildirim düşerse pano yine asılmış sayılıyor (asıl iş o):
  sonuç "asıldı: … · bildirildi" ya da "· bildirim gönderilemedi (…)".
- `python3 pano.py --dene` — elle deneme bildirimi (abonelik sınaması).

Gözcüye dokunulmadı: her turda `pano.py`'yi yeni süreçle çalıştırıyor, değişiklik
kendiliğinden devrede. `veri/gozcu.log`'daki 📌 satırında artık "· bildirildi" de görünür.

⚠️ **Mesajda anahtar YOK** ve bu konuyu uygulama OKUMUYOR → konunun adını öğrenen
biri sahte "yeni adres" assa bile anahtar sızmaz (82.3'teki imza ihtiyacı burada yok).
Bildirim yalnız BİLGİ: uygulama adresi zaten kendisi buluyor (82).

### 84.2. Doğrulama
- **18:10 `--dene`** → kilit ekranına geldi ✅ (Mehmet doğruladı).
- **18:18 değişim sınaması (kesintisiz, tünele dokunmadan):** `pano_son.json`'a sahte
  eski adres yazıldı → `pano.py` "asıldı · bildirildi"; kayıt gerçek adresle kendiliğinden
  düzeldi; ikinci çağrı "güncel" (aynı adres için tekrar bildirim YOK) ✅; panodaki yeni
  ilanın imzası doğru ✅.
- ⚠️ **AMA 18:18 bildirimi kilit ekranına GELMEDİ.** Mesaj ntfy uygulamasının listesinde
  var — fakat uygulama açılınca sunucudan kendisi çekiyor, bu anlık iletimi kanıtlamaz.
  Sunucu tarafında iki mesaj birebir aynı biçimde (konu, öncelik 3, etiket, 143 karakter).
  Sorun Mac'teki yayında değil; telefona anlık iletimde ya da iOS'un gösteriminde
  (aynı uygulamanın bildirimleri üst üste yığılabiliyor).
- ✅ **Kontrollü deneme (9 Ekim 00:46:40):** kilit ekranı temiz, telefon kilitli, aynı yol
  (sahte eski adres → `pano.py`). Bildirim **birkaç saniyede kilit ekranına geldi**
  (Mehmet doğruladı; ntfy'ye 00:46:42'de ulaştı). 18:18'deki kaçış tekrarlanmadı —
  büyük olasılıkla iOS'un yığması ya da telefonun o anki durumu. Anlık iletim çalışıyor.
- ✅ **Sessiz tazeleme gerçek koşulda:** gözcü 9 Ekim 00:23'te aynı adresi 6 saatlik
  tazelemeyle yeniden astı — `gozcu.log` satırında "bildirildi" YOK.

ℹ️ ntfy gönderimden hemen sonra sorgulanırsa mesaj birkaç saniye görünmeyebiliyor
(ilk sorgu 0 döndü, 2 sn sonra geldi) — "gitmedi" sanma.

### 84.3. Git — proje sürüm geçmişine alındı
Mehmet: *"arka planda ne yapıyorsan bunların hepsini görmemi sağla, yaptığın
değişiklikleri görmek istiyorum"*. Git yokken bir değişikliğin farkını göstermek için
eski hâli elle yeniden kurmak gerekti. Artık **yerel git deposu** (`main` dalı) var.

- **Yalnız bu Mac'te** — uzak depo (GitHub) YOK.
  ⚠️ VS Code'daki mavi **"Publish Branch"** = GitHub'a yükleme. Karar verilmedi, basılmamalı.
- `.gitignore`: `veri/` (10 GB + anahtar ve konu adları — gizli bilgi geçmişe GİRMEMELİ),
  `arac/` (indirilmiş binary), `.DS_Store`, `xcuserdata/`, `DerivedData/`, `build/`,
  `__pycache__/`. Almadan önce tarandı: anahtar ve iki konu adı `veri/` dışında hiçbir
  dosyada geçmiyor.
- Kimlik yalnız bu depoya (`git config` yerel): Mehmet + e-posta. 78 dosya, ~3,5 MB.

```
a12f624  Başlangıç: 8 Ekim hâli (bildirim öncesi)   ← pano.py bilerek ESKİ hâliyle
448506e  Adres değişince telefona ntfy bildirimi     ← bugünkü fark ayrı görünsün diye
d05da01  VS Code: markdown önerileri ayarı yeni biçime çevrildi
```

**Çalışma şekli:** Claude değiştirir → VS Code **Changes**'te görünür → Mehmet bakar →
kısa notla kayıt. Claude'un fark paneli YALNIZ kaydedilmemiş değişiklikleri gösteriyor,
geçmiş kayıtları değil ("No changes to show" bundandı).

### 84.4. VS Code
- **Masaüstü'nden** çalışıyor (`~/Desktop/Visual Studio Code.app`, 1.116); önce kurulum
  diskinin İÇİNDEN çalışıyordu (hiç kurulmamıştı). Uygulamalar'a taşınması ve diskin
  çıkarılması önerildi — disk hâlâ takılı (eski açılıştan kalan çökme raporlayıcısı
  tutuyor olabilir).
- Git görünümü: **View → Source Control** (⌃⇧G — Control, Command değil) → altta
  **Graph**. Kayda → dosyaya tıkla → eski/yeni yan yana. Git eklentisi depoyu tanıdı
  (Git.log 18:33). Proje güvenilir klasörler listesinde.
- VS Code'da ikinci bir pencere de açık: `Desktop/iett-projesi` — doğru pencerenin
  başlığında `otobus-takip` yazar.
- VS Code proje açılınca `.vscode/settings.json`'daki `quickSuggestions`'ı yeni biçime
  çevirdi (anlam aynı) → `d05da01`.

---

## 85. 📌 SİSTEMİN ŞU ANKİ HÂLİ (8 Ekim akşamı, devir özeti)

**Sunucu Mac'te kalıyor** (Bölüm 81). **Dokuz süreç — hepsi launchd'de:**
```
kaydedici.py        dakikada bir · 6.921 araç · kota 95/saat
gecis_dongusu.sh    10 dk · ham konumdan geçiş çıkarımı
duyuru_dongusu.sh   10 dk · sefer iptalleri
model_dongusu.sh    saat başı · havuz beslemesi + süre modeli
gps_dongusu.sh      10 dk · karanlık sefer iddiaları
arayuz_sunucu.py    port 8790 · anahtar · ızgara + önbellek · duran araç filtresi
cloudflared         internetten erişim tüneli (Bölüm 75)
gozcu_dongusu.sh    kaydedici + tünel nöbetçisi + ADRES PANOSU + bildirim (76, 82, 84)
sabah_rutini.sh     zamanlanmış (09:00) · sefer arşivi → dizin.db
```
8 Ekim 17:48 kontrol turu: dokuz servis ayakta · istek başarısı %100 · tünel 200,
anahtarsız 401 / anahtarlı 200 · `.local` 200 · panodaki 3 ilanın imzası doğru ·
durak isteği 0,16–0,41 sn · disk %21.

**Erişim — telefon bu sırayla dener:**
```
1. bu oturumda çalışan adres
2. ayarlardaki adres
3. http://Mehmet-MacBook-Air-2.local:8790   (ev ağı · IP değişse de sabit)
4. https://<değişken>.trycloudflare.com     (evdeyken öğrenilir)
5. ADRES PANOSU (ntfy.sh, imzalı) → yeni tünel adresi → bir kez daha
   her yerde X-Anahtar başlığı ZORUNLU (/saglik hariç)
```
**Bildirim:** tünel adresi değişince telefondaki ntfy uygulamasına haber gider (84) —
yalnız bilgi, uygulama adresi kendisi buluyor.

**Ekran doğruluğu:** gündüz gösterilen canlı araçların %96,5'i gerçekten yol
alıyor (79). Durak isteği ortanca 0,07 sn, en yavaş 1,8 sn (77, 80).

**Önemli dosya konumları:**
```
veri/kayit.db          9,7 GB · konum · geçiş · havuz
veri/dizin.db          ~460 MB · durak · hat · tarife · sefer arşivi (büyüyor)
veri/anahtar.txt       erişim anahtarı (izin 0600)
veri/pano_konu.txt     adres panosunun gizli adı (izin 0600)
veri/bildirim_konu.txt bildirim konusunun gizli adı (izin 0600) · telefon buna abone
veri/pano_son.json     son asılan adres + zaman
veri/tunel.log         güncel tünel adresi (servis her başlangıçta sıfırlar)
veri/gozcu.log         gözcünün müdahale kayıtları (📌 pano satırları dahil)
arac/cloudflared       tünel binary'si (38 MB · v2026.9.3)
pano.py                adres panosu (imzalı ilan) + bildirim · --dene
.gitignore             git dışı: veri/ · arac/ · sistem artıkları
~/Library/LaunchAgents/otobus.*.plist    dokuz servis tanımı
```

**Git:** yerel depo, `main` · her iş sonunda kısa notlu kayıt · uzak depo YOK (84.3).
Görmek için: VS Code → View → Source Control → Graph.

**Günlük kontrol:** `durum.sh` · `izle.sh` · `veri/gozcu.log`

**⚠️ Mac'in uyanık kalması ŞART** · **telefona yükleme kablo istiyor**
(`devicectl` kablo takılıyken de `available (paired)` gösterebilir — sonuca bak).

**🔜 Açık işler:**
- Veri bulunamayan hatlar durak ekranında HİÇ gösterilmiyor (gündüz %9 durak boş)
  — "bu saatte bilgi yok" soluk satırı önerildi, karar bekliyor.
  Örnek: **402031 KADIKÖY** — 1, 3, 12, 12A, 14C'nin İLK durağı, ekran tamamen boş
  (8 Ekim 17:50); bu hatlarda neden veri olmadığı henüz ölçülmedi
- Gösterilen hareketli araçların ~%20'si durağa gelmiyor (79.5)
- Bölüm 71 · şişkin hat ataması (21 hat) — "şimdilik kalsın"
- Kaydedicinin geri çekilme mantığı (kök sebep; gözcü semptomu çözüyor)
- `dizin.db` WAL'a alınması · duyuru kilitlenmesi (80.5 · son: 7 Ekim 04:05)
- `durum.sh` verim eşiği (8 Ekim: 0,55) · `parca_sure_ESKI` · peron beklemesi · `hayalet.py` duyuru
- Dizin eskimesi (130S, 14SB, 92S) · `filo_konum`'da ileri zaman damgaları

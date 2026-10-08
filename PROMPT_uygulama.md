# PROMPT — "Otobüsüm Nerede" Alternatifi Mobil Uygulama

> **Bu dosya nedir:** Mehmet'in anlattığı uygulama fikrinin, bir yapay zekâ asistanına
> (veya yeni bir seansa) tek seferde verilebilecek hâle getirilmiş tam tanımı.
> **Bu YENİ ve BAĞIMSIZ bir proje.** Seansın başında okunacak tek dosya budur.
> Kararlar netleştikçe burası güncellenir.
>
> **İETT arz-talep analizi projesiyle ilişkisi:** O proje **bitti**. Devamı değiliz.
> Ama sekiz seanslık teknik birikimi — hangi servis metodu çalışıyor, parametre adları
> ne, kota nerede kesiyor, hangi ölçümler yapıldı — bu uygulamanın en değerli başlangıç
> sermayesi. Bu dosyada o birikimin **yalnızca burada işe yarayan kısmı** taşındı;
> ayrıntısı gerekirse `Otobüs Takip Uygulaması PROJE DURUMU son durum.md` bir **başvuru kaynağı** olarak durur,
> bir görev listesi olarak değil.
>
> Oluşturulma: 26 Ağustos 2026

---

## 1. ÜRÜN TEK PARAGRAFTA

İstanbul'da toplu taşıma kullanan bir insanın durakta beklerken sorduğu tek soruya
dürüst cevap veren bir mobil uygulama: **"Otobüs gelecek mi, ne zaman gelecek?"**
Mevcut "Otobüsüm Nerede" uygulaması bu soruya yalnızca **GPS'i açık ve düzgün çalışan**
araçlar için cevap verebiliyor; geri kalan durumda ekran boş kalıyor ve yolcu
"sefer iptal mi, araç mı gözükmüyor" ayrımını yapamıyor. Bu uygulamanın varlık sebebi
tam olarak o boşluk: **araç görünmediğinde de bir şey söyleyebilmek.**

---

## 2. ÇÖZDÜĞÜ AN — SOMUT SENARYO (referans senaryo)

> 98 hattı Bakırköy'den 23:30'da kalkıyor. Sefaköy durağında bekleyen yolcu:
> - Durak ekranında hiçbir otobüs görünmüyor
> - "Otobüsüm Nerede"de de görünmüyor
> - Sebep: o aracın GPS'i kapalı, arızalı ya da sinyal vermiyor
> - **Yolcu bilmiyor:** sefer iptal mi oldu, yoksa otobüs yolda mı?

**Bu uygulamanın vermesi gereken cevap:**

```
98 · Bakırköy → Fenertepe
23:30 kalkışı  ·  konum bildirmiyor
Tahmini Sefaköy varışı: 23:52 – 23:58   (güven: orta)
Neden: aracın GPS'i görünmüyor; tahmin, tarife + bu saatte
       ölçülmüş gerçek sefer süresi + hattaki diğer araçların
       şu anki hızından üretildi.
```

Ya da, sinyaller iptali gösteriyorsa:

```
98 · 23:30 kalkışı  ·  büyük ihtimalle YAPILMADI  (güven: orta)
Sıradaki kalkış 23:50 · tahmini Sefaköy varışı 00:12
```

**Kritik ürün ilkesi:** Uygulama asla emin olmadığı şeyi emin gibi söylemez. Her cevap
bir **güven seviyesi** taşır. "Bilmiyorum" demek, yanlış söylemekten iyidir — çünkü bu
uygulamanın rakibine karşı tek gerçek kozu güvenilirliktir.

---

## 3. FARKLILAŞMA — ÜÇ MADDE

1. **Hayalet sefer tespiti.** Tarifede olup ekranda görünmeyen kalkışı fark eder,
   "iptal mi / GPS mi" ayrımını olasılıkla söyler. *(Kimse yapmıyor. Asıl fikir bu.)*
2. **GPS yokken de tahmin.** Tarife + ölçülmüş gerçek sefer süreleri + hattaki diğer
   araçlardan çıkarılan anlık hız ile varış aralığı üretir.
3. **Sadelik.** Tek ekranda tek cevap. Yolcu durakta, ayakta, tek elle, 3 saniyede
   okuyacak. Harita ikincil; **cevap cümlesi** birincil.

İkincil (öncelik 2): **mod öncelikli rota planlayıcı** — bkz. Bölüm 10.

---

## 4. ÖNCELİK 1 — "OTOBÜSÜM NEREDE" MOTORU

### 4.1. Sistemin cevaplaması gereken dört soru

| # | Soru | Hangi veriyle |
|---|---|---|
| S1 | Bu durağa hangi hatlar uğruyor, sıradaki planlı kalkışlar ne zaman? | `DurakDetay_GYY` + `GetPlanlananSeferSaati_json` |
| S2 | Şu an bu hatta yolda görünen araçlar nerede, hangi yönde? | `GetHatOtoKonum_json` (+ hareket vektöründen yön) |
| S3 | Görünen araç bu durağa kaç dakikada varır? | rota geometrisi üzerinde kalan mesafe ÷ ölçülmüş/anlık hız |
| S4 | **Tarifede olup görünmeyen kalkış ne oldu?** | hayalet sefer motoru — Bölüm 4.3 |

S1–S3 için gereken her şey elde ve çalıştığı doğrulanmış durumda. **Projenin yeni ve
zor kısmı S4.**

### 4.2. Temel kavram — "hayalet sefer"

**Hayalet sefer:** Tarifede yeri olan, kalkış saati geçmiş, ancak canlı konum
servisinde kendisine atfedilebilecek hiçbir araç bulunmayan sefer.

Bir hayalet seferin üç olası açıklaması var; ürünün işi bunları ayırmak:

| Açıklama | Yolcuya söylenecek |
|---|---|
| **A. İptal** — sefer hiç yapılmadı | "Bu kalkış büyük ihtimalle yapılmadı, sıradaki 23:50" |
| **B. GPS karanlığı** — araç yolda, sinyal yok | "Konum bildirmiyor; tahmini varış 23:52–23:58" |
| **C. Gecikmeli kalkış** — henüz kalkmadı | "Kalkış gecikmiş görünüyor; en erken 23:58" |

### 4.3. İptal / GPS ayrımı — kullanılabilecek sinyaller

Tek bir sinyal yeterli değil; **birden çok zayıf sinyalin birleşimi** gerekiyor:

1. **Arşiv görev kaydı** — `GetIettArsivGorev_json`, `SGOREVDURUM` alanı:
   `T` = tamamlandı (%95,4) · `I`/`YK`/`B` = iptal/yarım (%4,6). Bu **gerçeğin kaynağı**.
   ✅ **ÖLÇÜLDÜ (26 Ağustos 2026): arşiv ERTESİ GÜN geliyor.** Bugün soruldu → `[]` boş;
   dün → 51.764 kayıt, tam gün. Yani **canlı iptal bilgisi yok**; iptal anlık olarak
   *çıkarılmak* zorunda. Arşiv yalnızca **model eğitmek ve tahmini doğrulamak** için.
   Ayrıntı ve sayılar: `Otobüs Takip Uygulaması PROJE DURUMU.md` Bölüm 2.
2. **Hattaki araç sayısı** — o saatte tarife kaç araç gerektiriyor, canlıda kaç araç
   var? Fark büyükse iptal ihtimali artar.
3. **Aracın geçmişte kaybolup geri gelmesi** — kendi kaydedicimizin izinde araç
   daha önce görünüp sonra sustuysa, "GPS karanlığı" ihtimali artar (araç mevcut).
4. **Aşağı akışta yeniden belirme** — araç 10 dakika sonra rotanın ilerisinde
   belirirse, o sefer yapılmış demektir → geçmişe dönük etiket, model eğitimi için.
5. **Hat/saat/gün bazlı geçmiş iptal oranı** — 98 hattının 23:30 kalkışı son 30 günde
   kaç kez yapılmadı? Bu, **ön olasılık (prior)**.
6. **Hat/araç bazlı GPS karanlık oranı** — bazı araçların GPS'i kronik bozuk;
   bu da ayrı bir prior.

> **Yöntem önerisi:** Başlangıçta makine öğrenmesi değil, **açıklanabilir kural +
> olasılık tablosu**. Sebep: yolcuya "neden" cümlesi göstereceğiz; kara kutu bunu
> yapamaz. Yeterli etiketli veri biriktikten sonra (madde 4 ile otomatik etiketleniyor)
> lojistik regresyon gibi basit bir modele geçilebilir.

### 4.4. Varış tahmini — dört kademeli, her kademe bir öncekinin üstüne

| Kademe | Girdi | Ne zaman kullanılır |
|---|---|---|
| **v0 — Tarife** | planlanan kalkış + `SEFER_SURESI` | hiçbir şey bilinmiyorsa; en zayıf |
| **v1 — Ölçülmüş süre** | `cikti/gercek_sure_hat_saat.csv` (hat × saat gerçek süre) | GPS karanlığında ana yöntem |
| **v2 — Canlı otobüs-sensör** | aynı hattaki diğer araçların şu anki parça hızları | trafik anlık bozuksa v1'i düzeltir |
| **v3 — Şehir trafik indeksi** | `TrafficIndex` (1–99), genel çarpan | hatta hiç canlı araç yoksa v1'i düzeltir |

**Neden bu sıra doğru:** `gercek_sure_hat_saat.csv` zaten hat ve saat kırılımında
**gerçekleşmiş** süreleri taşıyor (tarife değil, ölçüm — Bölüm 6.9). Trafik indeksiyle
sefer süresi arasında **Spearman 0,759 · p = 0,00002** ölçüldü; yani indeks, hattı
görmeden bile anlamlı bir düzeltme çarpanı verir.

**Çıktı bir tek sayı değil, bir aralık olmalı** ("23:52–23:58"). Aralığın genişliği
güvenin görsel karşılığıdır. Tek sayı vermek, olmayan bir kesinlik iddiasıdır.

### 4.5. Hattaki mesafe hesabı

Araçtan durağa kuş uçuşu mesafe **kullanılmaz** — yol geometrisi üzerinde kalan mesafe
kullanılır. Bu iş için `cikti/rota_yollari.json` (676 hat, OSRM ile yola oturtulmuş
gerçek geometri) hazır. Araç, rota çizgisine izdüşürülür; durak da izdüşürülür; aradaki
yay uzunluğu alınır.
⚠️ 33 hatta OSRM sapması var (en kötüsü `11R`: API 18 km, çizim 45,8 km) — bu hatlarda
mesafe hesabı bozuk çıkar, tespit edilip elenmeli veya düzeltilmeli.

---

## 5. VERİ KAYNAKLARI

### 5.1. Elde olan ve çalıştığı DOĞRULANMIŞ kaynaklar

| Kaynak | Metot / dosya | Ne verir |
|---|---|---|
| Canlı araç konumu | `FiloDurum/SeferGerceklesme.asmx` → `GetHatOtoKonum_json` (`HatKodu`) | kapino, enlem, boylam, hatkodu, guzergahkodu, yon, son_konum_zamani, yakinDurakKodu |
| Şehir geneli filo | `GetFiloAracKonum_json` (parametresiz) | 6.911 araç tek istekte, **hız alanı dahil** — ama hat kodu YOK |
| Planlanan kalkışlar | `PlanlananSeferSaati.asmx` → `GetPlanlananSeferSaati_json` | SHATKODU, SYON, SGUNTIPI (I/C/P), DT ("06:15") — 130.435 kalkış |
| Durak listesi (sıralı) | `ibb/ibb.asmx` → `DurakDetay_GYY` (`hat_kodu`) | HATKODU, YON, SIRANO, DURAKKODU, DURAKADI, X/YKOORDINATI |
| Gerçekleşen seferler | `ibb/ibb360.asmx` → `GetIettArsivGorev_json` (`Tarih`, `yyyyMMdd`) | ~56.000 kayıt/gün, **`SGOREVDURUM` = iptal bilgisi** |
| Hat listesi | `GetHat_json` | 783 hat: kod, ad, tarife, uzunluk, sefer süresi |
| Trafik indeksi | `api.ibb.gov.tr/tkmservices/api/TrafficData/v1/TrafficIndex` | şehir geneli 1–99 tek sayı |
| Yola oturmuş rotalar | `cikti/rota_yollari.json` | 676 hat gerçek yol geometrisi |
| Durak koordinatları | `cikti/guzergahlar.json` | 676 hat, 55.564 durak |
| Ölçülmüş sefer süreleri | `cikti/gercek_sure_hat_saat.csv` · `gercek_sure_hat.csv` | hat × saat gerçek süre + gözlem sayısı |

### 5.2. Henüz denenmemiş, denenmesi gereken metotlar

`GetDuyurular_XML` *(iptal duyuruları burada olabilir — yüksek değerli)* ·
`GetPlanaUyum_json` *(plana uyum = iptal/gecikme ölçüsü olabilir — yüksek değerli)* ·
`GetSeferZayi_json` *("zayi" = kayıp sefer? isim çok umut verici)* ·
`GetOtsPlanlananKm_json` · `GetKaraKutu_json`

> **Tam metot listesi WSDL'den okunur:** `GET .../<yol>.asmx?wsdl`.
> `SeferGerceklesme.asmx`'te 36 metot tanımlı, çoğu geçitte kapalı.
> Doküman güvenilmez — parametre adları da WSDL'den okunmalı.

### 5.3. Rota planlayıcı için gereken, HENÜZ ELDE OLMAYAN kaynaklar

- **Metro / tramvay / Marmaray / füniküler tarifeleri ve hatları** — İETT servisi
  yalnızca otobüs. Metro İstanbul ve İBB açık verisinde GTFS aranmalı.
- **Metrobüs** — İETT kodlarında var (`34, 34A, 34AS, 34B, 34BZ, 34C, 34G, 34Z`) ama
  tarifesi gerçeği yansıtmıyor (Bölüm 6.7); ayrı ele alınmalı.
- **Vapur / deniz otobüsü** (Şehir Hatları, İDO) — İstanbul için gerçek bir seçenek.

---

## 6. BİLİNEN KISITLAR — MİMARİYİ BUNLAR BELİRLİYOR

1. **⚠️ KOTA.** ~86 ardışık istekten sonra `Policy Falsified / Rate limit exceeded`
   (HTTP 500 gövdesinde yazıyor). 3 dakikada açılmadı. **Blokluyken yoklamak cezayı
   uzatıyor** — tamamen susmak gerekiyor.
   → **Sonuç: telefonlar İETT'ye doğrudan bağlanamaz.** Araya kendi sunucumuz girmek
   zorunda. Bu bir tercih değil, zorunluluk.
2. **Canlı servis dakikada bir tazeleniyor** — yeni veri her dakikanın ~5. saniyesinde.
   Daha sık sormak boşa istek. Yoklama periyodu buna göre kurulmalı.
3. **Geçmiş GPS izi YOK.** Servis yalnızca "şu an"ı veriyor. Hayalet sefer tespiti de,
   parça hız modeli de geçmiş iz istiyor. → **Kaydedici yazmak ilk iş.**
4. **Yol bazında canlı trafik verisi açık veride YOK.** `TrafficDensity`, `RoadTraffic`,
   `Announcement` denendi, hepsi 404. `uym.ibb.gov.tr` bir web sayfası, API değil.
   → Yol bazlı trafiği **otobüslerin kendisinden** çıkarmak zorundayız (zaten çalışıyor).
5. **CORS.** Tarayıcı İETT SOAP servisine doğrudan bağlanamıyor (POST 200 ama başlık yok,
   OPTIONS 500). `11_canli_kopru.py` bu sorunu zaten çözüyor — yeni backend'in temeli olabilir.
6. **Yön bilgisi kırılgan.** Kaynak veride 103 hatta yön yok/yanlış. Çözüm üç kademeli
   ve çalışıyor: (1) hareket vektörü, (2) `guzergahkodu` orta harfi, (3) durak adı eşleme.
7. **TLS tuzağı.** macOS Python 3.9 + LibreSSL 2.8.3 → bazı dış servislerde
   "sslv3 alert handshake failure". Çözüm: o isteği `curl` ile atmak. İBB adresleri etkilenmiyor.

---

## 7. MİMARİ TASLAK

```
   İETT / İBB servisleri
            │  (dakikada bir, kotaya saygılı, TEK noktadan)
            ▼
   ┌──────────────────┐
   │  KAYDEDİCİ       │  sürekli çalışır, her ölçümü saklar
   │  (collector)     │  → araç izleri, hat bazlı zaman serisi
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │  VERİTABANI      │  araç izleri · parça hızları · tarife ·
   │                  │  gerçekleşen seferler · iptal etiketleri
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │  TAHMİN MOTORU   │  hayalet sefer tespiti + varış tahmini
   │                  │  + güven seviyesi
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │  API             │  /durak/{kod}  → sıradaki varışlar + güven
   │                  │  /hat/{kod}    → canlı araçlar + hayalet seferler
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │  MOBİL UYGULAMA  │  tek ekran, tek cevap
   └──────────────────┘
```

**Kaydedici neden ilk iş:** Hayalet sefer tespiti "geçmişte bu araç görünüyor muydu",
"bu kalkış geçen hafta kaç kez yapılmadı" sorularına cevap ister. Bu veri **birikmeye
başlamadan** hiçbir model kurulamaz. Kaydedici bugün başlarsa, model iki hafta sonra
eğitilebilir hâle gelir. Bir gün geç başlamak, bir gün geç bitirmek demektir.

---

## 8. DOĞRULAMA PLANI — pazarlıksız

Bu uygulamanın tek satış noktası doğruluk. O yüzden **her tahmin kaydedilir ve sonradan
gerçekle karşılaştırılır**:

- Her verilen tahmin (hat, durak, saat, tahmini aralık, güven) veritabanına yazılır.
- Ertesi gün `GetIettArsivGorev_json` ile o seferin gerçekten olup olmadığı öğrenilir.
- Ölçülen metrikler: **iptal tespitinde isabet** (kaç doğru, kaç yanlış alarm) ve
  **varış tahmininde sapma** (dakika cinsinden ortalama mutlak hata).
- Hedef bir sayı değil, bir eğri: hata zamanla düşmeli. Düşmüyorsa model yanlıştır.

⚠️ **Yanlış alarm, sessiz kalmaktan daha zararlıdır.** "Sefer iptal" deyip otobüs
gelirse yolcu bir daha o uygulamayı açmaz. Eşikler bu asimetriyi gözeterek seçilmeli.

---

## 9. İLK BEŞ ADIM (somut, sırayla)

1. **Kaydediciyi yaz ve çalıştır.** Seçilen 3–5 hat için (98 dahil — referans senaryo)
   dakikada bir konum çek, hepsini sakla. Kotaya saygılı. Bugün başlasın.
2. **`GetIettArsivGorev_json` tazeliğini ölç.** Bugünün seferleri kaç saat sonra
   arşivde beliriyor? Bu ölçüm, S4'ün ne kadarının çözülebileceğini belirler.
3. **Denenmemiş metotları dene:** `GetDuyurular_XML`, `GetPlanaUyum_json`,
   `GetSeferZayi_json`. Parametre adları WSDL'den okunsun.
4. **Tek hatta, tek durakta hayalet sefer tespitini elle kur.** 98 / Sefaköy /
   23:30. Otomatikleştirmeden önce senaryonun kendisi çalışsın.
5. **En kaba arayüz:** tek durak, sıradaki üç varış, güven seviyesi. Güzel olmasın,
   doğru olsun.

> Rota planlayıcı (Bölüm 10) bu beş adım bitmeden **başlamaz**. İki büyük problemi
> paralel yürütmek ikisini de yarım bırakır.

---

## 10. ÖNCELİK 2 — MOD ÖNCELİKLİ ROTA PLANLAYICI

### 10.1. Problem

Google Maps İstanbul'da çoğu zaman metro/metrobüs ile daha kısa ve rahat gidilebilecek
güzergâhlarda otobüs öneriyor; metrobüsü nadiren gösteriyor. Sebep genelde şu:
klasik rota motorları **beklenen toplam süreyi** en küçüklüyor ve otobüs tarifesini
olduğu gibi doğru kabul ediyor. Oysa İstanbul'da otobüs süresi **oynak**, ray sistemi
**öngörülebilir**.

### 10.2. Çözüm fikri — süre değil, "algılanan maliyet"

Rota motorunun en küçüklediği şey değişmeli:

```
maliyet = yürüme × a
        + bekleme × b
        + araç_içi_süre × mod_katsayısı(mod)
        + aktarma_sayısı × c
        + süre_belirsizliği × d          ← asıl fark burada
```

- `mod_katsayısı`: metro/tramvay/Marmaray < metrobüs < otobüs.
  Aynı 20 dakika, metroda otobüsteki 20 dakikadan **daha ucuz** sayılır — çünkü
  daha öngörülebilir ve daha rahat.
- `süre_belirsizliği`: her hat için **ölçülmüş** süre değişkenliği. Bu veri elimizde
  var — `gercek_sure_hat_saat.csv` gözlem sayısıyla birlikte geliyor, dolayısıyla
  hat bazında yayılım hesaplanabilir. **Bu, rakiplerin sahip olmadığı girdi.**
- Katsayılar **ayarlanabilir** olmalı; "en hızlı" / "en az aktarma" / "en rahat"
  seçenekleri aslında aynı motorun farklı katsayı setleri.

### 10.3. Teknik gereksinim

- Ray sistemleri + vapur için **GTFS** verisi bulunmalı (Bölüm 5.3).
- Rota motoru: hazır bir motor (OpenTripPlanner gibi) mod katsayılarıyla ayarlanabilir mi,
  yoksa GTFS üzerinde kendi arama algoritmamızı mı yazacağız? **Karar verilmedi.**
  Öğrenme amacı ağır basıyorsa ikincisi daha öğretici; hız amacı ağır basıyorsa birincisi.

---

## 11. TEKNOLOJİ VE ARAÇLAR

### 11.1. Karar verilmemiş, karar gerektiren

| Konu | Seçenekler | Not |
|---|---|---|
| **Mobil taraf** | (a) PWA — mevcut `mobil.html` yaklaşımının devamı · (b) React Native / Expo · (c) Flutter | (a) en hızlı yol, elde çalışan örnek var; (b) gerçek uygulama mağazası hedefi varsa |
| **Backend** | FastAPI (Python) | Mehmet Python biliyor; `11_canli_kopru.py` zaten yarı yolda |
| **Veritabanı** | (a) SQLite · (b) PostgreSQL + TimescaleDB · (c) DuckDB | Zaman serisi ağırlıklı; başlangıçta SQLite yeter |
| **Barındırma** | yerel · ucuz VPS · bulut | Kaydedicinin 7/24 çalışması gerekiyor — laptop yetmez |

### 11.2. VS Code eklentileri

**Zaten kurulu:** Python, Jupyter

**Kurulması önerilenler:**

| Eklenti | Ne işe yarar |
|---|---|
| **Data Wrangler** (Microsoft) | DataFrame'i tablo olarak gezme, filtreleme, temizleme — yaptığın her adımın pandas kodunu üretir. Veri keşfi için en yüksek getirili eklenti. |
| **SQLite Viewer** | Kaydedicinin veritabanını tıklayıp içine bakmak |
| **Thunder Client** veya **REST Client** | SOAP/REST isteklerini VS Code içinden deneme — yeni metot denerken şart |
| **Ruff** | Python linter/formatter, hızlı |
| **GitLens** | Git geçmişini satır satır görme |
| **Rainbow CSV** | CSV sütunlarını renklendirir, ham dosyaya bakarken |
| **Error Lens** | Hatayı satırın yanında gösterir |
| **XML Tools** | SOAP cevaplarını okunur biçimde biçimlendirme |

Mobil tarafa göre ek: **ES7+ React snippets** + **Prettier** (React Native seçilirse),
veya **Flutter** + **Dart** (Flutter seçilirse).

**Python paketleri (yeni):** `fastapi`, `uvicorn`, `httpx`, `apscheduler` (zamanlanmış
yoklama için), `shapely` (rota izdüşümü ve mesafe için).

⚠️ **Python 3.9.6 kısıtı.** Mevcut venv 3.9. Bazı modern paketler 3.10+ istiyor.
Yeni proje için ayrı ve daha güncel bir venv kurmak mantıklı olabilir — ama bu,
mevcut analiz projesinin ortamına **dokunmadan** yapılmalı.

---

## 12. AÇIK KARARLAR — Mehmet verecek

1. Yeni proje klasörünün adı ve yeri. (Öneri: `Desktop/` altında ayrı bir klasör —
   eski projenin `venv`'i, verisi ve betikleri karışmasın. Eski `cikti/` klasöründen
   yalnızca üç dosya kopyalanır: `rota_yollari.json`, `guzergahlar.json`,
   `gercek_sure_hat_saat.csv`.)
2. Mobil taraf: PWA mı, React Native mi?
3. Kaydedici nerede sürekli çalışacak?
4. Rota planlayıcı: hazır motor mu, kendi algoritmamız mı?
5. Kaç hatla başlıyoruz? (Öneri: 98 + 500T + 2–3 hat. Tüm şehir kotayı yakar.)

---

## 13. ÇALIŞMA KURALLARI (eski projeden aynen geçerli)

- **Kodu Mehmet yazar.** Asistan `.py` / `.ipynb` dosyası **oluşturmaz**; ne yazılacağını
  ve **neden** yazılacağını anlatır, Mehmet yapıştırıp çalıştırır.
  İstisna: `.md` dosyaları ve arayüz HTML/CSS/JS — bunlar da yazıldıktan sonra anlatılır.
- Her kod bloğunun altına `>` ile 1–2 cümlelik dipnot: **ne yapıyor, neden gerekli.**
- Mesajlar kısa, tek seferde tek konu.
- Amaç **öğrenmek**; bitmiş ürün ikincil.

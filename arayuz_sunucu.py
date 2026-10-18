"""
SUNUCU — arayüzün arka ucu. Motoru JSON'a çevirir.

⚠️ SADECE TEK DOSYA SUNAR (arayuz.html). Klasörün tamamı sunulmuyor — `veri/`
   içinde 4 GB'lık veritabanı var, ağa açılması istenmez.

ÇALIŞTIRMA:
    cd "/Users/mehmetkucukbirer/otobus-takip"
    python3 arayuz_sunucu.py

  Sonra tarayıcıda:  http://localhost:8790
  Telefondan       :  http://<bilgisayarın-yerel-IP>:8790
                      (IP için: ipconfig getifaddr en0)

UÇ NOKTALAR:
    /                      arayüz
    /api/ara?q=sefaköy     durak adı arama
    /api/yakin?e=&b=       konuma en yakın duraklar
    /api/durak?kod=124081  o durakta ne var — ASIL CEVAP
"""

import hmac
import json
import math
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

import durakta_ne_var as DNV
import duyurular
import hayalet
import rota

# ⭐ SUNUCUYA ÖZEL İZDÜŞÜM ÖNBELLEĞİ (7 Ekim) — gündüz yavaşlığına ikinci katman.
#   Uygulama 30 sn'de bir yeniliyor ve farklı duraklar aynı hatları paylaşıyor;
#   bir aracın iz noktaları ardışık isteklerde büyük ölçüde AYNI kayıtlar. Aynı
#   girdi → aynı çıktı, dolayısıyla sonuç kesin; ölçüm (6 Ekim gündüz yükü):
#       ızgara              0,40 sn/istek
#       ızgara + önbellek   0,21 sn/istek (tekrar isteklerde)
#   ⚠️ YALNIZ SUNUCUDA: geçiş çıkarımı (gecisler.py) şehrin tamamını tarıyor,
#   orada isabet oranı düşük olur ve önbellek sadece bellek yerdi. Bu yüzden
#   rota.py'nin kendisine değil, sunucu açılırken buraya konuldu. Tüm
#   çağıranlar `rota.yol_uzerinde(...)` biçiminde çağırdığı için hepsine ulaşıyor.
#   Dönüş değeri değiştirilemez demet — paylaşılması güvenli. ~25 MB üst sınır.
rota.yol_uzerinde = lru_cache(maxsize=100_000)(rota.yol_uzerinde)
import sure_modeli
import yon_tespit

VERI = KOK / "veri"
PORT = 8790

# ⚠️ TARİFE UFKU — 31 Ağustos'ta simülatörde görülerek eklendi.
#   98'in D yönünde gündüz tarifesi YOK (gidiş+dönüş varyantına yazılıyor), bu yüzden
#   "sıradaki kalkış 23:00" çıkıyor ve ekranda "429 DAKİKA" yazıyordu. Teknik olarak
#   doğru ama yolcuya faydasız. Bu ufkun ötesindeki tarife satırları gösterilmiyor;
#   yerine GÖZLEMDEN sıradaki geçiş tahmin ediliyor.
TARIFE_UFKU_DK = 120
#: İptal duyurusu için ufuk — gerekçesi iptal bloğunda (7 Ekim).
IPTAL_UFKU_DK = 360

# Hava durumu — sahadaki durak ekranında da sıcaklık gösteriliyor.
# open-meteo ücretsiz ve anahtar istemiyor. Durak koordinatına göre sorulur,
# şehir ölçeğinde değişim yavaş olduğu için 10 dakika önbellekte tutulur.
HAVA_ONBELLEK_DK = 10
_hava_onbellek = {}
SAYFA = KOK / "arayuz.html"


import threading
# ⚠️⚠️ ÇÖKMENİN KÖKÜ — İŞ PARÇACIĞI BAŞINA BAĞLANTI (4 Eylül)
#
#   Önceki sürüm tek bir SQLite bağlantısını tüm iş parçacıklarıyla paylaşıyordu:
#       with _kilit:                     ← kilit YALNIZCA bağlantı kurulurken
#           ...
#           return b                     ← kilit burada bırakılıyor
#   Kilit yalnızca oluşturmayı koruyordu; SORGULARI korumuyordu. Sunucu
#   ThreadingHTTPServer olduğu için her istek ayrı iş parçacığında koşuyor ve
#   iki istek çakıştığında aynı bağlantı üzerinde eşzamanlı execute() oluyordu.
#   `check_same_thread=False` Python'un uyarısını susturur, veri yarışını değil.
#   SQLite'ın dahili durumu bozulunca süreç SIGBUS ile SESSİZCE ölüyordu —
#   Bölüm 61 madde 6'daki "-10 (SIGBUS)" tam olarak buydu.
#
#   Eski yorum thread-local'dan "her seferinde yeniden kuruluyordu" diye vazgeçmiş.
#   ÖLÇÜLDÜ (4 Eylül): bağlantı açmak dizin.db'de 0,069 ms, kayit.db'de 0,143 ms.
#   Bir durak cevabı ~170 ms sürüyor — yani kaçınılan maliyet binde bir. O binde
#   bir için sessiz çökme riski alınmış. Artık her iş parçacığı kendi bağlantısını
#   kullanıyor: paylaşım yok, yarış yok, kilide de gerek yok.
_yerel = threading.local()


def _dizin():
    """Salt okunur referans veritabanı — iş parçacığı başına bir bağlantı."""
    b = getattr(_yerel, "dizin", None)
    if b is None:
        b = sqlite3.connect(str(VERI / "dizin.db"), timeout=20)
        b.execute("PRAGMA busy_timeout=20000")
        _yerel.dizin = b
    return b


# ⚠️ SQLite'ın NOCASE'i yalnızca ASCII harfleri katlar: "ö" ile "Ö" eşleşmez.
#    Türkçe durak adlarında arama bu yüzden hiç sonuç vermiyordu. Hem büyük/küçük
#    hem de Türkçe harfleri ASCII'ye indiren ayrı bir arama sütunu kullanılıyor —
#    böylece kullanıcı "sefakoy" yazınca da "SEFAKÖY MERKEZ" bulunur.
_KATLAMA = str.maketrans({"ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i",
                          "İ": "i", "ö": "o", "Ö": "o", "ş": "s", "Ş": "s",
                          "ü": "u", "Ü": "u", "â": "a", "î": "i", "û": "u"})


def katla(s):
    return " ".join((s or "").translate(_KATLAMA).lower().split())


#: Dizindeki ilçe adları Türkçe karakter kaybetmiş geliyor ("Bakirköy",
#: "Bagcilar", "Sisli"). Kaynak İETT verisi; düzeltme gösterim katmanında.
#: Listede olmayan bir ilçe gelirse olduğu gibi geçer.
ILCE_DUZELT = {
    "ADALAR": "Adalar", "Atasehir": "Ataşehir", "Avcilar": "Avcılar",
    "Bagcilar": "Bağcılar", "Bakirköy": "Bakırköy", "Basaksehir": "Başakşehir",
    "Bayrampasa": "Bayrampaşa", "Besiktas": "Beşiktaş", "Beyoglu": "Beyoğlu",
    "Gaziosmanpasa": "Gaziosmanpaşa", "Kadiköy": "Kadıköy", "Kagithane": "Kağıthane",
    "Sariyer": "Sarıyer", "Sile": "Şile", "Sisli": "Şişli", "Çayirova": "Çayırova",
}


def ilce_adi(i):
    i = (i or "").strip()
    return ILCE_DUZELT.get(i, i)


def _hat_ozetleri(d, kodlar, en_fazla=6):
    """Durağın hatları, doğal sırayla (89, 89A, 98, 141M …)."""
    if not kodlar:
        return {}
    yer = ",".join("?" * len(kodlar))
    hatlar = {}
    for kod, hat in d.execute("SELECT DISTINCT durak_kodu, hat_kodu FROM hat_durak"
                              " WHERE durak_kodu IN (%s)" % yer, list(kodlar)):
        hatlar.setdefault(kod, set()).add(hat)

    def dogal(h):
        bas = len(h) - len(h.lstrip("0123456789"))
        return (int(h[:bas]) if bas else 10**6, h[bas:], h)
    return {k: sorted(v, key=dogal)[:en_fazla] for k, v in hatlar.items()}


def _ayirici_yon_sirasi(d, satirlar, ozet):
    """Her durağın yön listesini, AYNI ADLI KARDEŞLERİNDE OLMAYAN yön başa gelecek
    şekilde yeniden sıralar.

    ⭐ NEDEN (7 Ekim, Mehmet: *"durakların konumu hangi durak olduğu aramada çok
    ayırt edici değil"*). Ölçüldü — 13.196 durağın 11.539'u (%87) adını başka
    bir durakla paylaşıyor ("ATATÜRK CADDESİ" 33 ayrı durak). Ekran tek satırda
    yön gösteriyor; hangi yönün gösterildiği belirleyici:

        ad + İLK yön (en çok hattın gittiği)   karışan %5,6 · 742 durak
        ad + AYIRT EDİCİ yön                    karışan %1,7 · 227 durak
        ad + TÜM yönler (satıra sığmaz)         karışan %1,5

    Karşılıklı iki durak çoğu zaman ortak bir yönü paylaşır (ikisinden de geçen
    bir ring hattı gibi); ilk yön o ortak yön olunca ikisi ekranda ÖZDEŞ görünür.
    Kardeşlerde bulunmayan yönü öne almak tek satırla neredeyse tüm ayrımı veriyor.

    ⚠️ Kardeşler GLOBAL hesaplanıyor (aynı adlı TÜM duraklar), yalnız sonuç
    listesindekiler değil: 25 sonuç sınırında bir kardeş kesilmiş olabilir, ama
    global olarak benzersiz olan yön sonuç listesinde de benzersizdir.
    """
    adlar = list({a for _, a, *_ in satirlar})
    if not adlar:
        return ozet
    yer = ",".join("?" * len(adlar))
    kardes_yon = {}       # ad → {durak_kodu: {yönler}}
    for kod, ad, yon_adi in d.execute(
            "SELECT d.durak_kodu, d.durak_adi, h.yon_adi FROM durak d"
            " JOIN hat_durak h ON h.durak_kodu = d.durak_kodu"
            " WHERE d.durak_adi IN (%s)" % yer, adlar):
        y = (yon_adi or "").strip()
        if len(y) > 22:
            y = y[:22].rstrip(" .,-") + "…"
        kardes_yon.setdefault(ad, {}).setdefault(kod, set()).add(y)
    yeni = {}
    for kod, ad, *_ in satirlar:
        liste = ozet.get(kod, [])
        baskalari = set()
        for k2, ys in kardes_yon.get(ad, {}).items():
            if k2 != kod:
                baskalari |= ys
        ozel = [y for y in liste if y not in baskalari]
        yeni[kod] = ozel + [y for y in liste if y not in ozel]
    return yeni


def _yon_ozetleri(d, kodlar, en_fazla=3):
    """Durakların "nereye gidiyor" özeti. Tek sorgu — durak başına ayrı sorgu yok.

    ⚠️ NEDEN VAR (4 Eylül, Mehmet'in tespiti): arama "sefaköy" için dört ÖZDEŞ
       satır döndürüyordu — aynı ad, aynı ilçe, farklı kod. Yolcu hangisini
       seçeceğini bilemiyor, çünkü ekranda durakları ayırt eden hiçbir şey yok.

       Oysa veri ayrımı zaten taşıyor:
           122621 → hatların HEPSİ G yönünde (Bakırköy'e doğru)
           122622 → hatların HEPSİ D yönünde (Beylikdüzü'ne doğru)
       Durak kodunun son hanesi de bunu kodluyor (…1 / …2), ama "1" ya da "2"
       yolcuya hiçbir şey söylemez. Söyleyen tek şey: hattın NEREYE gittiği.

    ⚠️ `yon_adi` kaynak veride kirli — başında/sonunda boşluk var ve aynı hedef
       iki farklı yazımla geliyor ("BAKIRKÖY " ve "BAKIRKÖY"). strip sonrası
       Python tarafında toplanıyor; SQL'de GROUP BY yapmak onları ayrı sayardı.
    """
    if not kodlar:
        return {}
    yer = ",".join("?" * len(kodlar))
    sayac = {}
    for kod, yon_adi, n in d.execute(
            "SELECT durak_kodu, yon_adi, COUNT(*) FROM hat_durak"
            " WHERE durak_kodu IN (%s) GROUP BY durak_kodu, yon_adi" % yer, list(kodlar)):
        ad = (yon_adi or "").strip()
        if not ad:
            continue
        if len(ad) > 22:                       # ekranda tek satıra sığsın
            ad = ad[:22].rstrip(" .,-") + "…"
        s = sayac.setdefault(kod, {})
        s[ad] = s.get(ad, 0) + n
    return {kod: [a for a, _ in sorted(s.items(), key=lambda kv: (-kv[1], kv[0]))[:en_fazla]]
            for kod, s in sayac.items()}


def durak_ara(q, limit=25, enlem=None, boylam=None):
    """Durak adı araması.

    ⭐ 7 Ekim: kullanıcının konumu gelirse her sonuca uzaklık eklenir ve aynı
    uzunluktaki adlar (yani aynı adlı kardeşler) EN YAKINDAN uzağa sıralanır.
    "ATATÜRK CADDESİ" 33 durak — yolcunun aradığı neredeyse her zaman kendine
    en yakın olanı. Ayrıca ilçe Türkçe, hatlar ve ayırt edici yön eklendi
    (gerekçe `_ayirici_yon_sirasi`).
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    d = _dizin()
    konum_var = enlem is not None and boylam is not None
    # ⚠️ Konum varken SQL'de geniş al: LENGTH sırasıyla 25'te kesilirse aynı
    #    uzunluktaki 33 kardeşten en yakını kesilmiş olabilirdi.
    satir = d.execute("""
        SELECT durak_kodu, durak_adi, ilce, enlem, boylam,
               (SELECT COUNT(DISTINCT hat_kodu) FROM hat_durak WHERE durak_kodu=d.durak_kodu)
        FROM durak d
        WHERE ad_arama LIKE ?
        ORDER BY LENGTH(durak_adi) LIMIT ?""",
        ("%" + katla(q) + "%", 400 if konum_var else limit)).fetchall()

    def uzaklik(e, b):
        if not konum_var or e is None or b is None:
            return None
        return round(math.hypot((e - enlem) * 111000, (b - boylam) * 83000))

    if konum_var:
        satir.sort(key=lambda r: (len((r[1] or "").strip()), uzaklik(r[3], r[4]) or 10**9))
        satir = satir[:limit]
    ozet = _ayirici_yon_sirasi(d, satir, _yon_ozetleri(d, [r[0] for r in satir]))
    hatlar = _hat_ozetleri(d, [r[0] for r in satir])
    # ⚠️ Adın içindeki çift boşluk kaynak veride ("SEFAKÖY  MERKEZ") — gösterimde
    #    tekleniyor. Gruplama (`_ayirici_yon_sirasi`) ham adla yapıldığı için etkilenmez.
    return [{"kod": k, "ad": " ".join((a or "").split()), "ilce": ilce_adi(i),
             "enlem": e, "boylam": b, "hat_sayisi": n,
             "uzaklik_m": uzaklik(e, b),
             "hatlar": hatlar.get(k, []),
             "yonler": ozet.get(k, [])}
            for k, a, i, e, b, n in satir]


def yakin_duraklar(enlem, boylam, limit=12):
    """Konuma en yakın duraklar. Kaba kutu ile süzüp sonra sıralıyoruz."""
    d = _dizin()
    pay = 0.012                       # ~1,3 km
    satir = d.execute("""
        SELECT durak_kodu, durak_adi, ilce, enlem, boylam,
               (SELECT COUNT(DISTINCT hat_kodu) FROM hat_durak WHERE durak_kodu=d.durak_kodu)
        FROM durak d WHERE enlem BETWEEN ? AND ? AND boylam BETWEEN ? AND ?""",
        (enlem - pay, enlem + pay, boylam - pay, boylam + pay)).fetchall()
    out = []
    for k, a, i, e, b, n in satir:
        if e is None or b is None:
            continue
        m = math.hypot((e - enlem) * 111000, (b - boylam) * 83000)
        out.append({"kod": k, "ad": (a or "").strip(), "ilce": ilce_adi(i),
                    "enlem": e, "boylam": b, "hat_sayisi": n, "uzaklik_m": round(m)})
    out.sort(key=lambda x: x["uzaklik_m"])
    out = out[:limit]
    # ⚠️ Özet, kırpmadan SONRA — 12 durak için sorulur, kutudaki yüzlercesi için değil.
    ozet = _yon_ozetleri(d, [x["kod"] for x in out])
    hatlar = _hat_ozetleri(d, [x["kod"] for x in out])
    for x in out:
        x["yonler"] = ozet.get(x["kod"], [])
        x["hatlar"] = hatlar.get(x["kod"], [])
    return out



# ─────────────────────────────────────────────────────────────────────────────
# ⭐ ŞEHİR TRAFİK İNDEKSİ (10 Eylül)
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ Bu kaynak 26 Ağustos'ta ölçülmüştü (PROMPT Bölüm 4.4): trafik indeksi ile
#    sefer süresi arasında Spearman 0,759 · p = 0,00002. Yani anlamlı. Ama iki
#    haftadır KODA HİÇ GİRMEMİŞTİ — ölçüldü, not edildi, unutuldu.
#
# ⚠️ Bu ŞEHİR GENELİ tek sayı (0-100), yol bazlı değil. Yol bazlı canlı trafik
#    açık veride yok (Bölüm 6/4: TrafficDensity, RoadTraffic, Announcement → 404).
#    Tahmine girmiyor — tahmin zaten otobüslerin kendi ölçülmüş hızından geliyor,
#    ki o daha doğrudan bir sinyal. Bu sayı yolcuya BAĞLAM veriyor:
#    "20 dakika normalden uzun mu?" sorusunun cevabı.

TRAFIK_URL = "https://api.ibb.gov.tr/tkmservices/api/TrafficData/v1/TrafficIndex"
TRAFIK_ONBELLEK_DK = 5
_trafik_onbellek = {}


def trafik_indeksi():
    """İstanbul geneli trafik yoğunluğu (0-100) → {"deger": int, "durum": str} | None

    ⚠️⚠️ BEKLETMEZ (7 Ekim) — hava_durumu ile aynı gerekçe, ama burada risk daha
    büyüktü: eski sürüm HATA durumunda önbelleğe hiçbir şey yazmıyordu. Trafik
    servisi aksarsa HER durak isteği 8 sn zaman aşımını bekleyecekti. Artık
    önbellekteki (bayat bile olsa) değer hemen döner, tazeleme arka planda.
    """
    kayit = _trafik_onbellek.get("t")
    if not (kayit and (datetime.now() - kayit[0]).total_seconds() < TRAFIK_ONBELLEK_DK * 60):
        _arka_planda(("trafik",), _trafik_getir)
    return kayit[1] if kayit else None


def _trafik_getir():
    """Dış servisten trafik indeksini çeker ve önbelleğe yazar (arka planda)."""
    simdi = datetime.now()
    eski = _trafik_onbellek.get("t")
    try:
        # ⚠️ `Accept` BAŞLIĞI ŞART (10 Eylül'de bulundu): başlıksız istekte servis
        #    XML döndürüyor (<ResponseTrafficIndex xmlns=...>), curl'e ise JSON.
        #    İlk sürüm XML'i json.loads'a veriyor, hata yutuluyor ve trafik
        #    sessizce "—" görünüyordu. Aynı uç nokta, iki farklı biçim.
        istek = urllib.request.Request(TRAFIK_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(istek, timeout=8) as c:
            ham = c.read().decode("utf-8")
        try:
            v = json.loads(ham).get("Result")
        except ValueError:
            # Yine de XML geldiyse: <Result>49</Result> içinden sayıyı al.
            import re
            m = re.search(r"<Result>(\d+)</Result>", ham)
            v = m.group(1) if m else None
        if v is None:
            raise ValueError("trafik değeri yok")
        v = int(v)
        # ⚠️ Eşikler İBB'nin kendi ölçeğinden: uygulamalarında yeşil/sarı/kırmızı
        #    bantları bu civarda. Kesin bir kaynak yok, o yüzden sayı da
        #    gösteriliyor — yolcu kendi yorumunu yapabilsin.
        durum = "akıcı" if v < 40 else ("yoğun" if v < 65 else "çok yoğun")
        _trafik_onbellek["t"] = (simdi, {"deger": v, "durum": durum})
    except Exception:
        # ⚠️ Hata da önbelleğe yazılıyor (eski değer korunarak) — yoksa servis
        #    aksadığında her istek yeniden denerdi. Trafik yoksa uygulama çalışır.
        _trafik_onbellek["t"] = (simdi, eski[1] if eski else None)


def arac_detay(kapino, hat, yon, durak_kodu=None):
    """Bir aracın ŞU AN nerede olduğu ve nereye gittiği.

    ⭐ NEDEN VAR (10 Eylül, Mehmet'in isteği):
      *"sefaköy ht20 otobüsü 10 dk'ya gelicek, üstüne tıklayınca anlık olarak
        hangi duraktan nereye hareket ediyor onu göster"*

    Ekrandaki "5 dk" tek başına bir iddia. Bu ekran o iddiayı DAYANAĞIYLA
    gösteriyor: otobüs şu an nerede, en son hangi duraktan geçti, yolcunun
    durağına kaç durak kaldı. Yolcu böylece tahmine kendi güvenini kurabiliyor.
    """
    k = DNV._kayit_db()
    if k is None:
        return None
    d = _dizin()

    son = k.execute("SELECT zaman, enlem, boylam, hiz FROM filo_konum"
                    " WHERE kapino=? ORDER BY zaman DESC LIMIT 1", (kapino,)).fetchone()
    if not son or son[1] is None:
        return None
    an = datetime.now()
    yas = (an - datetime.strptime(son[0], "%Y-%m-%d %H:%M:%S")).total_seconds() / 60

    # Rota üzerindeki konum
    try:
        nokta = rota.yol_uzerinde(hat, yon, son[2], son[1])
        toplam = rota.rota_uzunlugu(hat, yon)
        mesafeler = rota.durak_mesafeleri(hat, yon)
    except Exception:
        return None
    if not nokta:
        return None
    ilerleme = nokta[0]

    kodlar = dict(d.execute("SELECT sira, durak_kodu FROM hat_durak"
                            " WHERE hat_kodu=? AND yon=?", (hat, yon)))

    # ── GEÇTİĞİ duraklar: gecis kaydından, saatleriyle (son 2 saat)
    esik = (an - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    gecti = []
    for z, kod, sira in k.execute(
            "SELECT zaman, durak_kodu, sira FROM gecis WHERE kapino=? AND hat=? AND yon=?"
            " AND zaman >= ? ORDER BY zaman DESC LIMIT 3", (kapino, hat, yon, esik)):
        ad = d.execute("SELECT durak_adi FROM durak WHERE durak_kodu=?", (kod,)).fetchone()
        gecti.append({"ad": (ad[0] if ad else "").strip(), "sira": sira,
                      "saat": z[11:16],
                      "dk_once": round((an - datetime.strptime(z, "%Y-%m-%d %H:%M:%S")).total_seconds() / 60)})
    gecti.reverse()

    # ── GİDECEĞİ duraklar: rota üzerinde önündekiler, yolcunun durağına kadar
    gidecek = []
    for sira, ad, m, _ in mesafeler:
        if m <= ilerleme:
            continue
        kod = kodlar.get(sira)
        gidecek.append({"ad": (ad or "").strip(), "sira": sira, "kod": kod,
                        "km": round((m - ilerleme) / 1000, 1),
                        "hedef_mi": bool(durak_kodu and kod == durak_kodu)})
        if durak_kodu and kod == durak_kodu:
            break                          # yolcunun durağında kes
        if len(gidecek) >= 8:
            break

    # ⚠️ Araç yolcunun durağını GEÇMİŞ olabilir (10 Eylül'de görüldü): durak
    #    ekranı 30 sn'de bir tazeleniyor, o arada otobüs durağı geçebiliyor.
    #    Bu durumda "gidecek" listesinde hedef durak hiç yer almıyor ve ekranda
    #    sessizce kayboluyordu. Yolcuya açıkça söylenmeli.
    hedef_gecildi = bool(durak_kodu) and not any(g["hedef_mi"] for g in gidecek)

    # ⭐ HANGİ SEFER (11 Eylül): sefer saati üstteki çipten kaldırıldı, "tıklayınca
    #    görünsün" denildi — o yüzden bu ekranın başlığına giriyor. Kademeler ve
    #    gerekçeleri sefer_kimligi'nde. Bulunamazsa alan boş kalıyor.
    kimlik = None
    try:
        hedef_sira = next((g["sira"] for g in gidecek if g["hedef_mi"]), None)
        varis_dk = None
        if hedef_sira:
            # Kaba bir varış payı: kalan mesafe / ortalama hız. Yalnız tur
            # kontrolünde kullanılıyor, ekranda gösterilmiyor.
            kalan_km = next((g["km"] for g in gidecek if g["hedef_mi"]), 0)
            varis_dk = round(kalan_km / 0.3) if kalan_km else 0
        kimlik = sefer_kimligi(d, k, hat, yon, kapino, an,
                               DNV.gun_tipi(an), sira=hedef_sira, varis_dk=varis_dk)
    except Exception:
        kimlik = None

    return {
        "arac": kapino, "hat": hat, "yon": yon,
        "kalkis": (kimlik or {}).get("kalkis"),
        "kalkis_kaynak": (kimlik or {}).get("kalkis_kaynak"),
        "hedef_gecildi": hedef_gecildi,
        "enlem": son[1], "boylam": son[2],
        "hiz_kmh": round(son[3]) if son[3] is not None else None,
        "konum_yasi_dk": round(yas),
        "rota_oran": round(100 * ilerleme / toplam) if toplam else None,
        "sapma_m": round(nokta[1]),
        "gecti": gecti,
        "gidecek": gidecek,
        "trafik": trafik_indeksi(),
    }


def hat_seferleri(hat, yon, durak_kodu, gun=None):
    """Bu duraktan GÜNÜN TÜM SEFERLERİ, durumlarıyla → tablo.

    ⭐ NEDEN VAR (10 Eylül, Mehmet'in isteği):
      *"tüm sefer saatleri gözükecek, tablo şeklinde. Hangileri çıktıysa bittiyse
        başka bir renk, yoldakiler başka renk, GPS kapalı olanlar başka renk."*

    Dört durum üretiliyor:
        gecti     ✓ o saatte gerçekten araç geçti (gözlemlendi)
        yolda     🚌 şu an canlı görünen araç
        gps_yok   📡 tarifede var, saati geçmiş, ama hiç araç görünmedi
                     → HAYALET SEFER: ürünün asıl vaadi (PROMPT Bölüm 4.2)
        bekleniyor ⏳ tarifede var, saati henüz gelmemiş

    ⚠️⚠️ TARİFE TEK BAŞINA YETMİYOR. Ölçüldü (10 Eylül): 98/D tarifesinde bu
    durak için gün boyu 6 kalkış var ama 16 araç geçti (Bölüm 21). Bu yüzden
    tablo İKİ KAYNAĞI BİRLEŞTİRİYOR: tarife satırları + tarifede karşılığı
    olmayan gerçek geçişler. Yalnızca tarifeye baksaydık günün üçte ikisi
    ekranda hiç görünmezdi.

    ⚠️ EŞLEŞTİRME PENCERESİ: bir tarife kalkışı ile gözlenen geçiş, aradaki
    süre ESLESME_DK'dan azsa aynı sefer sayılıyor. Kalkış saati ile durağa varış
    arasında yol süresi var; bu yüzden pencere geniş tutuldu.
    """
    k = DNV._kayit_db()
    if k is None:
        return None
    d = _dizin()
    gun = gun or datetime.now().strftime("%Y-%m-%d")
    an = datetime.now()
    gun_t = datetime.strptime(gun, "%Y-%m-%d")   # seçilen günün kendisi
    ESLESME_DK = 45

    ad = d.execute("SELECT durak_adi FROM durak WHERE durak_kodu=?", (durak_kodu,)).fetchone()
    hedef = d.execute("SELECT yon_adi FROM hat_durak WHERE hat_kodu=? AND yon=? AND durak_kodu=?",
                      (hat, yon, durak_kodu)).fetchone()

    # ── Gözlenen geçişler
    gozlenen = []
    for z, kap in k.execute(
            "SELECT zaman, kapino FROM gecis WHERE hat=? AND yon=? AND durak_kodu=?"
            " AND zaman LIKE ? ORDER BY zaman", (hat, yon, durak_kodu, gun + "%")):
        gozlenen.append({"an": datetime.strptime(z, "%Y-%m-%d %H:%M:%S"),
                         "saat": z[11:16], "arac": kap, "eslesti": False})

    # ── Tarife kalkışları
    # ⚠️⚠️ GÜN TİPİ SEÇİLEN GÜNDEN ALINIR, BUGÜNDEN DEĞİL (11 Eylül'de bulundu).
    #   Önce `gun_tipi(an)` yazıyordu; tarih seçiciyle geçmişe bakılınca hep
    #   BUGÜNÜN tarifesi geliyordu. Ölçüldü: 141M/D hattında hafta içi 63 kalkış,
    #   pazar 60. Cuma günü pazara bakınca 3 fazla satır çıkıyor ve bunlar
    #   "GPS kapalı" (hayalet sefer) diye işaretleniyordu — o gün öyle bir sefer
    #   hiç planlanmamışken. Ürünün asıl vaadi hayalet tespiti olduğu için bu
    #   yanlış alarm en pahalı hata türü.
    gt = DNV.gun_tipi(gun_t)
    try:
        tarife = sorted({r[0][:5] for r in d.execute(
            "SELECT saat FROM tarife WHERE hat_kodu=? AND yon=? AND gun_tipi=?",
            (hat, yon, gt))})
    except Exception:
        tarife = []

    # ⚠️ GEÇMİŞ GÜN farklı davranır (10 Eylül): o gün bitmiş, "yolda" ya da
    #    "bekleniyor" diye bir şey yok. Canlı araç da sorulmuyor — bugünün
    #    araçlarını dünün tablosuna koymak yanlış olurdu.
    bugun_mu = (gun == an.strftime("%Y-%m-%d"))

    # ── Canlı araçlar (yalnızca bugün için)
    canli = []
    try:
        if not bugun_mu:
            raise StopIteration
        cevap = durakta_ne_var(durak_kodu)
        for h in (cevap or {}).get("hatlar", []):
            if h["hat"] == hat and h["yon"] == yon:
                for v in h.get("varislar", []):
                    if v.get("kaynak") == "canli":
                        canli.append(v)
    except (Exception, StopIteration):
        pass

    # Kaydedicinin o gün hangi saatlerde düzgün çalıştığı (Bölüm 63.7).
    try:
        dilimler = DNV.saglam_dilimler(
            k, (an - timedelta(days=DNV.GOZLEM_GUN)).strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        dilimler = None

    satirlar = []

    # ⭐ YOLDAKİ ARAÇLARI KALKIŞ SAATİNE GÖRE İNDEKSLE (11 Eylül).
    #    Önce yoldaki araç tabloya AYRI bir satır olarak ekleniyordu ve o satırın
    #    saati VARIŞ saatiydi. Sonuç: 09:30 seferi tabloda iki kez görünüyordu —
    #    bir kez tarifeden "bekleniyor", bir kez de varış saatinde "yolda".
    #    Artık aracın hangi kalkışa ait olduğunu biliyoruz (sefer_kimligi), o
    #    yüzden yoldaki araç KENDİ tarife satırını işaretliyor.
    yoldaki = {}
    for v in canli:
        if v.get("kalkis"):
            yoldaki.setdefault(v["kalkis"], v)

    # 1) Tarife satırları — her birine durum ata
    for kalkis in tarife:
        kt = datetime.strptime(gun + " " + kalkis, "%Y-%m-%d %H:%M")
        # bu kalkışa en yakın eşleşmemiş geçiş
        aday, fark = None, None
        for g in gozlenen:
            if g["eslesti"]:
                continue
            f = abs((g["an"] - kt).total_seconds()) / 60
            if f <= ESLESME_DK and (fark is None or f < fark):
                aday, fark = g, f
        if aday:
            aday["eslesti"] = True
            satirlar.append({"kalkis": kalkis, "durum": "gecti", "gecis_saati": aday["saat"],
                             "arac": aday["arac"], "tarifede": True})
        elif kalkis in yoldaki:
            # Bu seferin otobüsü ŞU AN görünüyor: "GPS yok" demek yanlış olurdu.
            v = yoldaki.pop(kalkis)
            satirlar.append({"kalkis": kalkis, "durum": "yolda", "gecis_saati": None,
                             "arac": v.get("arac"), "dakika": v.get("dakika"),
                             "km": v.get("km"), "tarifede": True})
        elif kt <= an:
            # ⚠️⚠️ ÖNCE SORULACAK SORU: o saatte BİZ kayıt yapıyor muyduk?
            #    Kaydedici uyuyorsa/çökmüşse araç geçmiş ama görülmemiş olabilir.
            #    "GPS yok" demek yanlış ALARM olurdu — PROMPT Bölüm 8:
            #    "yanlış alarm, sessiz kalmaktan daha zararlıdır."
            #    Kalite ölçüsü Bölüm 63.7'deki ile aynı: saatte ≥45 tur.
            dilim_saglam = dilimler is None or (gun, kalkis[:2]) in dilimler
            satirlar.append({"kalkis": kalkis,
                             "durum": "gps_yok" if dilim_saglam else "veri_yok",
                             "gecis_saati": None, "arac": None, "tarifede": True})
        else:
            # Geçmiş günde "bekleniyor" olmaz: gün bitti, o sefer görülmedi.
            dilim_saglam = dilimler is None or (gun, kalkis[:2]) in dilimler
            satirlar.append({"kalkis": kalkis,
                             "durum": ("bekleniyor" if bugun_mu
                                       else ("gps_yok" if dilim_saglam else "veri_yok")),
                             "gecis_saati": None, "arac": None, "tarifede": True})

    # 2) Tarifede karşılığı olmayan gerçek geçişler
    for g in gozlenen:
        if not g["eslesti"]:
            satirlar.append({"kalkis": g["saat"], "durum": "gecti",
                             "gecis_saati": g["saat"], "arac": g["arac"], "tarifede": False})

    # 3) Tarife satırına oturmayan yoldaki araçlar.
    #    Kalkışı biliniyorsa o saatte, bilinmiyorsa VARIŞ saatinde gösteriliyor;
    #    ikincisinde satır "tarifede yok" olarak işaretli kalıyor.
    for v in canli:
        k = v.get("kalkis")
        if k and k not in yoldaki:
            continue                     # zaten tarife satırına işlendi
        saat = k or (an + timedelta(minutes=v["dakika"])).strftime("%H:%M")
        satirlar.append({"kalkis": saat, "durum": "yolda", "gecis_saati": None,
                         "arac": v.get("arac"), "dakika": v["dakika"],
                         "km": v.get("km"), "tarifede": False})

    satirlar.sort(key=lambda s: s["kalkis"])
    sayim = {}
    for s in satirlar:
        sayim[s["durum"]] = sayim.get(s["durum"], 0) + 1

    return {
        "hat": hat, "yon": yon,
        "durak_kodu": durak_kodu,
        "durak_adi": (ad[0] if ad else "").strip(),
        "hedef": (hedef[0] if hedef else "").strip(),
        "gun": gun,
        "bugun_mu": bugun_mu,
        "satirlar": satirlar,
        "sayim": sayim,
        "tarife_sayisi": len(tarife),
        "gozlem_sayisi": len(gozlenen),
        # ⚠️ Tarife gözlemden belirgin azsa yolcuya söylenmeli.
        "tarife_eksik": bool(tarife) and len(gozlenen) > len(tarife) * 1.5,
    }


#: Tahmini konumun durak cinsinden payı.
#: ⚠️⚠️ SAYI ÖLÇÜMLE SEÇİLDİ (11 Eylül, 10 Eylül verisi, tek turluk gerçek
#:   izler): tahmin edilen durak sırası ile aracın gerçekten görüldüğü sıra
#:   arasında ortanca 4 durak sapma; %40'ı ≤2 durak, en kötüsü 9 durak.
#:   89A'da ±1-2 (iyi), 522'de sürekli +9 (kötü). Bu yüzden ekranda TEK DURAK
#:   gösterilmiyor — "otobüs şu an ŞURADA" demek ortalama dört durak yanıltmak
#:   olurdu. Bunun yerine BANT veriliyor ve payı yolcuya açıkça söyleniyor.
KONUM_PAY_DURAK = 4


def sefer_konumu(hat, yon, kalkis, durak_kodu=None):
    """GPS'i kapalı bir seferin ŞU AN nerede olduğu — BANT olarak.

    ⭐ NEDEN VAR (11 Eylül, Mehmet'in isteği):
      *"tahmini yapılan aracın da konumu gösterilsin"*

    Canlı araçta konum ölçülüyor (arac_detay). Burada araç görünmüyor: elimizde
    yalnızca kalkış saati ve ölçülmüş parça süreleri var. Kalkıştan bu yana
    geçen süreyi durak sırasına çeviriyoruz.

    ⚠️⚠️ İKİ SINIR, İKİSİ DE ÖLÇÜLDÜ — ve ikisi de yolcuya söyleniyor:
      1. KAPSAMA %34. 1495 hat-yön çiftinin yalnız 503'ünde parça süre verisi
         var (141M ve HT20'de hiç yok, 89A ve 13'te var). Veri yoksa bu
         fonksiyon konum ÜRETMİYOR, `konum_var: False` dönüyor.
      2. SAPMA ortanca 4 durak (gerekçe KONUM_PAY_DURAK'ta). Bu yüzden sonuç
         tek durak değil, ±KONUM_PAY_DURAK'lık bir BANT.

    Ürünün vaadi "GPS kapalıyken de cevap ver" ama cevabın kalitesini saklamak
    o vaadi bozar (PROMPT Bölüm 8).
    """
    k = DNV._kayit_db()
    if k is None:
        return None
    d = _dizin()
    an = datetime.now()

    try:
        mesafeler = rota.durak_mesafeleri(hat, yon)
    except Exception:
        return None
    if not mesafeler:
        return None
    enb = max(m[0] for m in mesafeler)
    kodlar = dict(d.execute("SELECT sira, durak_kodu FROM hat_durak"
                            " WHERE hat_kodu=? AND yon=?", (hat, yon)))
    adlar = {s: (ad or "").strip() for s, ad, _m, _ in mesafeler}

    kalkis_dt = an.replace(hour=int(kalkis[:2]) % 24, minute=int(kalkis[3:5]),
                           second=0, microsecond=0)
    if kalkis_dt > an + timedelta(minutes=1):
        kalkis_dt -= timedelta(days=1)     # gece yarısını aşan sefer
    gecen = (an - kalkis_dt).total_seconds() / 60

    hedef_sira = None
    for s, kod in kodlar.items():
        if kod == durak_kodu:
            hedef_sira = s
            break

    temel = {"hat": hat, "yon": yon, "kalkis": kalkis,
             "durak_kodu": durak_kodu,
             "durak_adi": adlar.get(hedef_sira, "") if hedef_sira else "",
             "gecen_dk": round(gecen), "pay_durak": KONUM_PAY_DURAK,
             "toplam_durak": enb, "konum_var": False, "duraklar": []}

    if gecen < 0:
        temel["not"] = "bu sefer henüz kalkmadı"
        return temel

    # ── Kalkıştan bu yana geçen süre hangi durak sırasına denk geliyor?
    #    İkili arama: kümülatif süre `gecen`i aşmayan en büyük sıra.
    def sure(sira):
        try:
            r = sure_modeli.varis_suresi(k, hat, yon, 1, sira, kalkis_dt)
        except Exception:
            return None
        return r[0] if isinstance(r, (tuple, list)) else r

    if sure(min(10, enb)) is None and sure(max(2, enb // 2)) is None:
        # Bu hat için ölçülmüş parça verisi yok — %66'lık dilim.
        temel["not"] = "bu hat için ölçülmüş süre verisi yok"
        return temel

    lo, hi, bulunan = 1, enb, None
    while lo <= hi:
        orta = (lo + hi) // 2
        s = sure(orta)
        if s is None:
            hi = orta - 1
            continue
        if s <= gecen:
            bulunan, lo = orta, orta + 1
        else:
            hi = orta - 1
    if bulunan is None:
        temel["not"] = "konum hesaplanamadı"
        return temel

    bas = max(1, bulunan - KONUM_PAY_DURAK)
    son = min(enb, bulunan + KONUM_PAY_DURAK)
    temel.update({
        "konum_var": True,
        "tahmini_sira": bulunan,
        "bant_bas": bas, "bant_son": son,
        "bant_bas_ad": adlar.get(bas, ""), "bant_son_ad": adlar.get(son, ""),
        "hedef_sira": hedef_sira,
        # ⚠️ Yolcunun durağı bandın GERİSİNDE kaldıysa otobüs muhtemelen geçmiştir.
        #    Sessiz kalmak yolcuyu boşuna bekletirdi.
        "hedef_gecilmis_olabilir": bool(hedef_sira and hedef_sira < bas),
    })

    # Bandın içindeki duraklar + hedefe kadar birkaç durak daha
    ust = min(enb, max(son, (hedef_sira or son)))
    for s, ad, m, _ in mesafeler:
        if s < bas or s > ust:
            continue
        temel["duraklar"].append({
            "sira": s, "ad": (ad or "").strip(), "kod": kodlar.get(s),
            "bantta": bas <= s <= son,
            "hedef_mi": bool(durak_kodu and kodlar.get(s) == durak_kodu)})
        if len(temel["duraklar"]) >= 16:
            break
    return temel


#: Arka planda süren dış istekler — aynı bölge/kaynak için ikinci bir istek açılmasın.
_suren_istek = set()
_suren_kilit = threading.Lock()


def _arka_planda(anahtar, is_):
    """`is_`'i ayrı bir iş parçacığında BİR KEZ çalıştırır (aynı anahtar sürüyorsa açmaz)."""
    with _suren_kilit:
        if anahtar in _suren_istek:
            return
        _suren_istek.add(anahtar)

    def kos():
        try:
            is_()
        finally:
            with _suren_kilit:
                _suren_istek.discard(anahtar)
    threading.Thread(target=kos, daemon=True).start()


def hava_durumu(enlem, boylam):
    """Durağın konumundaki anlık sıcaklık ve hava kodu — BEKLETMEZ.

    ⚠️⚠️ NEDEN BEKLETMİYOR (7 Ekim, Mehmet'in "gün içinde yavaş" şikâyetinin
    kalan parçası): durak isteklerinin %8'i ~6,2 sn sürüyordu — ızgara
    (Bölüm 77) bunu çözmemişti. Ölçüldü: 3 sn'den uzun süren 23 isteğin 23'ünde
    hava bilgisi BOŞ (zaman aşımı), kısa sürenlerin yalnız 2/97'sinde. Aynı anda
    birden çok bölge sorulunca open-meteo yavaşlıyor ve durak cevabı süs
    niteliğindeki bir SICAKLIĞI 6 sn bekliyordu.

    Artık: önbellekte varsa (BAYAT bile olsa) hemen döner; yoksa None döner ve
    değeri ARKA PLANDA getirir — uygulama 30 sn sonra yenilediğinde görünür.
    """
    if enlem is None or boylam is None:
        return None
    anahtar = (round(enlem, 2), round(boylam, 2))
    kayit = _hava_onbellek.get(anahtar)
    if not (kayit and (datetime.now() - kayit[0]).total_seconds() < HAVA_ONBELLEK_DK * 60):
        _arka_planda(("hava",) + anahtar, lambda: _hava_getir(anahtar, enlem, boylam))
    return kayit[1] if kayit else None


def _hava_getir(anahtar, enlem, boylam):
    """Dış servisten hava bilgisini çeker ve önbelleğe yazar (arka planda)."""
    eski = _hava_onbellek.get(anahtar)
    simdi = datetime.now()
    try:
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
               "&current=temperature_2m,weather_code&timezone=Europe%%2FIstanbul"
               % (enlem, boylam))
        with urllib.request.urlopen(url, timeout=6) as c:   # arka planda; durağı bekletmez
            d = json.loads(c.read().decode("utf-8"))
        g = d.get("current", {})
        sonuc = {"sicaklik": round(g.get("temperature_2m", 0)),
                 "kod": g.get("weather_code")}
    except Exception:
        # Hata: varsa eski BAŞARILI değeri koru (bayat sıcaklık, hiç yoktan iyi).
        sonuc = eski[1] if eski else None
    _hava_onbellek[anahtar] = (simdi, sonuc)


# ─────────────────────────────────────────────────────────────────────────────
# SEFER KİMLİĞİ — "bu otobüs hangi kalkışın otobüsü?"
# ─────────────────────────────────────────────────────────────────────────────

#: Ölçülen kalkış ile tarife kalkışı arasında kabul edilen en büyük fark.
#: ⚠️ SAYI ÖLÇÜMLE SEÇİLDİ (11 Eylül, 10 Eylül verisi üzerinde):
#:     141M/D → geçiş−tarife farkı ortanca +3 dk, %100'ü ±10 dk içinde
#:     HT20/D → ortanca +2 dk, %100'ü ±10 dk içinde
#:     98/D   → ortanca +310 dk, %0'ı ±10 dk içinde
#:   İlk ikisinde eşleştirme kusursuz. 98'de çöküyor çünkü o hattın tarifesi
#:   zaten bozuk (6 kalkış yazılı, 18 araç geçmiş — Bölüm 21). Pencere olmasa
#:   "en yakın tarife" seçilir ve yolcuya 457 DAKİKA şaşan bir sefer saati
#:   gösterilirdi. Pencere, bozuk tarifeyi sessizce reddetmeyi sağlıyor.
SEFER_ESLESME_DK = 10

#: Son 20 dakikalık izinde bundan az yer değiştiren araç "canlı yaklaşan" SAYILMAZ.
#: ⚠️⚠️ NEDEN (7 Ekim, Mehmet: *"bu saatte yolda otobüs olması imkansız ama
#:   uygulama tek tük otobüs gösteriyor, bunlar duran ama GPS açık otobüsler"*).
#:   Kaydedici duran araçları da 10 dk'da bir yazıyor (DURAN_ARAC_NABZI_DK —
#:   "peronda bekleyen" ile "GPS'i sönmüş"ü ayırmak için, veri tarafında DOĞRU
#:   bir karar). Ama durak ekranı bu nabız kayıtlarını yaklaşan otobüs sanıp
#:   "17 dk sonra" diyordu. Ölçüldü:
#:       gece  01:54   140 "canlı" araç → 123'ü son 30 dk'da <120 m (%88)
#:       sabah 08:15   206 "canlı" araç →  15'i son 20 dk'da <150 m (%7)
#:       akşam 18:00   254 "canlı" araç →  17'si               (%7)
#:   Dağılım iki tepeli: duranlar 0-120 m, yol alanlar akşam trafiğinde bile
#:   20 dk'da 600 m'nin çok üstünde. 150 m = 0,45 km/sa — bu trafik değil,
#:   park ya da son durakta bekleme; o hızla "X dk" tahmini zaten yanlış olurdu.
#:   Gizlenen araç bilgi kaybı değil: o hat için tarife/gözlem kademesi devralır.
#:   Yan etki: yeni KALKAN araç, kalkıştan 1-2 dk sonra görünür hâle gelir.
#:
#:   ⚠️ DOĞRULAMA — gizlenen araç gerçekten GELDİ Mİ? (6 Ekim verisi, gecis
#:   tablosundan; "geldi" = gösterilen dakika + 20 dk içinde o duraktan geçti)
#:       gece   01:50   gizlenen 29 → geldi  0   ✅ hepsi park (ortanca 120 dk duruyor)
#:       sabah  08:15   gizlenen 21 → geldi 11   gündüz kalkış bekleyenler var
#:       akşam  18:00   gizlenen 21 → geldi  6
#:   Gündüz gizlenip yine de gelenlerde eski ekranın dakikası −25…+15 dk
#:   şaşıyordu — gösterilse de doğru bilgi değildi. Ve gizlenen aracın hattı
#:   ekrandan KAYBOLMUYOR: 42 gündüz vakasının 40'ında hat başka kaynakla
#:   görünmeye devam etti (25 başka canlı araç · 9 tarife · 4 GPS-kapalı · 2 gözlem).
#:
#:   ⚠️⚠️ EŞİĞİ YÜKSELTME. 300 ve 400 m denendi:
#:       sabah 08:15   150 m → 21 gizli (11 geldi) · 300 m → 25 gizli (15 geldi)
#:   Eklenen 4 aracın 4'ü de gerçekten gelmişti; gece ise hiçbir kazanç yok.
#:   Yavaş trafik 150-400 m bandına düşüyor, park bandı 150 m altında.
#:
#:   ⚠️ ÖLÇÜ "İLK-SON" DEĞİL "EN UZAK" (7 Ekim akşamı düzeltildi): izin ilk
#:   ve son noktasını kıyaslamak, 20 dk içinde gidip başladığı yere dönen gerçek
#:   otobüsü (son durakta dönüş, ring güzergâh) gizliyordu. İzdeki en uzak
#:   noktanın son konuma uzaklığına bakılınca (gerçek varışlarla, 6 Ekim):
#:       sabah 08:15   gizlenen 21 → 17 · bunlardan gelen 11 → 8  (3 otobüs kurtarıldı)
#:       akşam 18:00   gizlenen 21 → 19 · bunlardan gelen  6 → 5
#:       gece  01:50   gizlenen 29 → 29 · gelen 0 → 0  (GPS sıçraması sorun yaratmadı)
#:
#:   Ayrım ölçütü olarak "durma süresi" ve "yakın tarife kalkışı" da denendi;
#:   ikisi de park ile kalkış beklemeyi temiz ayırmadı (tarife olan duran
#:   araçların bile %62'si gelmedi). Basit kural kazandı.
DURAN_ESIK_M = 150

#: Kalkıştan bu yana geçen süre, ölçülmüş seyahat süresinin kaç katını aşarsa
#: o kalkış REDDEDİLİR (araç aslında yeni bir tura çıkmış demektir).
#: ⚠️⚠️ NEDEN GEREKLİ (11 Eylül, ilk sürümde bulunan hata): araçlar gün içinde
#:   defalarca tur atıyor ve kaydedici her turun kalkışını göremiyor. "Kalkış
#:   durağından EN SON geçiş" almak, kaçırılan turlarda ESKİ kalkışı gösteriyordu.
#:   Ölçüldü (11 Eylül 09:47): 15B/C-252 kalkış durağından yalnız 06:55'te geçmiş
#:   ama 09:43'te hâlâ yolda — ikinci turunda. 98/A-1847 ise "01:00 kalkışlı"
#:   görünüyordu; aradan 8 sa 43 dk geçmişti. Yolcuya üç saat önce kalkmış bir
#:   seferin numarasını vermek, hiç vermemekten kötü.
TUR_TOLERANS = 1.8
TUR_PAY_DK = 25

#: 3. KADEME — kalkış geçişi hiç kaydedilmemişse varış saatinden GERİYE hesap.
#: ⚠️ Ölçüldü (11 Eylül, 10 Eylül verisi): hesaplanan kalkış ile gerçek kalkış
#:   arasında ortanca +3,6 dk fark; %54'ü ±5 dk, %81'i ±10 dk içinde. Tarife
#:   kalkışları 10-20 dk aralıklı olduğu için ±10 dk'lık bir pencere beşte bir
#:   ihtimalle KOMŞU SEFERİ gösterirdi. Bu yüzden pencere ±5 dk'ya çekildi ve
#:   ikinci bir koşul kondu: en yakın kalkış, ikinciden belirgin yakın olmalı.
#:   İki kalkış arasında ortada kalan hesap belirsizdir → susuyoruz.
#:   (Aynı desen hat_tahmini.tahmin_et'teki USTUNLUK kontrolü.)
HESAP_ESLESME_DK = 5
HESAP_USTUNLUK = 2.0

#: (hat, yon) → (sira, durak_kodu). Kalkış durağı gün içinde değişmez.
_KALKIS_DURAK_ONBELLEK = {}
#: (hat, yon, gun_tipi) → [dakika, ...] tarife kalkışları
_TARIFE_ONBELLEK = {}


def _kalkis_duragi(d, hat, yon):
    """Kalkışı haber veren durak — rota başından biraz ötedeki ilk durak."""
    anahtar = (hat, yon)
    if anahtar not in _KALKIS_DURAK_ONBELLEK:
        try:
            kd = hayalet.kalkis_durak(d, hat, yon)
        except Exception:
            kd = None
        _KALKIS_DURAK_ONBELLEK[anahtar] = (kd[1] if kd else None)
    return _KALKIS_DURAK_ONBELLEK[anahtar]


def _tarife_dakikalari(d, hat, yon, gt, an=None):
    """Kalkış saatleri (günün dakikası). `an` verilirse önce PLAN (arşiv ·
    gerekçe DNV.planli_seferler'de), arşivde yoksa tarife."""
    if an is not None:
        plan = DNV.planli_seferler(d, hat, yon, an)
        if plan is not None:
            return sorted({k.hour * 60 + k.minute for k, _ in plan})
    anahtar = (hat, yon, gt)
    if anahtar not in _TARIFE_ONBELLEK:
        try:
            saatler = {r[0][:5] for r in d.execute(
                "SELECT saat FROM tarife WHERE hat_kodu=? AND yon=? AND gun_tipi=?",
                (hat, yon, gt))}
        except Exception:
            saatler = set()
        _TARIFE_ONBELLEK[anahtar] = sorted(
            int(s[:2]) * 60 + int(s[3:5]) for s in saatler if len(s) >= 5)
    return _TARIFE_ONBELLEK[anahtar]


def _hesapla_kalkis(d, hat, yon, an, gt, sira, varis_dk):
    """3. kademe: aracın kalkışını VARIŞ saatinden geriye hesaplar.

    Araç durağa `varis_dk` sonra varacak; kalkıştan bu durağa ölçülmüş süre
    biliniyor → kalkış ≈ varış − süre. Bulunan saat bir tarife kalkışına yeterince
    yakın VE komşusundan belirgin yakınsa o sefer kabul edilir.

    ⚠️ Hata payı ölçülü (gerekçe HESAP_ESLESME_DK'da). Belirsizlikte None
    döndürüyor: yanlış sefer numarası vermektense hiç vermemek yeğ
    (PROMPT Bölüm 8 — "yanlış alarm, sessiz kalmaktan daha zararlıdır").
    """
    if sira is None or varis_dk is None:
        return None
    tarife = _tarife_dakikalari(d, hat, yon, gt, an)
    if not tarife:
        return None
    varis = an + timedelta(minutes=varis_dk)
    try:
        tahmin = DNV.saatli_varis(hat, yon, sira, varis)
    except Exception:
        tahmin = None
    if not tahmin:
        return None
    sure = tahmin[0] if isinstance(tahmin, (tuple, list)) else tahmin
    hd = int(((varis - timedelta(minutes=sure)) - an.replace(
        hour=0, minute=0, second=0, microsecond=0)).total_seconds() // 60)

    sirali = sorted(tarife, key=lambda x: abs(x - hd))
    en_yakin = sirali[0]
    fark = abs(en_yakin - hd)
    if fark > HESAP_ESLESME_DK:
        return None
    # Komşu kalkış da bu kadar yakınsa hangisi olduğunu bilemeyiz → sus.
    if len(sirali) > 1 and abs(sirali[1] - hd) < max(fark, 1) * HESAP_USTUNLUK:
        return None
    return {"kalkis": "%02d:%02d" % (en_yakin // 60 % 24, en_yakin % 60),
            "kalkis_kaynak": "hesap", "kalkis_olculen": None}


def sefer_kimligi(d, k, hat, yon, kapino, an, gt, sira=None, varis_dk=None):
    """Görünen aracın hangi kalkışa ait olduğunu döndürür.

    ⭐ NEDEN VAR (11 Eylül, Mehmet'in isteği):
      *"tahmini yapılan seferin hangi saat dakikadaki otobüs olduğunu öğreneyim"*

    Ekranda "5 dk" yazıyordu ama bu, tarifedeki hangi seferin otobüsü belli
    değildi. Tarife satırlarında ve GPS'i kapalı seferlerde kalkış saati zaten
    vardı; ironik biçimde EN ÇOK GÜVENDİĞİMİZ satırda — canlı görünen araçta —
    yoktu.

    Yöntem, kademeli: önce ÖLÇÜM, sonra tarife, hiçbiri tutmazsa SUSMAK.
        1. Araç kalkış durağından bugün en son ne zaman geçti? Bu, içinde
           bulunduğu turun başlangıcı — tahmin değil, kaydedilmiş gözlem.
        2. O saatin ±SEFER_ESLESME_DK içinde bir tarife kalkışı varsa onu
           göster: yolcunun tarifede göreceği saat odur.
        3. Tarife tutmuyorsa ölçülen saati göster ve "tarifede yok" de.
        4. Kalkış geçişi hiç yoksa None döndür — uydurmuyoruz.

    ⚠️ Kapsama ölçüldü (10 Eylül verisi): 141M %100, HT20 %100, 98 %80,
       89A %73, 146 %45. Yani her araçta cevap veremiyoruz; veremediğimizde
       ekranda o satır hiç görünmüyor, yanlış saat görünmesinden iyidir.
    """
    kod = _kalkis_duragi(d, hat, yon)
    gun = an.strftime("%Y-%m-%d")
    r = None
    if kod:
        r = k.execute(
            "SELECT zaman FROM gecis WHERE hat=? AND yon=? AND durak_kodu=? AND kapino=?"
            " AND zaman LIKE ? ORDER BY zaman DESC LIMIT 1",
            (hat, yon, kod, kapino, gun + "%")).fetchone()
    if not r:
        # Kalkış geçişi yok → 3. kademe: varıştan geriye hesap (gerekçe yukarıda).
        return _hesapla_kalkis(d, hat, yon, an, gt, sira, varis_dk)
    olculen = r[0][11:16]
    od = int(olculen[:2]) * 60 + int(olculen[3:5])

    # ── TUR KONTROLÜ: bu kalkış GERÇEKTEN bu seferin kalkışı mı? ─────────────
    #    Gerekçe TUR_TOLERANS'ın başında. Kalkıştan bu durağa ölçülmüş süreyi
    #    biliyoruz; aradan bunun çok üstünde zaman geçtiyse araç o turu çoktan
    #    bitirmiş, elimizdeki kalkış eskimiş demektir → sussak daha iyi.
    if sira is not None:
        kalkis_dt = datetime.strptime(r[0][:16], "%Y-%m-%d %H:%M")
        gecen = (an - kalkis_dt).total_seconds() / 60 + (varis_dk or 0)
        try:
            tahmin = DNV.saatli_varis(hat, yon, sira, kalkis_dt)
        except Exception:
            tahmin = None
        if tahmin:
            beklenen = tahmin[0] if isinstance(tahmin, (tuple, list)) else tahmin
            if gecen > beklenen * TUR_TOLERANS + TUR_PAY_DK:
                return _hesapla_kalkis(d, hat, yon, an, gt, sira, varis_dk)
        elif gecen > 150:
            # Ölçülmüş süre yoksa kaba bir üst sınır: 2,5 saatten eski kalkış
            # şehir içi bir hat için gerçekçi değil.
            return _hesapla_kalkis(d, hat, yon, an, gt, sira, varis_dk)

    tarife = _tarife_dakikalari(d, hat, yon, gt, an)
    if tarife:
        en_yakin = min(tarife, key=lambda x: abs(x - od))
        if abs(en_yakin - od) <= SEFER_ESLESME_DK:
            return {"kalkis": "%02d:%02d" % (en_yakin // 60 % 24, en_yakin % 60),
                    "kalkis_kaynak": "tarife", "kalkis_olculen": olculen}
    # Tarife tutmadı: bozuk ya da eksik. Ölçtüğümüzü söylüyoruz.
    return {"kalkis": olculen, "kalkis_kaynak": "olcum", "kalkis_olculen": olculen}


def _tarife_gurultusunu_at(varislar):
    """⚠️ Elimizde GERÇEK varış varken uzak tarife satırı göstermek gürültü.

    Ölçülen vaka: 98S'de 15 ve 17 dakikalık iki canlı otobüsün altında
    "17:00 kalkışı · 115 dk" duruyordu. Yolcu için değersiz, hatta kafa karıştırıcı —
    iki otobüs zaten geliyor. (Bölüm 38'deki '429 DAKİKA' hatasının aynı ailesi.)

    Kural: kaç tane gerçek varış (canlı / GPS kapalı) varsa, tarife o kadar geri
    çekilir. Hiç gerçek varış yoksa tarife tek kaynak, üçü birden gösterilir.
    """
    gercek = [v for v in varislar if v["kaynak"] in ("canli", "gps_kapali")]
    if not gercek:
        return varislar
    izin = max(0, 2 - len(gercek))       # 1 gerçek varış → 1 tarife · 2+ → hiç
    sonuc, n = [], 0
    for v in varislar:
        if v["kaynak"] == "tarife":
            if n >= izin:
                continue
            n += 1
        sonuc.append(v)
    return sonuc


def _ayni_hat_kartlarini_birlestir(hatlar):
    """Aynı (hat, yön) için açılmış birden fazla kartı tek karta indirir.

    ⚠️⚠️ NEDEN (7 Ekim, denetimde bulundu): bazı güzergâhlar bir durağın önünden
    AYNI TURDA İKİ KEZ geçiyor — döngülü güzergâh ya da başlangıcı ile sonu aynı
    durak olan ring hatlar. Ölçüldü: şehirde 87 (durak, hat, yön) çifti birden
    fazla sırada (ör. MK12/G sıra 1 ve 42; BA-5/G DEĞİRMEN PLAJI'nda 5 ve 11).
    Motor her sıra için ayrı kart açıyordu; tarife tahmini durak koduna göre
    yapıldığı için iki kart AYNI dakikaları gösteriyordu — yolcu aynı otobüsü
    iki kez görüyordu.

    Birleştirme: varışlar tek listede toplanır; aynı araç (canlı) ya da aynı
    kalkış saati (tarife / GPS-kapalı / iptal) iki kez geçiyorsa EN YAKINI
    tutulur — yolcu için anlamlı olan otobüsün bu duraktan İLK geçişi.
    Kartın geri kalan alanları (sıra, gözlem…) en yakın varışı taşıyan karttan.
    """
    gruplar, sira = {}, []
    for h in hatlar:
        a = (h["hat"], h["yon"])
        gruplar.setdefault(a, []).append(h)
        if len(gruplar[a]) == 1:
            sira.append(a)
    sonuc = []
    for a in sira:
        kartlar = gruplar[a]
        if len(kartlar) == 1:
            sonuc.append(kartlar[0])
            continue
        en_iyi = {}
        for k in kartlar:
            for v in k.get("varislar", []):
                if v.get("kaynak") == "canli" and v.get("arac"):
                    anahtar = ("canli", v["arac"])
                elif v.get("kalkis"):
                    anahtar = (v.get("kaynak"), v["kalkis"])
                else:
                    anahtar = (v.get("kaynak"),)
                if anahtar not in en_iyi or v.get("dakika", 9999) < en_iyi[anahtar].get("dakika", 9999):
                    en_iyi[anahtar] = v
        varislar = sorted(en_iyi.values(), key=_sira)
        ana = min(kartlar, key=lambda k: _sira(k["varislar"][0]) if k.get("varislar") else (9, 999))
        birlesik = dict(ana)
        birlesik["varislar"] = _tarife_gurultusunu_at(varislar)
        sonuc.append(birlesik)
    return sonuc


def _sira(v):
    """Sıralama anahtarı: önce gerçekten gelen otobüsler, sonra gecikmiş uyarılar,
    en sonda seferi bitmiş hatlar.
    ⚠️ `dakika` boş olabilir (iptal satırında varış yok) — sona atılır, çökmez."""
    return (2 if v.get("kaynak") == "son_sefer" else (1 if v.get("gecikmis") else 0),
            v["dakika"] if v.get("dakika") is not None else 10 ** 6)


#: ⭐⭐ SON SEFER (9 Ekim · Bölüm 86). Bugünün son planlı seferi kalktıysa ekran
#: artık "~X dk" diye KÖR TAHMİN yapmıyor. ÖLÇÜLDÜ (6-8 Ekim geceleri · 150 durak ·
#: 2.700 ekran geçmişte canlandırıldı): gece gösterilen gözlem satırlarının %65'i
#: seferi çoktan bitmiş bir hattı gösteriyordu (00:30'da %83). Mehmet'in gördüğü:
#: 8 Ekim 23:35, 76O "~8 dk" — son sefer 23:17'de geçmişti, o gece başka yoktu.
#:
#: Son seferin bu duraktan GEÇTİĞİ, beklenen varışından en çok bu kadar önce
#: görülen bir geçişle kabul edilir. Daha erken bir geçiş bir önceki sefer ya da
#: yanlış hatta atanmış bir araç olabilir (Bölüm 71 · 8 Ekim'de 15C'nin aracı
#: C-1669, 14F diye kaydedilmişti). Sık seferli hatta pencere iki kalkış
#: arasının yarısına daralır: önceki seferin geçişi son sefer sanılmasın.
SON_SEFER_ERKEN_DK = 20
#: Pencerenin GEÇ ucu: beklenen varıştan bu kadar SONRAKİ geçiş son sefer sayılmaz.
#: ⚠️ NEDEN (9 Ekim, sınamada bulundu): 98KM'nin son kalkışı 15:10, ama aynı
#:   araçlar (A-1847, A-1845…) akşam başka işte/garaja giderken de "98KM" diye
#:   kaydediliyor → ekran "son sefer geçti · 23:00" diyordu. ÖLÇÜLDÜ (5-7 Ekim ·
#:   4.351 son sefer): kalkış gecikmesi ortanca 0 · %95 10 · %99 32 dk. 32 + yolculuk
#:   süresi payı → 45.
SON_SEFER_GEC_DK = 45


def _son_sefer(dz, hat, yon, durak_kodu, sira, an):
    """Bugünün son planlı seferi KALKTIYSA onun satırı; kalkmadıysa ya da plan yoksa None.

    ⚠️ Saate bakıp "geçti" demek yetmiyor: arşivin "erken" hatalarının çoğu son
    seferin GEÇ kalkması (gerekçe DNV.planli_seferler'de). "Geçti" için bu
    duraktan geçişin GÖRÜLMESİ şart; görülmediyse "henüz görülmedi" — dakika
    yok, söz yok (PROMPT Bölüm 2: emin olmadığını emin gibi söylemez)."""
    son = DNV.son_planli_kalkis(dz, hat, yon, an)
    if son is None or son > an:
        return None
    sb = DNV.sefer_bazli_varis(hat, yon, durak_kodu, son)
    sm = None if sb else DNV.saatli_varis(hat, yon, sira, son)
    sure = (sb or sm or [None])[0]
    beklenen = son + timedelta(minutes=sure) if sure is not None else None
    gecis = None
    if beklenen is not None:
        erken = SON_SEFER_ERKEN_DK
        onceki = [k for k, _ in (DNV.planli_seferler(dz, hat, yon, an) or []) if k < son]
        if onceki:
            erken = min(erken, (son - max(onceki)).total_seconds() / 60 / 2)
        r = DNV._kayit_db().execute(
            "SELECT MAX(zaman) FROM gecis WHERE durak_kodu=? AND hat=? AND yon=?"
            " AND zaman >= ? AND zaman <= ?",
            (durak_kodu, hat, yon,
             (beklenen - timedelta(minutes=erken)).strftime("%Y-%m-%d %H:%M:%S"),
             min(an, beklenen + timedelta(minutes=SON_SEFER_GEC_DK)).strftime("%Y-%m-%d %H:%M:%S"))
        ).fetchone()
        gecis = r[0][11:16] if r and r[0] else None
    kalkis = son.strftime("%H:%M")
    return {"kaynak": "son_sefer", "guven": "orta",
            # `dakika` uygulamanın modelinde zorunlu; anlamı yok, sıralama _sira'da.
            "dakika": 0, "kalkis": kalkis, "gecis": gecis,
            "varis": beklenen.strftime("%H:%M") if beklenen else None,
            "not": ("bugünkü son sefer geçti · %s" % gecis) if gecis
                   else ("son sefer %s kalkışlı · henüz görülmedi" % kalkis)}


def durakta_ne_var(durak_kodu, an=None, surum=1):
    """ASIL CEVAP. Üç kademe: canlı araç · gözlem · tarife (9 Ekim'den beri plan).

    `surum`: uygulamanın tanıdığı satır türleri. 2 → "son_sefer" satırı da gelir
    (eski uygulama bu türü tanımıyor — gerekçe aşağıda, SON SEFER bloğunda)."""
    an = an or datetime.now()
    dz = _dizin()
    d = dz.execute("SELECT durak_adi, ilce, enlem, boylam FROM durak WHERE durak_kodu=?",
                   (durak_kodu,)).fetchone()
    if not d:
        return None
    gt = DNV.gun_tipi(an)
    sonuc = {"kod": durak_kodu, "ad": (d[0] or "").strip(), "ilce": d[1],
             "an": an.strftime("%H:%M"), "gun_tipi": gt, "hatlar": [],
             "hava": hava_durumu(d[2], d[3]),
             # Şehir geneli trafik — başlıkta hava durumunun yanında. Tahmine
             # girmiyor, "20 dakika normalden uzun mu?" sorusuna bağlam veriyor.
             "trafik": trafik_indeksi()}
    # ⭐ İPTAL DUYURULARI (Bölüm 47) — İETT'nin kendi bildirimi, tahmin değil.
    try:
        iptaller = duyurular.iptal_haritasi(DNV._kayit_db(), dz)
    except Exception:
        iptaller = {"kesin": {}, "belirsiz": {}, "gunluk": {}}

    for hat, yon, yon_adi, sira, hat_adi, toplam_durak in DNV.duraktan_gecen_hatlar(dz, durak_kodu):
        try:
            oran = rota.oran(hat, yon, sira)
        except (KeyError, IndexError):
            continue
        kayit = {"hat": hat, "yon": yon, "hedef": (yon_adi or "").strip() or hat_adi,
                 "sira": sira, "toplam_durak": toplam_durak,
                 "oran": round(oran * 100), "varislar": []}

        # ── 1. CANLI ────────────────────────────────────────────────────────
        try:
            araclar = DNV.canli_araclar(hat, an) or []
        except Exception:
            araclar = []
        durak_m = None
        if araclar:
            try:
                durak_m = rota.durak_mesafeleri(hat, yon)[sira - 1][2]
            except (KeyError, IndexError):
                durak_m = None
        if durak_m is not None:
            yaklasan = []
            for a in araclar:
                if a.get("yon") != yon:
                    continue
                # ⚠️ DURAN ARAÇ CANLI YAKLAŞAN DEĞİLDİR — gerekçe DURAN_ESIK_M'de.
                if a.get("en_uzak_m") is not None and a["en_uzak_m"] < DURAN_ESIK_M:
                    continue
                try:
                    arac_m, sapma = rota.yol_uzerinde(hat, yon, a["boylam"], a["enlem"])
                except Exception:
                    continue
                if sapma > DNV.YAKIN_SAPMA_M:
                    continue
                kalan = durak_m - arac_m
                if kalan > 0:
                    yaklasan.append((kalan, arac_m, a))
            yaklasan.sort(key=lambda t: t[0])
            # ⚠️ AYNI SEFER İKİ ARACA VERİLEMEZ (11 Eylül'de görüldü): 89A'da
            #    arka arkaya gelen iki otobüsün ikisi de "09:45 seferi" çıktı.
            #    Geri hesap kademesi yakın araçlarda aynı kalkışa düşebiliyor.
            #    Liste durağa yakınlığa göre sıralı; kalkışı ilk talep eden alır,
            #    sonraki sussun — yanlış sefer numarası vermektense boş bırakılır.
            kullanilan_kalkis = set()
            for kalan, arac_m, a in yaklasan[:3]:
                hiz = a["hiz"][0] if a.get("hiz") else DNV.VARSAYILAN_HIZ
                # ⭐ Ölçülmüş parça süreleri; veremezse mesafe÷hıza düşer (Bölüm 51)
                dk, yontem = DNV.canli_varis_dk(hat, yon, sira, arac_m, kalan, hiz, an)
                v = {
                    "kaynak": "canli", "guven": "yuksek",
                    "dakika": round(dk),
                    "km": round(kalan / 1000, 2),
                    "arac": a["kapino"],
                    "hiz_kmh": round(a["hiz"][0] * 60 / 1000) if a.get("hiz") else None,
                    "yontem": yontem,
                    "not": "araç görünüyor"}
                # ⭐ "Bu hangi seferin otobüsü?" — gerekçesi sefer_kimligi'nde.
                #    Cevap veremezsek alan hiç eklenmiyor; ekranda da görünmüyor.
                try:
                    kimlik = sefer_kimligi(dz, DNV._kayit_db(), hat, yon, a["kapino"],
                                           an, gt, sira=sira, varis_dk=round(dk))
                except Exception:
                    kimlik = None
                if kimlik and kimlik["kalkis"] in kullanilan_kalkis:
                    kimlik = None
                if kimlik:
                    kullanilan_kalkis.add(kimlik["kalkis"])
                    v.update(kimlik)
                kayit["varislar"].append(v)

        # ── 1b. GPS KARANLIĞI — yolda ama görünmeyen seferler ───────────────
        #    Ürünün asıl vaadi: "Otobüsüm Nerede"nin sustuğu yer tam burası.
        try:
            gorunen = [v["dakika"] for v in kayit["varislar"] if v["kaynak"] == "canli"]
            for s, varis, dakika in DNV.yoldaki_gorunmeyenler(
                    dz, hat, yon, sira, an, gt, gorunen, iptaller):
                kayit["varislar"].append({
                    "kaynak": "gps_kapali", "guven": "orta",
                    "kalkis": s, "varis": varis.strftime("%H:%M"),
                    "dakika": round(dakika),
                    "not": "konum bildirmiyor · ölçülmüş sürelerden tahmin"})
        except Exception:
            pass

        # ── 2. GÖZLEM ───────────────────────────────────────────────────────
        try:
            g = DNV.gozlenen_gecisler(hat, yon, durak_kodu, an, gt)
        except Exception:
            g = None
        if g:
            ortanca, en_az, en_cok, n, son_dk, bekleme = g
            # ⚠️ `aralik_dk` (ortanca) DEĞİŞMEDİ — "sıradaki geçiş" hesabı ona
            #    dayanıyor (aşağıda: aralik_dk - son_gecis_dk). `bekleme_dk` ise
            #    yolcuya gösterilecek olan: rastgele gelen birinin gerçekte
            #    bekleyeceği süre. İkisi farklı sorular, ikisi de gerekli.
            kayit["gozlem"] = {"aralik_dk": round(ortanca), "en_az": round(en_az),
                               "en_cok": round(en_cok), "olcum": n,
                               "bekleme_dk": round(bekleme) if bekleme is not None else None,
                               "son_gecis_dk": round(son_dk) if son_dk is not None else None}

        # ── 3. TARİFE + SAATLİ SÜRE MODELİ ──────────────────────────────────
        for saat, guzergah in DNV.sonraki_kalkislar(dz, hat, yon, gt, an, adet=3):
            kalkis = an.replace(hour=int(saat[:2]) % 24, minute=int(saat[3:5]),
                                second=0, microsecond=0)
            if kalkis < an:
                kalkis += timedelta(days=1)

            # ⭐⭐ SEFER BAZLI ÖNCE (9 Eylül · Bölüm 63.8, Mehmet'in fikri):
            #    "bu kalkış geçmişte buraya kaç dakikada geldi" — tek ölçüm.
            #    Parça modeli 16 durak arasını ayrı tahmin edip topluyor ve
            #    hatalar birikiyor. Kayırmasız sınavda ortanca hata 4,5 → 2,4 dk.
            #    Veri yoksa (o durak için geçmiş kayıt yok) parçaya düşülüyor.
            sb = DNV.sefer_bazli_varis(hat, yon, durak_kodu, kalkis)
            sm = None if sb else DNV.saatli_varis(hat, yon, sira, kalkis)

            # ── ⭐ İPTAL DUYURUSU (Bölüm 47) ──────────────────────────────────
            #    Bu satır TAHMİN DEĞİL; İETT bu kalkışın yapılmayacağını bildirdi.
            #    `varis` bilerek boş: gelmeyecek otobüsün varış saati yok.
            #    Ama `dakika` doluyor — yalnızca SIRALAMA için: iptal uyarısı
            #    komşu varışların arasında, doğru yerinde görünsün diye.
            #    Ufuk (TARIFE_UFKU_DK) burada uygulanmıyor: beklediği otobüsün
            #    gelmeyeceğini bilmek, varış tahmininden daha değerli.
            duyuru = iptaller["kesin"].get((hat, yon, saat[:5]))
            # ⚠️⚠️ İPTAL UFKU (7 Ekim, denetimde bulundu): "BA-2 · DEĞİRMEN PLAJI →
            #   1.442 dk". Tarifedeki 17:03, saat 17:03'ü birkaç saniye geçince
            #   yukarıda YARINA kaydırılıyordu; iptal anahtarı (hat, yön, saat)
            #   tarih taşımadığı için BUGÜNÜN iptal duyurusu YARININ aynı saatli
            #   seferine iliştiriliyordu. Ufkun yokluğu "gelmeyeceğini bilmek
            #   değerli" gerekçesiyle kasıtlıydı — birkaç saat için doğru, 24 saat
            #   için anlamsız. 6 saat: gece yarısını aşan yakın iptaller korunur.
            if duyuru and (kalkis - an) > timedelta(minutes=IPTAL_UFKU_DK):
                duyuru = None
            if duyuru:
                tahmini = (sb or sm or [None])[0]
                if tahmini is not None:
                    sirala = round(((kalkis + timedelta(minutes=tahmini)) - an).total_seconds() / 60)
                else:
                    sirala = round((kalkis - an).total_seconds() / 60)
                kayit["varislar"].append({
                    # ⚠️ guven "kesin" DEĞİL: ölçüldü (1 Eylül, arşivle kıyas),
                    #    duyurulan iptallerin %66'sı gerçekleşiyor, %34'ü telafi
                    #    ediliyor. Kesin olan DUYURUNUN KENDİSİ, seferin akıbeti değil.
                    "kaynak": "iptal", "guven": "orta",
                    "kalkis": saat[:5], "varis": None, "dakika": sirala,
                    "kalkis_yeri": duyuru["kalkis_yeri"],
                    "not": "İETT duyurusu: bu sefer yapılmayacak"})
                continue

            if not (sb or sm):
                continue

            if sb:
                # Sefer bazlı: alt/üst SINIRI da ölçümden geliyor (p10-p90),
                # uydurma bir yüzde payı değil. Bu yüzden güven daha yüksek.
                dk, alt_dk, ust_dk, n = sb
                # ⚠️ Gözlem sayısı tek başına yetmiyor: 89S'de 6 ölçüm vardı ama
                #    aralık 17:18–18:59 (1 sa 41 dk) çıktı. O hattın süresi
                #    gerçekten oynak; "orta güven" demek yolcuyu yanıltırdı.
                #    Aralık ortancanın yarısından genişse güven DÜŞÜK.
                #    (PROMPT Bölüm 2: "asla emin olmadığı şeyi emin gibi söylemez")
                #    EŞİK ÖLÇÜLEREK KONDU (9 Eylül · 214 tahminlik örneklem):
                #        yayılma dağılımı → %25: 0,27 · ORTANCA: 0,42 · %75: 0,73 · %90: 1,30
                #    0,8 = ortancanın iki katı; tahminlerin ~%77'si "orta" güven
                #    alıyor, oynak hatlar (89S: 1,87) dışarıda kalıyor.
                yayilma = (ust_dk - alt_dk) / dk if dk else 9
                guven = "orta" if (n >= 5 and yayilma <= 0.8) else "dusuk"
                aciklama = "%d ölçülmüş seferden" % n
                yontem = "sefer"
            else:
                dk, n_saatli, n_yedek = sm
                pay = 0.12 if n_yedek == 0 else 0.22
                alt_dk, ust_dk = dk * (1 - pay), dk * (1 + pay)
                guven = "orta" if n_yedek == 0 else "dusuk"
                aciklama = ("%d parça o saatin verisinden" % n_saatli
                            + (", %d genel" % n_yedek if n_yedek else ""))
                yontem = "parça"

            varis = kalkis + timedelta(minutes=dk)
            gecen = (varis - an).total_seconds() / 60
            if gecen > TARIFE_UFKU_DK:
                continue                  # çok uzak, ekranda anlamsız
            kayit["varislar"].append({
                "kaynak": "tarife", "guven": guven, "yontem": yontem,
                "kalkis": saat, "varis": varis.strftime("%H:%M"),
                "alt": (kalkis + timedelta(minutes=alt_dk)).strftime("%H:%M"),
                "ust": (kalkis + timedelta(minutes=ust_dk)).strftime("%H:%M"),
                "dakika": round((varis - an).total_seconds() / 60),
                "sure_dk": round(dk),
                "not": aciklama})

        # ── ⭐⭐ SON SEFER (9 Ekim · gerekçe SON_SEFER_ERKEN_DK'da) ──────────────
        son_sefer = None if kayit["varislar"] else _son_sefer(dz, hat, yon, durak_kodu, sira, an)
        if son_sefer is not None:
            # Bugünün seferleri bitti: "ortalama X dk beklersin" de artık geçersiz.
            kayit["gozlem"] = None
            # ⚠️ Eski uygulama bu satır türünü tanımıyor: `dakika` 0 olduğu için
            #    "şimdi" yazardı. Yalnız tanıyan sürüme gidiyor; eskisi kartı hiç
            #    görmüyor — hayalet "~8 dk"dan iyidir.
            if surum >= 2:
                kayit["varislar"].append(son_sefer)

        # Canlı araç da yakın tarife de yoksa, GÖZLEMDEN sıradaki geçişi kestir.
        # "Bu durakta bu saatte ortalama 20 dk'da bir geçiyor, sonuncusu 12 dk önceydi"
        # → sıradaki ~8 dakika içinde. Tarifenin sustuğu yerde tek anlamlı cevap bu.
        # ⚠️⚠️ 9 Ekim: YALNIZ arşivde planı OLMAYAN hatlarda (binde 1). Plan varsa
        #    sefer listesi biliniyor; plan susuyorsa "şu an yakında sefer yok"
        #    demektir — kör tahmin gece %65 hayalet gösteriyordu (Bölüm 86).
        elif (not kayit["varislar"] and kayit.get("gozlem")
              and DNV.planli_seferler(dz, hat, yon, an) is None):
            g = kayit["gozlem"]
            son = g.get("son_gecis_dk")
            if son is not None and son < 180:
                # Son geçiş, ortalama aralıktan uzun süre önceyse otobüs GECİKMİŞ
                # demektir. "şimdi" demek fazla iddialı olur; ayrı işaretliyoruz.
                kalan = g["aralik_dk"] - son
                gecikmis = kalan <= 0
                kayit["varislar"].append({
                    "kaynak": "gozlem", "guven": "orta",
                    "dakika": max(0, kalan), "gecikmis": gecikmis,
                    "aralik_dk": g["aralik_dk"], "son_gecis_dk": son,
                    "not": "%d ölçümün ortancası · tarifede bu saatte kalkış yok" % g["olcum"]})

        if kayit["varislar"] or kayit.get("gozlem"):
            kayit["varislar"].sort(key=_sira)
            kayit["varislar"] = _tarife_gurultusunu_at(kayit["varislar"])
            sonuc["hatlar"].append(kayit)

    sonuc["hatlar"] = _ayni_hat_kartlarini_birlestir(sonuc["hatlar"])

    # ⚠️ Sıralama "dakika"ya göre yapılınca GECİKMİŞ satırlar (0 dk) 1 dakika sonra
    #    gelen otobüsün önüne geçiyordu. Yolcu için önemli olan gelen otobüs;
    #    gecikmiş hat bir uyarı, bir varış değil. Gecikmişler sona atılıyor.
    sonuc["hatlar"].sort(key=lambda h: _sira(h["varislar"][0]) if h["varislar"] else (9, 999))
    return sonuc


# ─────────────────────────────────────────────────────────────────────────────
# ERİŞİM ANAHTARI — sunucu internete açıldığında tek koruma
# ─────────────────────────────────────────────────────────────────────────────

#: Anahtar DOSYADA durur, kodda değil (`veri/anahtar.txt`, izin 0600).
#: ⚠️⚠️ NEDEN İSTİSNA YOK — "yerel ağdan gelene sorma" kuralı koymak CAZİP ama
#:   YANLIŞ olurdu: Cloudflare tüneli sunucuya 127.0.0.1 üzerinden bağlanır,
#:   yani tünelden gelen istek YEREL GÖRÜNÜR. Localhost'u muaf tutsaydık
#:   korumanın tam da koruması gereken yol muaf kalırdı.
_ANAHTAR_DOSYA = VERI / "anahtar.txt" if "VERI" in dir() else Path(__file__).parent / "veri" / "anahtar.txt"
_anahtar_onbellek = None


def erisim_anahtari():
    """Dosyadaki anahtarı okur. Dosya yoksa None → koruma kapalı demektir."""
    global _anahtar_onbellek
    if _anahtar_onbellek is None:
        try:
            _anahtar_onbellek = _ANAHTAR_DOSYA.read_text(encoding="utf-8").strip()
        except Exception:
            _anahtar_onbellek = ""
    return _anahtar_onbellek or None


def anahtar_gecerli(istek):
    """İsteğin anahtarı doğru mu?

    Anahtar BAŞLIKTA taşınır (`X-Anahtar`), sorgu dizesinde değil: URL'ler
    günlüklere, tarayıcı geçmişine ve ara sunucu kayıtlarına düşer.

    Karşılaştırma `hmac.compare_digest` ile yapılıyor — normal `==` karakter
    karakter kıyaslayıp ilk farkta durur ve geçen süreden anahtarın ne kadarının
    doğru olduğu sızdırılabilir (zamanlama saldırısı).
    """
    beklenen = erisim_anahtari()
    if not beklenen:
        return True                      # anahtar kurulmamış → koruma kapalı
    gelen = istek.headers.get("X-Anahtar", "")
    return hmac.compare_digest(gelen, beklenen)


def tunel_adresi():
    """Cloudflare tünelinin ŞU ANKİ genel adresi — yoksa None.

    ⭐ NEDEN VAR (4 Ekim, Mehmet'in isteği):
      *"telefon mac ayrı iplerdeyken uygulama çalışıcak hale getiricez"*

    ⚠️⚠️ ÜCRETSİZ TÜNELİN ADRESİ HER BAŞLANGIÇTA DEĞİŞİYOR. Sabit adres için
    Cloudflare hesabı + alan adı gerekiyor. Onun yerine: telefon EV AĞINDAYKEN
    (`.local` ile bağlıyken) buradan güncel adresi öğrenip saklıyor, dışarıda
    onu kullanıyor. Yani kullanıcı eve her geldiğinde adres kendiliğinden
    tazeleniyor.

    Adres cloudflared'in günlüğünden okunuyor. ⚠️ Günlük, servis her başladığında
    SIFIRLANIYOR (plist'te `: > veri/tunel.log`) — yoksa eski ve yeni adresler
    birikir ve hangisinin güncel olduğu anlaşılmazdı. 3 Ekim'de tam bu oldu:
    iki adres birikti, eski olanı seçildi ve istekler 530 döndü.
    """
    try:
        g = (VERI / "tunel.log").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    bulunan = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", g)
    return bulunan[-1] if bulunan else None


class Sunucu(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass                              # sessiz

    def _json(self, veri, kod=200):
        gövde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(gövde)))
        self.end_headers()
        try:
            self.wfile.write(gövde)
        except (BrokenPipeError, ConnectionResetError):
            # ⚠️ 3 Eylül: telefon isteği iptal edince (ekran değişimi, yenileme)
            #    bağlantı kopuyor ve `wfile.write` BrokenPipe atıyordu. Bu istisna
            #    iş parçacığını çökertiyor, arka arkaya gelince sunucu ölüyordu.
            #    İstemcinin gitmesi HATA DEĞİL — sessizce geçilmeli.
            pass

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        # ⚠️ Koruma /api/ altındaki HER uçta. Sağlık yolu (/saglik) muaf: tünelin
        #    ayakta olup olmadığı anahtarsız öğrenilebilmeli, ama o uç veri
        #    döndürmüyor — yalnız "çalışıyor" diyor.
        if u.path.startswith("/api/") and not anahtar_gecerli(self):
            return self._json({"hata": "erişim anahtarı geçersiz"}, 401)
        if u.path == "/saglik":
            return self._json({"durum": "calisiyor"})
        try:
            if u.path == "/api/ara":
                # Konum isteğe bağlı: gelirse sonuçlar uzaklıkla zenginleşir.
                try:
                    e, b = float(q["e"][0]), float(q["b"][0])
                except (KeyError, ValueError, IndexError):
                    e = b = None
                return self._json(durak_ara(q.get("q", [""])[0], enlem=e, boylam=b))
            if u.path == "/api/yakin":
                return self._json(yakin_duraklar(float(q.get("e", ["0"])[0]),
                                                 float(q.get("b", ["0"])[0])))
            if u.path == "/api/tunel":
                # Telefon bunu EV AĞINDAYKEN çağırıp saklıyor (gerekçe yukarıda).
                a = tunel_adresi()
                # ⭐ 8 Ekim: panonun adı da veriliyor — telefon onu da evdeyken
                #    öğrenip saklıyor (pano.py). Kodda gömülü değil: değişebilsin.
                try:
                    import pano
                    konu = pano.konu()
                except Exception:
                    konu = None
                return self._json({"adres": a, "pano": konu} if a else
                                  {"adres": None, "pano": konu, "not": "tünel çalışmıyor"})
            if u.path == "/api/sefer":
                r = sefer_konumu(q.get("hat", [""])[0], q.get("yon", [""])[0],
                                 q.get("kalkis", [""])[0], q.get("durak", [None])[0])
                return self._json(r or {"hata": "sefer bulunamadı"}, 200 if r else 404)
            if u.path == "/api/hat":
                r = hat_seferleri(q.get("hat", [""])[0], q.get("yon", [""])[0],
                                  q.get("durak", [""])[0], q.get("gun", [None])[0])
                return self._json(r or {"hata": "hat bulunamadı"}, 200 if r else 404)
            if u.path == "/api/arac":
                r = arac_detay(q.get("kapino", [""])[0], q.get("hat", [""])[0],
                               q.get("yon", [""])[0], q.get("durak", [None])[0])
                return self._json(r or {"hata": "araç bulunamadı"}, 200 if r else 404)
            if u.path == "/api/durak":
                kod = q.get("kod", [""])[0]
                saat = q.get("saat", [None])[0]
                an = None
                if saat and ":" in saat:
                    s, d = saat.split(":")
                    an = datetime.now().replace(hour=int(s), minute=int(d), second=0, microsecond=0)
                try:
                    surum = int(q.get("surum", ["1"])[0])
                except ValueError:
                    surum = 1
                r = durakta_ne_var(kod, an, surum)
                return self._json(r or {"hata": "durak bulunamadı"}, 200 if r else 404)
        except Exception as e:
            return self._json({"hata": str(e)[:200]}, 500)
        # Yalnızca arayüz sayfası sunulur; klasör listelenmez.
        if u.path in ("/", "/arayuz.html"):
            try:
                govde = SAYFA.read_bytes()
            except OSError:
                return self._json({"hata": "arayuz.html bulunamadı"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)
            return
        self.send_response(404); self.end_headers()


def on_isit():
    """⚠️ AÇILIŞTA ROTA GEOMETRİSİNİ YÜKLE (3 Eylül).

    Ölçüldü: sunucu yeniden başladıktan sonra İLK durak sorgusu 34 saniye,
    sonrakiler 0,07 sn. Fark, 676 hattın rota geometrisinin ilk çağrıda belleğe
    yüklenmesi. O 34 saniye boyunca telefon zaman aşımına uğrayıp
    **"Sunucuya ulaşılamadı"** diyordu — kullanıcının gördüğü hata buydu.

    launchd servisi çökünce/yeniden başlayınca bu her seferinde yaşanır, yani
    kullanıcı hatayı tam da sistemin kendini toparladığı anda görür.

    Çözüm: yükleme portu dinlemeden ÖNCE yapılır. Sunucu geç açılır ama
    açıldığı anda hazırdır — yarım hazır bir sunucudan iyidir.
    """
    import time
    t0 = time.time()
    try:
        rota.durak_mesafeleri("98", "D")          # geometri önbelleğini doldurur
        _trafik_getir()                           # şehir geneli tek değer — baştan dolsun
        # ⭐ TÜM rota ızgaraları (7 Ekim) — ölçüldü, 1.300 hat-yön 0,35 sn.
        #    Bunsuz her hattın ızgarası o hatta ilk sorulduğunda kuruluyordu;
        #    sunucu yeniden başladıktan sonraki ilk istekler yavaş kalıyordu.
        for _h, _yonler in rota._rotalar().items():
            for _y in _yonler:
                try:
                    rota._izgara(_h, _y)
                except Exception:
                    pass
        # ⭐ TÜM hatların parça süre önbelleği — ölçüldü, yalnızca 1,4 sn.
        #    Bunsuz her YENİ durak ilk açılışında ~20 sn sürüyordu: 7 GB'lık
        #    veritabanından soğuk disk okuması. İkinci açılışta 0,1 sn, çünkü
        #    işletim sistemi önbelleği doluyor. Yolcu ilk açılışı bekliyordu.
        kdb = DNV._kayit_db()
        for (h,) in kdb.execute("SELECT DISTINCT hat FROM parca_sure_genel"):
            for y in ("G", "D"):
                sure_modeli._parcalar(kdb, h, y, "I")
        durakta_ne_var("124081")                  # tüm zinciri bir kez ısıtır
        print("ön ısıtma tamam · %.1f sn" % (time.time() - t0))
    except Exception as e:
        # Isınma başarısız olsa da sunucu açılmalı; ilk istek yavaş olur, o kadar.
        print("⚠️ ön ısıtma atlandı (%s) — ilk istek yavaş olabilir" % str(e)[:80])


if __name__ == "__main__":
    print("arayüz sunucusu · http://localhost:%d" % PORT)
    print("telefondan: http://<yerel-IP>:%d   (ipconfig getifaddr en0)" % PORT)
    # ⚠️⚠️ ISITMA ARKA PLANDA (3 Eylül, ikinci düzeltme): ilk sürümde ısıtma
    #    portu açmadan ÖNCE yapılıyordu. Isıtma disk/kilit yüzünden bazen
    #    135 saniye sürdü ve o boyunca port HİÇ AÇILMADI — telefon
    #    "Sunucuya ulaşılamadı" diyordu. Yani ısıtma, çözmeye çalıştığı
    #    sorunun daha kötüsünü yarattı.
    #    Artık port hemen açılıyor, ısıtma paralel koşuyor: ilk birkaç istek
    #    yavaş olabilir ama BAĞLANTI KURULUR. Yavaş cevap, cevapsızlıktan iyi.
    threading.Thread(target=on_isit, daemon=True).start()
    print("durdurmak için Ctrl+C\n")
    class DayanikliSunucu(ThreadingHTTPServer):
        """⚠️ Tek bir isteğin hatası TÜM SUNUCUYU öldürmemeli.
        `daemon_threads` açık olmadan çöken iş parçacıkları birikiyor,
        `handle_error` susturulmadan her kopan bağlantı yığın izi basıyordu."""
        daemon_threads = True
        def handle_error(self, request, client_address):
            import sys, traceback
            t = sys.exc_info()[0]
            if t in (BrokenPipeError, ConnectionResetError):
                return                      # istemci gitti, olağan
            traceback.print_exc()

    DayanikliSunucu(("0.0.0.0", PORT), Sunucu).serve_forever()

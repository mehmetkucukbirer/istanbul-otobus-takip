"""
YÖN TESPİTİ — araç hangi bacakta ilerliyor?

SORUN:
  `guzergahkodu` alanının orta harfi (98_G_D7742 → G) yönü verir SANILIYOR ama
  vermiyor. Gidiş+dönüşü tek sefer sayan varyantlarda araç turun ikinci yarısında
  ters bacakta ilerlerken etiket hâlâ ilk yönü gösteriyor. Eski projede ölçülmüştü:
  98'in kalkışlarının %91'i "G" etiketli.

  Yanlış yön = "otobüs gelmiyor" derken aslında geliyor olması. Uygulamanın var
  oluş sebebine doğrudan ters, o yüzden düzgün çözülmesi gerekiyor.

YÖNTEM — İLERLEME TESTİ (açı hesabı yerine):
  Aracın ardışık konumlarını HER İKİ rotaya da izdüşürüyoruz.
    · doğru bacakta  → rota üzerindeki mesafe ARTAR   (ilerleme +)
    · ters bacakta   → mesafe AZALIR                  (ilerleme −)
  "İlerleme ÷ gerçek yer değiştirme" oranı doğru bacakta +1'e yakın çıkar.

  Açıyla uğraşmaya gerek yok; işaret ve büyüklük yetiyor. Ayrıca bu ölçü
  izdüşüm sapmasını da kendiliğinden cezalandırıyor: araç o rotanın üzerinde
  değilse izdüşümü zıplar, oran 1'den uzaklaşır.

ÜÇ KADEME (birincisi karar veremezse ikinciye düşer):
  1. İlerleme testi          — en güvenilir, hareket gerektirir
  2. İzdüşüm sapması         — duran araçta çalışır, ortak güzergâhta zayıf
  3. guzergahkodu harfi      — son çare
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import math
import rota

VERI = Path(__file__).parent / "veri"

EN_AZ_YER_DEGISTIRME_M = 60      # bundan azı gürültü — eski projede ölçülmüştü
EN_AZ_UYUM = 0.5                 # ilerleme/yer değiştirme oranı eşiği
SAPMA_KARAR_ORANI = 2.0          # 2. kademe: bir rota diğerinden bu kat daha yakınsa
SAPMA_KARAR_FARKI_M = 20.0       # ve fark en az bu kadarsa karar verilir


ESLEME_MAX_YAS_DK = 180      # bundan eski araç→hat eşlemesi şüpheli sayılır
IZ_PENCERESI_DK = 20         # yön ve hız hesabı için geriye kaç dakika bakılır


# ⚠️ PERFORMANS — 1 Eylül'de profille bulundu.
#   Her çağrıda yeni bağlantı açılıyordu: tek durak sorgusunda 704 kez
#   sqlite3.connect, 3,8 saniye. Bağlantı artık iş parçacığı başına bir kez
#   açılıp yeniden kullanılıyor (sunucu çok iş parçacıklı, paylaşmak güvenli değil).
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


def _db():
    """İş parçacığı başına bir bağlantı — gerekçe yukarıda."""
    b = getattr(_yerel, "kayit", None)
    if b is None:
        b = sqlite3.connect(str(VERI / "kayit.db"), timeout=30)
        b.execute("PRAGMA busy_timeout=30000")
        _yerel.kayit = b
    return b


def arac_izi(kapino, adet=12, guzergahkodu=None, an=None):
    """Aracın son N konum bildirimi, eskiden yeniye.

    `konum_birlesik` görünümünden okunuyor: hem yeni şehir geneli tablo
    (`filo_konum`) hem eski hat bazlı tablo (`konum`, 26/27 Ağustos gecesi).
    Aynı ana ait iki kayıt varsa biri eleniyor.
    """
    an = an or datetime.now()
    esik = (an - timedelta(minutes=IZ_PENCERESI_DK)).strftime("%Y-%m-%d %H:%M:%S")
    satir = _db().execute(
        "SELECT zaman, enlem, boylam FROM konum_birlesik"
        " WHERE kapino=? AND zaman >= ? AND zaman <= ? AND enlem IS NOT NULL"
        " ORDER BY zaman DESC LIMIT ?",
        (kapino, esik, an.strftime("%Y-%m-%d %H:%M:%S"), adet * 2)).fetchall()

    gorulen, iz = set(), []
    for zaman, enlem, boylam in reversed(satir):
        if zaman in gorulen:
            continue                      # iki tablodan gelen aynı an
        gorulen.add(zaman)
        iz.append((zaman, enlem, boylam, guzergahkodu))
    return iz[-adet:]


def _yer_degistirme_m(hat, yon, iz):
    """İzin ilk ve son noktası arasındaki gerçek yer değiştirme (düzlemde, metre)."""
    _, _, enlem0 = rota.yol(hat, yon)
    x1, y1 = rota._duzleme(iz[0][2], iz[0][1], enlem0)
    x2, y2 = rota._duzleme(iz[-1][2], iz[-1][1], enlem0)
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def _bacak_puani(hat, yon, iz):
    """Bir bacak için (uyum, ortalama sapma, yer değiştirme) döndürür.

    uyum = rota üzerindeki ilerleme ÷ gerçek yer değiştirme
           +1'e yakın → araç bu bacakta ileri gidiyor
           -1'e yakın → bu bacağın tersine gidiyor (yani öbür bacakta)
    """
    izdusumler = [rota.yol_uzerinde(hat, yon, b, e) for _, e, b, _ in iz]
    mesafeler = [m for m, _ in izdusumler]
    sapmalar = [s for _, s in izdusumler]
    yer_deg = _yer_degistirme_m(hat, yon, iz)
    ilerleme = mesafeler[-1] - mesafeler[0]
    uyum = (ilerleme / yer_deg) if yer_deg > 0 else 0.0
    return uyum, sum(sapmalar) / len(sapmalar), yer_deg


def yon_bul(hat, iz, etiket_yonu=None):
    """Aracın hangi bacakta olduğunu belirler.

    Döner: (yon, yontem, ayrinti)  ·  yon None ise karar verilemedi
    """
    bacaklar = [y for y in ("G", "D") if hat in rota._rotalar() and y in rota._rotalar()[hat]]
    if not bacaklar:
        return None, "rota yok", {}
    if len(bacaklar) == 1:
        return bacaklar[0], "tek bacak", {}
    if len(iz) < 2:
        return (etiket_yonu, "etiket", {}) if etiket_yonu else (None, "iz yok", {})

    puanlar = {y: _bacak_puani(hat, y, iz) for y in bacaklar}

    # ── 1. KADEME: ilerleme testi ────────────────────────────────────────────
    hareketli = {y: p for y, p in puanlar.items() if p[2] >= EN_AZ_YER_DEGISTIRME_M}
    if hareketli:
        aday = max(hareketli.items(), key=lambda kv: kv[1][0])
        if aday[1][0] >= EN_AZ_UYUM:
            return aday[0], "hareket", {
                "uyum": aday[1][0], "sapma": aday[1][1], "yer_degistirme": aday[1][2],
                "diger": {y: round(p[0], 2) for y, p in puanlar.items() if y != aday[0]}}

    # ── 2. KADEME: izdüşüm sapması ───────────────────────────────────────────
    sirali = sorted(puanlar.items(), key=lambda kv: kv[1][1])
    en_yakin, ikinci = sirali[0], sirali[1]
    if (ikinci[1][1] >= en_yakin[1][1] * SAPMA_KARAR_ORANI
            and ikinci[1][1] - en_yakin[1][1] >= SAPMA_KARAR_FARKI_M):
        return en_yakin[0], "sapma", {
            "sapma": en_yakin[1][1], "diger_sapma": ikinci[1][1]}

    # ── 3. KADEME: etiket ────────────────────────────────────────────────────
    if etiket_yonu in bacaklar:
        return etiket_yonu, "etiket", {}
    return None, "kararsız", {}


def arac_hizi(hat, yon, iz):
    """Aracın KENDİ izinden ölçülen anlık hızı (m/dakika).

    NEDEN ÖNEMLİ: bu, tarifeden gelen ortalama hız değil — o aracın ŞU ANKİ
    trafikte gerçekte ne kadar ilerlediği. Otobüsü hareketli bir trafik sensörü
    gibi kullanıyoruz. Yol bazında canlı trafik verisi açık veride yok (404),
    dolayısıyla trafiği ancak böyle görebiliyoruz.

    Döner: (m_dakika, kullanilan_sure_dk, ilerleme_m) · ölçülemezse None
    """
    if len(iz) < 2:
        return None
    t0 = datetime.strptime(iz[0][0], "%Y-%m-%d %H:%M:%S")
    t1 = datetime.strptime(iz[-1][0], "%Y-%m-%d %H:%M:%S")
    dakika = (t1 - t0).total_seconds() / 60.0
    if dakika < 1:
        return None
    bas = rota.yol_uzerinde(hat, yon, iz[0][2], iz[0][1])[0]
    son = rota.yol_uzerinde(hat, yon, iz[-1][2], iz[-1][1])[0]
    ilerleme = son - bas
    if ilerleme <= 0:
        return None                      # geri gitmiş görünüyor — ölçüm güvenilmez
    hiz = ilerleme / dakika
    # akıl sağlığı bandı: 2-70 km/sa dışı şehir içi otobüs için gerçekçi değil
    if not (33 <= hiz <= 1167):
        return None
    return hiz, dakika, ilerleme


def hatta_atanmis_araclar(hat, an=None, yas_dk=ESLEME_MAX_YAS_DK):
    """Şu anda bu hatta çalışan araçlar + eşlemenin yaşı (dakika).

    ⚠️ Neden "son eşlemesi bu hat olan" diye soruyoruz da "bu hatta görülmüş"
    demiyoruz: araçlar hat değiştiriyor (14 günde araçların %90'ı birden fazla
    hatta çalışmış). Araç saat 08'de 98'de, saat 11'de 89'da olabilir. Sadece
    EN SON eşlemesi bu hat olanlar sayılır.
    """
    an = an or datetime.now()
    esik = (an - timedelta(minutes=yas_dk)).strftime("%Y-%m-%d %H:%M:%S")
    simdi_m = an.strftime("%Y-%m-%d %H:%M:%S")
    db = _db()
    # ⚠️ ESKİ SORGU TÜM TABLOYU TARIYORDU: önce her aracın MAX(zaman)'ı hesaplanıp
    #    sonra hatta göre süzülüyordu — arac_hat büyüdükçe (200 bin+ satır) çöktü,
    #    tek durak sorgusunda 29 saniye. Şimdi önce HATTA göre süzülüyor (indeksli),
    #    sonra her aday için "daha yeni bir ataması var mı" diye bakılıyor.
    satir = db.execute("""
        SELECT a.kapino, a.guzergahkodu, a.zaman
          FROM arac_hat a
         WHERE a.hat = ? AND a.zaman >= ? AND a.zaman <= ?
           AND NOT EXISTS (SELECT 1 FROM arac_hat b
                            WHERE b.kapino = a.kapino
                              AND b.zaman > a.zaman AND b.zaman <= ?)
         GROUP BY a.kapino""", (hat, esik, simdi_m, simdi_m)).fetchall()

    if not satir:
        satir = db.execute(
            "SELECT DISTINCT kapino, guzergahkodu, MAX(damga) FROM konum"
            " WHERE hat=? AND damga >= ? AND damga <= ? GROUP BY kapino",
            (hat, esik, simdi_m)).fetchall()
    return [(k, g, z, (an - datetime.strptime(z, "%Y-%m-%d %H:%M:%S")).total_seconds() / 60)
            for k, g, z in satir]


def hattaki_araclar(hat, an=None):
    """Hattaki araçlar: yönü hareketten tespit edilmiş, hızı kendi izinden ölçülmüş."""
    an = an or datetime.now()
    sonuc = []
    for kapino, gkod, esleme_zamani, yas_dk in hatta_atanmis_araclar(hat, an):
        iz = arac_izi(kapino, guzergahkodu=gkod, an=an)
        if not iz:
            continue
        etiket = gkod.split("_")[1] if gkod and "_" in gkod else None
        yon, yontem, ayrinti = yon_bul(hat, iz, etiket)
        hiz = arac_hizi(hat, yon, iz) if yon else None
        # ⭐ İzin baştan sona kuş uçuşu yer değiştirmesi (7 Ekim). Kullanan:
        #    arayuz_sunucu — duran aracı "canlı yaklaşan" saymamak için.
        #    Ek sorgu yok: iz zaten son IZ_PENCERESI_DK dakikayı kapsıyor.
        hareket_m = round(math.hypot((iz[-1][1] - iz[0][1]) * 111000,
                                     (iz[-1][2] - iz[0][2]) * 83000))
        # ⭐ İzdeki EN UZAK noktanın son konuma uzaklığı (7 Ekim). Duran aracı
        #    ayırmak için asıl ölçü bu; `hareket_m` (ilk-son) yalnız bilgi.
        #    Neden: ilk-son, 20 dk içinde gidip başladığı yere dönen aracı
        #    (son durakta dönüş, ring güzergâh) DURUYOR sanıyordu — ölçüldü,
        #    55T/B-1756 ilk-son 102 m ama arada 1.518 m uzaklaşmış, dakikada
        #    bir kayıt. Duran araç hiç uzaklaşmaz; dönen araç uzaklaşıp gelir.
        en_uzak_m = round(max(math.hypot((p[1] - iz[-1][1]) * 111000,
                                         (p[2] - iz[-1][2]) * 83000) for p in iz))
        sonuc.append({"kapino": kapino, "enlem": iz[-1][1], "boylam": iz[-1][2],
                      "damga": iz[-1][0], "guzergahkodu": gkod, "etiket_yonu": etiket,
                      "yon": yon, "yontem": yontem, "ayrinti": ayrinti,
                      "iz_uzunlugu": len(iz), "hiz": hiz, "hareket_m": hareket_m, "en_uzak_m": en_uzak_m,
                      "esleme_yasi_dk": yas_dk})
    return sonuc


if __name__ == "__main__":
    hat = sys.argv[1] if len(sys.argv) > 1 else "98"
    araclar = hattaki_araclar(hat)
    print("\n%s hattı · %d araç\n" % (hat, len(araclar)))
    print("araç      etiket  TESPİT  yöntem    ayrıntı")
    print("-" * 78)
    for a in sorted(araclar, key=lambda x: x["kapino"]):
        ay = a["ayrinti"]
        if a["yontem"] == "hareket":
            ek = "uyum %+.2f · %.0f m hareket · diğer bacak %s" % (
                ay["uyum"], ay["yer_degistirme"], ay["diger"])
        elif a["yontem"] == "sapma":
            ek = "sapma %.0f m · diğer bacak %.0f m" % (ay["sapma"], ay["diger_sapma"])
        else:
            ek = ""
        uyari = "  ← ETİKET YANLIŞ" if (a["yon"] and a["etiket_yonu"]
                                        and a["yon"] != a["etiket_yonu"]) else ""
        print("%-9s %-7s %-7s %-9s %s%s"
              % (a["kapino"], a["etiket_yonu"] or "-", a["yon"] or "?", a["yontem"], ek, uyari))
    n_ters = sum(1 for a in araclar if a["yon"] and a["etiket_yonu"]
                 and a["yon"] != a["etiket_yonu"])
    print("\n%d araçtan %d'sinde etiket yanlış çıktı." % (len(araclar), n_ters))
    for y in ("hareket", "sapma", "etiket", "kararsız"):
        n = sum(1 for a in araclar if a["yontem"] == y)
        if n:
            print("  %-9s %d araç" % (y, n))

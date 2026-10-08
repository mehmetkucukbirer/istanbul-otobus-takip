"""
DURAKTA NE VAR — uygulamanın çekirdek sorusunu cevaplayan ilk uçtan uca çıktı.

    python3 durakta_ne_var.py 124081          # şu an
    python3 durakta_ne_var.py 124081 23:20    # belirli bir saatte

DÖRT KAYNAĞI BİRLEŞTİRİYOR:
    dizin.db  hat_durak  → bu duraktan hangi hatlar geçer, kaçıncı durak
    dizin.db  tarife     → o hatlar bugün saat kaçta kalkıyor
    dizin.db  sefer      → o kalkışlar gerçekte kaç dakika sürüyor + kaç kez yapılmıyor
    kayit.db  konum      → şu an yolda görünen araçlar nerede
    rota.py              → durağın ve aracın rota üzerindeki yeri

İKİ AYRI CEVAP ÜRETİYOR — ürünün ana fikri bu ayrım:
    CANLI   : araç görünüyor  → konumundan hesaplanır      (güven: yüksek)
    TARİFE  : araç görünmüyor → plandan tahmin edilir      (güven: düşük/orta)
              ↑ "Otobüsüm Nerede"nin sustuğu yer tam burası
"""

import bisect
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import duyurular
import rota
import sure_modeli
import yon_tespit

# motorun yedek hızı: ölçülmüş şehir içi ortalama (m/dakika)
VARSAYILAN_HIZ = 25000 / 60

# Aracın o anki trafiği yalnızca ÖNÜNDEKİ ilk 2 km'yi belirler sayılır;
# ötesi şehir ortalamasına döner. Yedek yolun saçmalamasını önlüyor.
YAKIN_ETKI_M = 2000

VERI = Path(__file__).parent / "veri"

# ⚠️ PERFORMANS (1 Eylül): her yardımcı fonksiyon kendi bağlantısını açıp
#   kapatıyordu. Tek durak sorgusunda yüzlerce bağlantı açılıyordu. Artık
#   iş parçacığı başına tek bağlantı yeniden kullanılıyor.
import threading

# ⚠️ Sunucu her istek için YENİ iş parçacığı açıyor; iş parçacığı-yerel bağlantı
#    her seferinde yeniden kuruluyordu. Veritabanı WAL kipinde ve bu sorgular
#    salt okuma — tek bağlantıyı kilitle paylaşmak hem güvenli hem hızlı.
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


def _kayit_db():
    """İş parçacığı başına bir bağlantı — gerekçe yukarıda."""
    b = getattr(_yerel, "kayit", None)
    if b is None:
        yol = VERI / "kayit.db"
        if not yol.exists():
            return None
        b = sqlite3.connect(str(yol), timeout=30)
        b.execute("PRAGMA busy_timeout=30000")
        _yerel.kayit = b
    return b
YAKIN_SAPMA_M = 300          # araç rotadan bu kadar uzaksa "bu rotada değil" sayılır
AZ_ORNEK = 5                 # bir tahmin için gereken en az gözlem sayısı

# ⭐⭐ SAĞLAM SAAT DİLİMİ EŞİĞİ (8 Eylül, Mehmet'in tespiti)
#
#   *"verinin düzgün toplanmadığı günler, sadece düzgün toplanan saatler için
#     işlem yapacaksın. 13.00-15.00 arası güzel veri toplanmış, işlem yaparsın;
#     ama 17.00-23.00 kesik kesik toplanmışsa o zaman geçen günkü veri kalacak,
#     bir günde o kadar çok fark olmaz."*
#
# ⚠️ NEDEN ŞART: kesinti veriyi yalnızca EKSİLTMİYOR, YANILTICI veri üretiyor.
#    17:05'te bir geçiş kaydedilip sonra kaydedici susarsa ve 17:50'de yeniden
#    kaydederse, sistem "45 dakikada bir geçiyor" der. Oysa gerçekte 5 dakikada
#    bir geçiyordu — sadece kayıt yoktu. Yani kesintili dilimler ortalama aralığı
#    YUKARI çekiyor ve yolcuya "otobüs seyrek" diye yanlış bilgi veriliyor.
#
# ÖLÇÜLDÜ (8 Eylül · son 7 gün · 192 gün-saat dilimi):
#     sağlam (≥45 tur/saat)   138  %72
#     kısmi  (20-44 tur)       16   %8
#     kesintili (<20 tur)      38  %20   ← her beş dilimden biri kirli
#
# Kaydedici uyanıkken DAKİKADA BİR tur atar, yani sağlıklı bir saatte 60 tur
# beklenir. 45 eşiği = %75 kapsama. Bu ölçü otobüs sayısından bağımsız: gece de
# tur atılır, sadece hareketli araç az olur.
SAGLAM_TUR_ESIGI = 45        # bir saat diliminin sayılması için gereken tur sayısı
GOZLEM_GUN = 7               # gözlem için geriye kaç gün bakılır (indeks kullanılabilsin)


# ─────────────────────────────────────────────────────────────────────────────
# VERİ ERİŞİMİ
# ─────────────────────────────────────────────────────────────────────────────

def gun_tipi(t):
    return "C" if t.weekday() == 5 else ("P" if t.weekday() == 6 else "I")


def duraktan_gecen_hatlar(db, durak_kodu):
    return db.execute("""
        SELECT hd.hat_kodu, hd.yon, hd.yon_adi, hd.sira, h.hat_adi,
               (SELECT COUNT(*) FROM hat_durak x
                 WHERE x.hat_kodu=hd.hat_kodu AND x.yon=hd.yon)
        FROM hat_durak hd JOIN hat h ON h.hat_kodu=hd.hat_kodu
        WHERE hd.durak_kodu=? ORDER BY hd.hat_kodu""", (durak_kodu,)).fetchall()


def sonraki_kalkislar(db, hat, yon, gt, andan_itibaren, adet=3):
    """Tarifeden, verilen saatten sonraki ilk kalkışlar."""
    return db.execute("""
        SELECT saat, guzergah FROM tarife
        WHERE hat_kodu=? AND yon=? AND gun_tipi=? AND saat >= ?
        ORDER BY saat LIMIT ?""",
        (hat, yon, gt, andan_itibaren.strftime("%H:%M"), adet)).fetchall()


def olculmus_sure(db, guzergah, saat):
    """O güzergâh varyantının GERÇEK süresi. Önce o saat, yetmezse tümü.

    Yön yerine VARYANT ile gruplanıyor: 98'de yön G altında hem 76 dk'lık tek yön
    hem 185 dk'lık gidiş+dönüş var; varyant kodu bunları ayırıyor (Bölüm 11)."""
    for kosul, par in ((" AND plan_saat=?", (guzergah, saat)), ("", (guzergah,))):
        s = [r[0] for r in db.execute(
            "SELECT sure_dk FROM sefer WHERE guzergah=? AND sure_dk IS NOT NULL" + kosul, par)]
        if len(s) >= AZ_ORNEK:
            s.sort()
            return statistics.median(s), s[len(s)//10], s[-max(1, len(s)//10)], len(s)
    return None


def iptal_orani(db, hat, saat, gt):
    r = db.execute("""SELECT COUNT(*), SUM(CASE WHEN durum!='T' THEN 1 ELSE 0 END)
                      FROM sefer WHERE hat_kodu=? AND plan_saat=? AND gun_tipi=?""",
                   (hat, saat, gt)).fetchone()
    return (r[1] / r[0], r[0]) if r and r[0] else (None, 0)


def esleme_tazeligi(hat):
    """Bu hattın araç eşlemesi en son ne zaman tazelendi? (dakika) · hiç yoksa None.

    Kaydedici v2 şehir geneli konumu dakikada bir alıyor ama HAT BİLGİSİ o serviste
    yok; hangi aracın hangi hatta olduğu ayrı sorgularla, 780 hat SIRAYLA dönülerek
    tazeleniyor (tam tur ~26 saat). Yani bir hattın eşlemesi taze de olabilir,
    saatler öncesine ait de. Bu yaş, cevabın güvenine doğrudan giriyor.
    """
    k = _kayit_db()
    if k is None:
        return None
    r = k.execute("SELECT MAX(zaman) FROM yoklama WHERE hat=? AND sonuc='ok'",
                  (hat,)).fetchone()
    if not r or not r[0]:
        return None
    return (datetime.now() - datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")).total_seconds() / 60


def canli_varis_dk(hat, yon, hedef_sira, arac_m, kalan_m, hiz, an):
    """⭐ Canlı aracın bu durağa kaç dakikada varacağı.

    ⚠️ NEDEN DEĞİŞTİ (4. seans): eski hesap `kalan mesafe ÷ aracın anlık hızı` idi.
    Ölçüldü — 3.312 gerçek varış üzerinde, aracın gerçekten vardığı an biliniyorken
    Δ dakika öncesine dönülerek:

        Δ=15 dk   mesafe÷hız : ortanca |hata| 5,2 dk · ±3 dk içinde %30
                  parça modeli:              1,7 dk ·             %74

    Sebep: aracın son 12 dakikada ölçülen hızı ÖNÜNDEKİ yolun trafiğini bilmiyor.
    Parça modeli biliyor — o parçadan gerçekte kaç dakikada geçildiği günlerdir
    ölçülüyor (Bölüm 35). Model tarife dalına bağlanmıştı, canlı dala unutulmuştu.

    Döner: (dakika, yöntem) · yöntem = "parça" | "hız" | "varsayılan"
    """
    mesafeler = [x[2] for x in rota.durak_mesafeleri(hat, yon)]
    # aracın HENÜZ VARMADIĞI ilk durak — parça toplamı oradan başlar
    sonraki = bisect.bisect_right(mesafeler, arac_m)
    if 1 <= sonraki < hedef_sira:
        r = sure_modeli.varis_suresi(_kayit_db(), hat, yon, sonraki, hedef_sira, an)
        if r:
            dk = r[0]
            # Araç, `sonraki` durağa da varmamış: o parçanın kalan kısmını ekle.
            # Parça modeli durak-durak çalışıyor, araç ise iki durağın arasında.
            onceki_m = mesafeler[sonraki - 2] if sonraki >= 2 else 0.0
            parca_m = mesafeler[sonraki - 1] - onceki_m
            if parca_m > 0 and hiz:
                dk += max(0.0, mesafeler[sonraki - 1] - arac_m) / hiz
            return dk, "parça"
    # ── YEDEK YOL — parça modeli cevap veremiyor (hiç gözlenmemiş parça) ──────
    # ⚠️ Ham `kalan ÷ anlık hız` burada çöküyordu: 89S'de araç 11,44 km uzakta
    #    ve o an 2 km/sa ölçülmüş → 323 DAKİKA çıkıyordu. Otobüs 11 km boyunca
    #    2 km/sa gitmez; o ölçüm bir kırmızı ışık ya da tıkanma.
    #
    # Çözüm — mesafeye göre harmanlama: içinde bulunduğu trafik YAKIN yolu belirler,
    # uzak yol zamanla normale döner. İlk YAKIN_ETKI_M anlık hızla, gerisi şehir
    # ortalamasıyla hesaplanıyor.
    yakin = min(kalan_m, YAKIN_ETKI_M)
    uzak = max(0.0, kalan_m - YAKIN_ETKI_M)
    dk = yakin / max(hiz, 1.0) + uzak / VARSAYILAN_HIZ
    return dk, ("hız" if hiz != VARSAYILAN_HIZ else "varsayılan")


GPS_ESLESME_TOLERANS_DK = 6   # görünen araçla kalkışı eşleştirme payı
GPS_EN_AZ_ARALIK_DK = 12      # bundan sık hatta tek tek sefer iddiası yok (Bölüm 25)


def yoldaki_gorunmeyenler(dz, hat, yon, hedef_sira, an, gt, gorunen_varislar, iptaller=None):
    """⭐⭐ GPS'İ KAPALI OTOBÜS — ürünün asıl vaadi (PROMPT Bölüm 2).

    ⚠️ NEDEN GEREKLİ: motor bugüne kadar yalnızca GELECEK kalkışlara bakıyordu
    (`saat >= şimdi`). 20 dakika önce kalkmış, yolda olan ama GPS'i susmuş otobüs
    hiç hesaba katılmıyordu. Sefaköy'de ölçüldü: 15:35'te üç sefer yoldaydı
    (varış 16, 19, 36 dk sonra) ve uygulama hiçbirini göstermiyordu.
    Referans senaryonun (98 · 23:30 · Sefaköy) tam olarak bu olması gerekiyordu.

    YÖNTEM — sayarak, tek tek atayarak değil:
      1. Bu durağa kalkıştan kaç dakikada gelindiğini parça modelinden al.
      2. O kadar geriye bakıp, varışı HÂLÂ GELECEKTE olan kalkışları bul (yolda).
      3. İptali duyurulmuşları çıkar — onlar gelmiyor.
      4. Görünen araçların tahmini varışlarıyla sırayı bozmadan eşleştir.
      5. Eşleşmeden kalanlar = yolda ama görünmeyen → GPS karanlığı.

    ⚠️ SIK SEFERLİ HATTA İDDİA YOK: aralık 12 dk'nın altındaysa hangi seferin
    görünmediği ayırt edilemiyor (Bölüm 25'te ölçüldü, 500T'de yöntem çökmüştü).

    Döner: [(kalkis_saati, tahmini_varis, dakika), ...]
    """
    r = sure_modeli.varis_suresi(_kayit_db(), hat, yon, 1, hedef_sira, an)
    if not r:
        return []
    yol_dk = r[0]
    bas = (an - timedelta(minutes=yol_dk)).strftime("%H:%M")
    simdi = an.strftime("%H:%M")
    if bas >= simdi:
        return []                       # gece yarısını aşıyor — karışmasın, atla
    kalkislar = [x[0] for x in dz.execute(
        "SELECT saat FROM tarife WHERE hat_kodu=? AND yon=? AND gun_tipi=?"
        " AND saat >= ? AND saat < ? ORDER BY saat", (hat, yon, gt, bas, simdi))]
    if len(kalkislar) < 2:
        aralik = None
    else:
        dk = lambda s: int(s[:2]) * 60 + int(s[3:5])
        farklar = [dk(b) - dk(a) for a, b in zip(kalkislar, kalkislar[1:])]
        aralik = statistics.median(farklar)
        if aralik < GPS_EN_AZ_ARALIK_DK:
            return []                   # sık seferli hat — ayırt edilemez

    yolda = []
    for s in kalkislar:
        if iptaller and (hat, yon, s[:5]) in iptaller.get("kesin", {}):
            continue                    # iptal duyurulmuş, gelmiyor
        kalkis = an.replace(hour=int(s[:2]) % 24, minute=int(s[3:5]),
                            second=0, microsecond=0)
        rr = sure_modeli.varis_suresi(_kayit_db(), hat, yon, 1, hedef_sira, kalkis)
        if not rr:
            continue
        varis = kalkis + timedelta(minutes=rr[0])
        if varis > an:
            yolda.append((s[:5], varis, (varis - an).total_seconds() / 60))
    if not yolda:
        return []

    # Görünen araçlarla sırayı bozmadan eşleştir; eşleşmeyenler karanlıkta.
    # (Bölüm 24: açgözlü eşleştirme çökmüştü, sıra koruyan hizalama doğru araç.)
    gorunen = sorted(gorunen_varislar)
    kalan, i = [], 0
    for s, varis, dakika in sorted(yolda, key=lambda t: t[2]):
        if i < len(gorunen) and abs(gorunen[i] - dakika) <= GPS_ESLESME_TOLERANS_DK:
            i += 1                      # bu kalkış görünen araçla açıklandı
        else:
            kalan.append((s, varis, dakika))
    return kalan


def canli_araclar(hat, an=None):
    """Yönü GERÇEK HAREKETTEN tespit edilmiş, hızı kendi izinden ölçülmüş araçlar.

    Yön için `guzergahkodu` etiketine GÜVENİLMİYOR: ölçüldü (26 Ağustos, 98 hattı),
    10 aracın 10'u "G" etiketliyken 5'i gerçekte D bacağındaydı. Etikete güvenmek
    duraktaki insanların yarısına yanlış söylemek demekti. Ayrıntı: yon_tespit.py
    """
    return yon_tespit.hattaki_araclar(hat, an)


# ─────────────────────────────────────────────────────────────────────────────
# ÇIKTI
# ─────────────────────────────────────────────────────────────────────────────

_dilim_onbellek = {}


def saglam_dilimler(k, esik):
    """Kaydedicinin düzgün çalıştığı (gün, saat) dilimleri — gerekçe SAGLAM_TUR_ESIGI'nde.

    `yoklama` tablosu küçük (günde ~900 satır), ama bu işlev durak başına 15+ hat
    için çağrılıyor; 5 dakikalık önbellek konuldu.
    """
    anahtar = esik[:13]
    kayit = _dilim_onbellek.get(anahtar)
    if kayit and (datetime.now() - kayit[0]).total_seconds() < 300:
        return kayit[1]
    d = set()
    try:
        for g, s, n in k.execute(
                "SELECT substr(zaman,1,10), substr(zaman,12,2),"
                " COUNT(DISTINCT substr(zaman,12,5)) FROM yoklama"
                " WHERE zaman >= ? GROUP BY 1,2", (esik,)):
            if n >= SAGLAM_TUR_ESIGI:
                d.add((g, s))
    except Exception:
        return None                      # yoklama okunamadıysa süzme yapma
    _dilim_onbellek[anahtar] = (datetime.now(), d)
    return d


def _aralik_saglam(t0, t1, dilimler):
    """İki geçiş ARASINDAKİ her saat dilimi sağlam mı?

    ⚠️ İki ucun sağlam olması yetmez: 16:00 ve 18:00 sağlam ama 17:00 kesintili
       olabilir. O durumda 16:55 → 18:05 arası 70 dakikalık YAPAY bir aralık
       üretilir. Aradaki her dilim kontrol ediliyor.
    """
    t = t0.replace(minute=0, second=0, microsecond=0)
    while t <= t1:
        if (t.strftime("%Y-%m-%d"), t.strftime("%H")) not in dilimler:
            return False
        t += timedelta(hours=1)
    return True


def gozlenen_gecisler(hat, yon, durak_kodu, an, gun_tipi, saat_penceresi=1):
    """Bu durakta GERÇEKTE ölçülmüş geçişler → (aralık_dk, gözlem_sayısı, son_geçiş).

    ⚠️ Bu katman TARİFENİN ÖNÜNDE geliyor. Sebep ölçüldü (Bölüm 21): 98'in hafta içi
    tarifesi Sefaköy'de D yönünde 06:40-23:00 arası SIFIR kalkış gösteriyor, gerçekte
    23 dakikada bir otobüs geçiyor. Tarife kâğıt, gözlem gerçek.
    """
    k = _kayit_db()
    if k is None:
        return None
    # ⚠️ Eski sorgu strftime ile saat süzüyordu; indeks kullanılamıyor, o durağın
    #    tüm geçmişi taranıyordu (gecis tablosu 11 milyon satır). Artık önce TARİH
    #    ARALIĞI ile daraltılıyor (indeksli), saat süzmesi Python'da yapılıyor.
    esik = (an - timedelta(days=GOZLEM_GUN)).strftime("%Y-%m-%d %H:%M:%S")
    saatler = {(an.hour + d) % 24 for d in range(-saat_penceresi, saat_penceresi + 1)}
    ham = k.execute(
        "SELECT zaman FROM gecis WHERE durak_kodu=? AND zaman >= ? AND hat=? AND yon=?"
        " ORDER BY zaman", (durak_kodu, esik, hat, yon)).fetchall()
    # ⚠️ Kesintili dilimler ELENİYOR (gerekçe SAGLAM_TUR_ESIGI'nde). `son` süzme
    #    ÖNCESİNDEN alınıyor: "son geçiş ne zamandı" sorusunun cevabı, o dilimin
    #    kalitesinden bağımsız olarak gerçek son gözlemdir.
    dilimler = saglam_dilimler(k, esik)
    zamanlar = [z for (z,) in ham if int(z[11:13]) in saatler]
    son = ham[-1][0] if ham else None
    if dilimler is not None:
        zamanlar = [z for z in zamanlar if (z[:10], z[11:13]) in dilimler]
    if len(zamanlar) < 4:
        return None

    # ardışık geçişler arası aralıklar — gün sınırını aşanlar elenir
    araliklar = []
    for i in range(1, len(zamanlar)):
        t0 = datetime.strptime(zamanlar[i - 1], "%Y-%m-%d %H:%M:%S")
        t1 = datetime.strptime(zamanlar[i], "%Y-%m-%d %H:%M:%S")
        fark = (t1 - t0).total_seconds() / 60
        if 0 < fark <= 120 and (dilimler is None or _aralik_saglam(t0, t1, dilimler)):
            araliklar.append(fark)
    if len(araliklar) < 3:
        return None
    araliklar.sort()
    son_dk = ((an - datetime.strptime(son, "%Y-%m-%d %H:%M:%S")).total_seconds() / 60
              if son else None)

    # ⭐⭐ YOLCUNUN GERÇEKTE BEKLEDİĞİ SÜRE (7 Eylül) — ortanca aralık DEĞİL.
    #
    # ⚠️ Ekranda "bu saatte ortalama 1 dk'da bir geçiyor" yazıyordu ve bu, teknik
    #    olarak doğru ama YOLCU İÇİN YANILTICI. Sebep: otobüsler düzenli aralıkla
    #    gelmiyor, KONVOY halinde geliyor. 76 hattında ölçüldü:
    #        %25'lik dilim 0,5 dk · ortanca 1,1 dk · %90'lık dilim 3,8 dk
    #    Üç otobüs arka arkaya geçip sonra uzun bir boşluk oluyor. Ortanca o
    #    boşluğu görmüyor.
    #
    # ⚠️ Yolcu durağa RASTGELE bir anda gelir; uzun boşluğa denk gelme olasılığı
    #    daha yüksektir, çünkü boşluk daha uzun sürer. Kuyruk teorisinde buna
    #    "inceleme paradoksu" deniyor. Beklenen bekleme süresi:
    #
    #        E[W] = E[X²] / (2·E[X])        X = ardışık geçiş aralıkları
    #
    #    Yani her aralık, KENDİ UZUNLUĞUYLA ağırlıklanıyor.
    #
    # ÖLÇÜLDÜ (7 Eylül · Sefaköy):
    #        hat    ortanca   gerçek bekleme
    #        76      1,1 dk       2,6 dk      ← 2,4 kat fark
    #        89A    13,0 dk      14,2 dk
    #        146    12,8 dk      14,6 dk
    #        98     19,5 dk      19,3 dk
    #    Fark yalnızca SIK geçen hatlarda büyük — orada da zaten en çok yanıltıyor.
    toplam = sum(araliklar)
    bekleme = (sum(x * x for x in araliklar) / (2 * toplam)) if toplam else None

    return (statistics.median(araliklar), araliklar[0], araliklar[-1],
            len(zamanlar), son_dk, bekleme)



# ─────────────────────────────────────────────────────────────────────────────
# ⭐⭐⭐ SEFER BAZLI VARIŞ — kalkışın kendi geçmişi (9 Eylül)
# ─────────────────────────────────────────────────────────────────────────────

SEFER_MIN_ORNEK = 3        # bir kalkış saati için gereken en az gözlem
SEFER_GUN = 7              # geriye kaç gün bakılır
SEFER_ONBELLEK_DK = 30     # tablo bu süre boyunca yeniden hesaplanmaz
SEFER_MAX_DK = 180         # bundan uzun "sefer" eşleşmesi kabul edilmez

_sefer_onbellek = {}


def _sefer_tablosu(k, dz, hat, yon, durak_kodu):
    """Kalkış saatine göre: kalkış durağından bu durağa GEÇMİŞTE ölçülen süre.

    Aynı aracın (kapino) kalkış durağından geçişi ile bu duraktan geçişi
    eşleştiriliyor; aradaki fark o seferin gerçek süresi.

    ⚠️ Tek SQL ile yapılıyor. N+1 sorgu (her sefer için ayrı sorgu) ölçümde
       çalışıyordu ama istek başına yüzlerce sorgu demekti. İki indeks bu JOIN'i
       ucuzlatıyor: ix_gecis_durak_hat (kalkış tarafı) · ix_gecis_arac (varış tarafı).
    """
    try:
        import hayalet
        kd = hayalet.kalkis_durak(dz, hat, yon)
    except Exception:
        return None
    if not kd or kd[1] == durak_kodu:
        return None                       # kalkış durağının kendisi

    esik = (datetime.now() - timedelta(days=SEFER_GUN)).strftime("%Y-%m-%d %H:%M:%S")
    kova = {}
    try:
        for z0, z1 in k.execute(
                "SELECT a.zaman, MIN(b.zaman) FROM gecis a JOIN gecis b"
                "  ON b.kapino = a.kapino AND b.hat = a.hat AND b.yon = a.yon"
                " WHERE a.hat = ? AND a.yon = ? AND a.durak_kodu = ? AND a.zaman >= ?"
                "   AND b.durak_kodu = ? AND b.zaman > a.zaman"
                " GROUP BY a.zaman, a.kapino",
                (hat, yon, kd[1], esik, durak_kodu)):
            if not z1:
                continue
            t0 = datetime.strptime(z0, "%Y-%m-%d %H:%M:%S")
            dk = (datetime.strptime(z1, "%Y-%m-%d %H:%M:%S") - t0).total_seconds() / 60
            if 1 < dk < SEFER_MAX_DK:
                kova.setdefault(t0.hour, []).append(dk)
    except Exception:
        return None

    # ⚠️ AYKIRI TEMİZLİĞİ — ölçüldü (9 Eylül): MR40'ta aralık "30–179 dk" çıktı.
    #    Sebep, aracın TUR ATIP geri dönmesi: kalkış durağından geçtikten sonra
    #    hedef duraktan ikinci turda geçerse eşleşme o turu ölçüyor. Kalkış
    #    durağındaki geçiş de kaçmışsa (GPS boşluğu) aynı sonuç doğuyor.
    #    Ortancanın 2,5 katından uzun süreler eleniyor — ortanca zaten sağlam,
    #    elenen yalnızca uçlar. Eleme SONRASI eşik yeniden uygulanıyor.
    tablo = {}
    for saat, v in kova.items():
        if len(v) < SEFER_MIN_ORNEK:
            continue
        orta = statistics.median(v)
        v = sorted(x for x in v if x <= orta * 2.5)
        if len(v) < SEFER_MIN_ORNEK:
            continue
        tablo[saat] = (statistics.median(v), v[len(v) // 10], v[-max(1, len(v) // 10)], len(v))
    return tablo


def sefer_bazli_varis(hat, yon, durak_kodu, kalkis):
    """Kalkıştan bu durağa tahmini süre → (ortanca_dk, alt, ust, gözlem) | None

    ⭐ MEHMET'İN FİKRİ (8 Eylül):
      *"Bugün 13:00'daki aracın GPS'i kapalı ama sefer saati görünüyor. Yarın
        13:00'da aynı hattın GPS'i açık olabilir — buradaki verileri toplayıp
        'bu saatte GPS açıkken bu kadar dakikada geliyordu' demek."*

    ⚠️ PARÇA MODELİNDEN FARKI: parça modeli kalkıştan durağa kadar HER durak
       arasını ayrı tahmin edip topluyor; 16 durak varsa 16 tahminin hatası
       birikiyor. Bu yöntem tek ölçüm — zincir yok, birikim yok.

    KAYIRMASIZ SINAV (8 Eylül · model 6 günden, sınav dün · 25 hat×durak · 140 tahmin):
        SEFER BAZLI   ortalama 6,9 dk · ortanca 2,4 dk
        PARÇA MODELİ  ortalama 7,7 dk · ortanca 4,5 dk
    Ortanca hata neredeyse yarıya iniyor. Her eşikte üstün (1+, 3+, 6+ gözlem).

    ⚠️ Gün tipi (hafta içi/sonu) AYRILMIYOR: 7 günlük pencerede hafta sonu iki
       gün, ayırmak gözlemi eşiğin altına düşürürdü. Sınavda gün tipi ayrımı
       olmadan da kazandı.

    ⚠️ Bu yöntem her durakta çalışmaz — o durak için geçmiş kayıt yoksa None
       döner ve çağıran taraf parça modeline düşer (kademe orada).
    """
    k = _kayit_db()
    if k is None:
        return None
    try:
        dz = sqlite3.connect(str(VERI / "dizin.db"), timeout=20)
    except Exception:
        return None
    try:
        anahtar = (hat, yon, durak_kodu)
        simdi = datetime.now()
        kayit = _sefer_onbellek.get(anahtar)
        if kayit and (simdi - kayit[0]).total_seconds() < SEFER_ONBELLEK_DK * 60:
            tablo = kayit[1]
        else:
            tablo = _sefer_tablosu(k, dz, hat, yon, durak_kodu)
            _sefer_onbellek[anahtar] = (simdi, tablo)
        if not tablo:
            return None
        return tablo.get(kalkis.hour)
    finally:
        dz.close()


def saatli_varis(hat, yon, sira, kalkis):
    """Kalkıştan bu durağa tahmini süre — SAATLİ PARÇA MODELİ.

    ⭐ Eski yöntem hattın tek ortanca süresini alıp rota oranıyla çarpıyordu:
    "yolun %28'ini yaptıysa sürenin de %28'ini harcamıştır". Ama şehir içi bölüm
    ağır, çevre yolu hızlı — ve saat 18'deki trafik saat 23'tekiyle aynı değil.

    Ölçüldü (30 Ağustos, 9.276 gerçek sefer, aynı aracın durak-arası süresi referans):
        eski (rota oranı)   ortanca hata 5,12 dk
        yeni (saatli parça) ortanca hata 1,71 dk    → %67 iyileşme

    Somut fark — 98, Bakırköy→Sefaköy:
        eski: her saat 21,3 dk
        yeni: 06:00→21 dk · 14:00→36 dk · 18:00→53 dk · 23:00→26 dk
    """
    k = _kayit_db()
    if k is None:
        return None
    try:
        return sure_modeli.varis_suresi(k, hat, yon, 1, sira, kalkis)
    except Exception:
        return None



def guven_etiketi(kaynak, ornek, iptal):
    if kaynak == "canli":
        return "YÜKSEK — araç görünüyor"
    if ornek is None:
        return "ÇOK DÜŞÜK — ölçülmüş süre yok"
    if iptal is not None and iptal > 0.15:
        return "DÜŞÜK — bu hat bu saatte sık iptal oluyor"
    return "ORTA — araç görünmüyor, tarifeden tahmin"


def anlat(durak_kodu, an):
    dz = sqlite3.connect(str(VERI / "dizin.db"))
    d = dz.execute("SELECT durak_adi, ilce, durak_tipi FROM durak WHERE durak_kodu=?",
                   (durak_kodu,)).fetchone()
    if not d:
        print("durak bulunamadı:", durak_kodu)
        return
    gt = gun_tipi(an)
    gt_adi = {"I": "hafta içi", "C": "cumartesi", "P": "pazar"}[gt]
    # ⭐ İPTAL DUYURULARI (4. seans, Bölüm 47) — tahmin değil, İETT'nin kendi bildirimi.
    #    Yalnızca BUGÜN için geçerli; geçmiş/gelecek gün sorgulanırsa harita boş kalır.
    try:
        iptaller = duyurular.iptal_haritasi(_kayit_db(), dz)
    except Exception:
        iptaller = {"kesin": {}, "belirsiz": {}, "gunluk": {}}
    print("\n" + "=" * 74)
    print("  %s  ·  %s" % (d[0].strip(), d[1]))
    print("  %s  ·  %s  ·  durak kodu %s" % (an.strftime("%d.%m.%Y %H:%M"), gt_adi, durak_kodu))
    print("=" * 74)

    for hat, yon, yon_adi, sira, hat_adi, toplam_durak in duraktan_gecen_hatlar(dz, durak_kodu):
        try:
            o = rota.oran(hat, yon, sira)
        except (KeyError, IndexError):
            continue                       # rota geometrisi olmayan hat (676 hat var, 781 değil)

        kalkislar = sonraki_kalkislar(dz, hat, yon, gt, an)
        araclar = canli_araclar(hat, an)
        if not kalkislar and not araclar:
            continue

        print("\n  %-6s → %s" % (hat, (yon_adi or "").strip() or hat_adi))
        print("         bu durak: %d/%d · rotanın %%%.0f'i" % (sira, toplam_durak, o * 100))

        # ── CANLI ────────────────────────────────────────────────────────────
        yas = esleme_tazeligi(hat)
        if yas is None:
            print("     · bu hattın araç eşlemesi henüz alınmadı"
                  " (780 hat sırayla dönüyor, tam tur ~26 saat)")
        elif not araclar:
            print("     · %.0f dk önce bakıldı, hatta çalışan araç yoktu" % yas)
        else:
            durak_m = rota.durak_mesafeleri(hat, yon)[sira - 1][2]
            yaklasan = []
            for a in araclar:
                if a["yon"] != yon:
                    continue                      # ters bacakta, bu durağa gelmiyor
                arac_m, sapma = rota.yol_uzerinde(hat, yon, a["boylam"], a["enlem"])
                if sapma > YAKIN_SAPMA_M:
                    continue                      # rotadan uzak — garaj / servis dışı
                kalan = durak_m - arac_m
                if kalan > 0:
                    yaklasan.append((kalan, arac_m, a))
            yaklasan.sort(key=lambda t: t[0])
            if yaklasan:
                for kalan, arac_m, a in yaklasan[:3]:
                    if a["hiz"]:
                        hiz, olcum_dk, _ = a["hiz"]
                        kaynak = "kendi ölçülen hızı %.0f km/sa" % (hiz * 60 / 1000)
                    else:
                        hiz, kaynak = VARSAYILAN_HIZ, "hat ortalaması (hız ölçülemedi)"
                    dk, yontem = canli_varis_dk(hat, yon, sira, arac_m, kalan, hiz, an)
                    kaynak = ("ölçülmüş parça süreleri" if yontem == "parça"
                              else kaynak)
                    print("     🚌 CANLI  %-8s %5.2f km uzakta → ~%2.0f dakika · %s"
                          % (a["kapino"], kalan / 1000, dk, kaynak))
                    print("        yön %s (%s ile tespit%s) · hat eşlemesi %.0f dk önce"
                          % (a["yon"], a["yontem"],
                             ", etiket '%s' diyordu" % a["etiket_yonu"]
                             if a["etiket_yonu"] and a["etiket_yonu"] != a["yon"] else "",
                             a["esleme_yasi_dk"]))
            else:
                ters = sum(1 for a in araclar if a["yon"] and a["yon"] != yon)
                print("     · hatta %d araç var; %d'i ters bacakta, hiçbiri bu durağa yaklaşmıyor"
                      % (len(araclar), ters))

        # ── GÖZLEM — tarifenin ÖNÜNDE ────────────────────────────────────────
        g = gozlenen_gecisler(hat, yon, durak_kodu, an, gt)
        if g:
            ortanca, en_az, en_cok, n, son_dk, bekleme = g
            print("     📊 GÖZLEM  bu saatte ortanca %.0f dakikada bir geçiyor"
                  "  (aralık %.0f-%.0f dk · %d ölçüm · beklenen bekleme %.0f dk)"
                  % (ortanca, en_az, en_cok, n, bekleme or 0))
            if son_dk is not None and son_dk < 180:
                print("        son geçiş %.0f dk önce → sıradaki ~%s civarı"
                      % (son_dk, (an + timedelta(minutes=max(0, ortanca - son_dk))
                                  ).strftime("%H:%M")))

        # ── TARİFE ───────────────────────────────────────────────────────────
        if g and kalkislar:
            print("     ⏱  tarife (gözlem varken daha zayıf kaynak):")
        for saat, guzergah in kalkislar:
            kalkis = an.replace(hour=int(saat[:2]) % 24, minute=int(saat[3:5]),
                                second=0, microsecond=0)
            if kalkis < an:
                kalkis += timedelta(days=1)

            # ── ⭐ İPTAL DUYURUSU — varsa varış hesabı yapılmaz ────────────────
            #    Burası tahmin DEĞİL: İETT bu kalkışın yapılmayacağını bildirdi.
            #    Bölüm 24-33'te bu bilgi konumdan çıkarılmaya çalışılıyor ve %13
            #    isabette tıkanıyordu; artık okunuyor.
            hhmm = saat[:5]
            duyuru = iptaller["kesin"].get((hat, yon, hhmm))
            if duyuru:
                print("     ⛔ %s kalkışı için İETT İPTAL DUYURDU"
                      "  (ölçüm: bu duyuruların %%66'sı gerçekleşiyor)" % hhmm)
                print("        kalkış yeri: %s" % (duyuru["kalkis_yeri"] or "—"))
                continue
            karisik = iptaller["belirsiz"].get((hat, hhmm))
            if karisik:
                # Aynı saatte iki yönde kalkış var ve duyurudaki kalkış yeri
                # hiçbir yönün ilk durağı değil (ara duraktan kısa sefer).
                # Yönü uydurmuyoruz — yolcuya belirsizliği olduğu gibi söylüyoruz.
                print("     ⚠️  %s civarında bu hatta bir sefer iptali duyuruldu"
                      " (%s kalkışlı); hangi yön olduğu belirsiz"
                      % (hhmm, karisik["kalkis_yeri"] or "—"))
            saatli = saatli_varis(hat, yon, sira, kalkis)
            olcum = olculmus_sure(dz, guzergah, kalkis.hour)
            iptal, n_iptal = iptal_orani(dz, hat, kalkis.hour, gt)

            if saatli:
                dk, n_saatli, n_yedek = saatli
                v1 = kalkis + timedelta(minutes=dk)
                # belirsizlik: ölçülen parçaların oranına göre daralt/genişlet
                pay = 0.12 if n_yedek == 0 else 0.22
                v_alt = kalkis + timedelta(minutes=dk * (1 - pay))
                v_ust = kalkis + timedelta(minutes=dk * (1 + pay))
                print("     ⏱  %s kalkış → bu durağa %s – %s   (orta nokta %s)"
                      % (saat, v_alt.strftime("%H:%M"), v_ust.strftime("%H:%M"),
                         v1.strftime("%H:%M")))
                print("        saatli parça modeli: %.0f dk · %d parça o saatin verisinden%s"
                      % (dk, n_saatli,
                         (", %d parça genel ortalamadan" % n_yedek) if n_yedek else ""))
            elif olcum:
                ortanca, alt, ust, n = olcum
                v1 = kalkis + timedelta(minutes=ortanca * o)
                v_alt = kalkis + timedelta(minutes=alt * o)
                v_ust = kalkis + timedelta(minutes=ust * o)
                aralik = "%s – %s" % (v_alt.strftime("%H:%M"), v_ust.strftime("%H:%M"))
                print("     ⏱  %s kalkış → bu durağa %s   (orta nokta %s)"
                      % (saat, aralik, v1.strftime("%H:%M")))
                print("        ölçüm: %s varyantı %d seferde ortanca %.0f dk · %s"
                      % (guzergah, n, ortanca, guven_etiketi("tarife", n, iptal)))
            else:
                print("     ⏱  %s kalkış → süre ölçümü yok, varış tahmin edilemiyor" % saat)
            if iptal is not None and n_iptal >= 10:
                print("        geçmiş 14 gün: bu saatteki kalkışların %%%.0f'i yapılmadı (%d sefer)"
                      % (iptal * 100, n_iptal))
    print()
    dz.close()


if __name__ == "__main__":
    kod = sys.argv[1] if len(sys.argv) > 1 else "124081"
    if len(sys.argv) > 2:
        s, dk = sys.argv[2].split(":")
        an = datetime.now().replace(hour=int(s), minute=int(dk), second=0, microsecond=0)
    else:
        an = datetime.now()
    anlat(kod, an)

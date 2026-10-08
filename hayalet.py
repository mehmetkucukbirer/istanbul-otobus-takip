"""
HAYALET SEFER — tarifede olup ortada görünmeyen kalkışı bulur ve AÇIKLAR.

Ürünün asıl fikri bu. "Otobüsüm Nerede" araç görünmediğinde susuyor; biz
susmak yerine üç açıklamayı ayırmaya çalışıyoruz:

    İPTAL          sefer hiç yapılmadı            → "sıradaki kalkış 23:50"
    GPS KARANLIĞI  araç yolda ama bildirmiyor     → "konum yok, tahmini varış 23:52"
    BİZ KÖRÜZ      o an biz bakamadık             → "bilmiyorum" demek zorundayız

⚠️ ÜÇÜNCÜSÜ EN ÖNEMLİSİ. Kendi kesintimizi iptal sanıp "otobüs gelmeyecek" dersek
   yolcuyu yanıltırız. `yoklama` tablosu tam da bunun için tutuluyor: "baktık ve
   yoktu" ile "bakmadık" farklı şeyler (bkz. Bölüm 16 — 26/27 Ağustos gecesi bu
   ayrım gerçek bir vakada işe yaradı).

KALKIŞ NASIL TESPİT EDİLİYOR:
  Peronun kendisine bakmıyoruz — orada araçlar park hâlinde durur, sinyal gürültülüdür.
  Bunun yerine rotanın başından ~400 m ötedeki ilk durak "kalkış habercisi" sayılıyor:
  bir araç oradan geçtiyse sefer başlamıştır. Geçişler `gecis` tablosundan geliyor
  (gecisler.py), yani yön gerçek hareketten belirlenmiş oluyor.

⚠️ CANLI ÇALIŞMADA PLAN KAYNAĞI `tarife` (gün tipine bağlı, elimizde olan tek şey).
   Arşivdeki gerçek plan ertesi gün geliyor; o yalnızca DOĞRULAMA için kullanılıyor.

KULLANIM:
    python3 hayalet.py 98 20260826           # bir hattı bir gün için değerlendir
    python3 hayalet.py 98 20260826 --dogrula # arşivle karşılaştır (ertesi gün)
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rota

VERI = Path(__file__).parent / "veri"

PENCERE_ONCE_DK = 10          # kalkış bu kadar erken olabilir
PENCERE_SONRA_DK = 25         # bu kadar gecikebilir; sonrası artık başka kalkıştır
SAPMA_ORANI = 0.45            # tolerans, hattın kendi sefer aralığının bu kadarı
MAX_SAPMA_TAVAN_DK = 18       # ama hiçbir zaman bundan fazla değil
MIN_SAPMA_DK = 4              # ve bundan az değil (ölçüm gürültüsü payı)

# ⚠️ YÖNTEMİN SINIRI — ölçüldü (500T, 26 Ağustos):
#   Sefer aralığı kalkış gecikmesine yaklaşınca hangi seferin yapılmadığını tek tek
#   ayırt etmek mümkün olmuyor. 500T'de aralık 7 dk, kalkış gecikmesi ±5 dk, bizim
#   ölçümümüz dakikada bir. Sonuç: 8 iptalden 1'i yakalandı, 3 yanlış alarm verildi.
#   98'de (aralık 20 dk) aynı yöntem 17/17 doğru.
#   Bu eşiğin altındaki hatlarda TEK TEK İDDİA EDİLMİYOR; toplu servis düzeyi bakılıyor.
YOGUN_HAT_ESIGI_DK = 12

# ⚠️ EŞLEME TAZELİĞİ — 28 Ağustos'ta ölçülerek eklendi.
#   Kaydedici v2 konumları herkesten alıyor ama HANGİ ARACIN HANGİ HATTA olduğunu
#   hatları sırayla sorarak öğreniyor (tam tur ~26 saat). Ölçüm: 336 hattın 332'si
#   gün boyunca YALNIZCA BİR KEZ eşlendi; hat×saat kapsaması %2,2.
#   Sonuç: çoğu hatta geçişlerin çoğu bize görünmüyor, kalkışlar hayalet sanılıyor.
#   İlk geniş doğrulamada bunun bedeli 6.291 kalkışta 1.487 YANLIŞ ALARM oldu.
#   Kural: eşlemesi bu kadar taze olmayan hatta İPTAL İDDİA EDİLMEZ.
ESLEME_TAZELIK_DK = 15
KALKIS_DURAK_MIN_M = 400      # peron gürültüsünden uzaklaşmak için
KAPSAMA_ESIGI = 0.6           # pencerenin bu oranından azına baktıysak "körüz"


def gun_tipi(tarih):
    g = datetime.strptime(tarih, "%Y%m%d").weekday()
    return "C" if g == 5 else ("P" if g == 6 else "I")


def kalkis_durak(dizin, hat, yon):
    """Kalkışı haber veren durak: rota başından KALKIS_DURAK_MIN_M ötedeki ilk durak."""
    try:
        mesafeler = rota.durak_mesafeleri(hat, yon)
    except (KeyError, IndexError):
        return None
    kodlar = dict(dizin.execute(
        "SELECT sira, durak_kodu FROM hat_durak WHERE hat_kodu=? AND yon=?", (hat, yon)))
    for sira, ad, m, _ in mesafeler:
        if m >= KALKIS_DURAK_MIN_M and sira in kodlar:
            return sira, kodlar[sira], m, ad
    return None


def planli_kalkislar(dizin, hat, tarih):
    """Tarifeden o günün planlanan kalkışları → [(datetime, yon, guzergah)]"""
    gt = gun_tipi(tarih)
    gun = datetime.strptime(tarih, "%Y%m%d")
    sonuc = []
    for saat, yon, guzergah in dizin.execute(
            "SELECT saat, yon, guzergah FROM tarife WHERE hat_kodu=? AND gun_tipi=?"
            " ORDER BY saat", (hat, gt)):
        try:
            s, d = int(saat[:2]), int(saat[3:5])
        except (ValueError, TypeError):
            continue
        sonuc.append((gun + timedelta(hours=s, minutes=d), yon, guzergah))
    return sonuc


def gozlenen_kalkislar(kayit, hat, yon, durak_kodu, bas, bit):
    """Kalkış habercisi duraktan geçen araçlar → [(datetime, kapino)]"""
    return [(datetime.strptime(z, "%Y-%m-%d %H:%M:%S"), k) for z, k in kayit.execute(
        "SELECT zaman, kapino FROM gecis WHERE hat=? AND yon=? AND durak_kodu=?"
        " AND zaman >= ? AND zaman <= ? ORDER BY zaman",
        (hat, yon, durak_kodu, bas.strftime("%Y-%m-%d %H:%M:%S"),
         bit.strftime("%Y-%m-%d %H:%M:%S")))]


def kapsama(kayit, bas, bit):
    """O aralıkta kaç dakikada başarılı yoklama yapmışız → 0-1 arası oran."""
    toplam_dk = max(1, int((bit - bas).total_seconds() / 60))
    n = kayit.execute(
        "SELECT COUNT(DISTINCT substr(zaman,1,16)) FROM yoklama"
        " WHERE sonuc='ok' AND zaman >= ? AND zaman <= ?",
        (bas.strftime("%Y-%m-%d %H:%M:%S"), bit.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()[0]
    return min(1.0, n / toplam_dk)


def hatta_arac_var_miydi(kayit, hat, bas, bit):
    """O aralıkta bu hatta ATANMIŞ herhangi bir araç bildirim yapmış mı?

    Ayırt edici olan sinyal: hattın başka araçları görünüyorsa servis ayakta
    demektir, o hâlde görünmeyen tek kalkış muhtemelen İPTAL. Hiçbir aracı
    görünmüyorsa sorun bizim eşlememizde de olabilir — iddia zayıflar.
    """
    return kayit.execute(
        "SELECT COUNT(*) FROM gecis WHERE hat=? AND zaman >= ? AND zaman <= ?",
        (hat, bas.strftime("%Y-%m-%d %H:%M:%S"),
         bit.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()[0]


def onceki_iptal_orani(dizin, hat, saat, gt):
    r = dizin.execute(
        "SELECT COUNT(*), SUM(CASE WHEN durum!='T' THEN 1 ELSE 0 END) FROM sefer"
        " WHERE hat_kodu=? AND plan_saat=? AND gun_tipi=?", (hat, saat, gt)).fetchone()
    return (r[1] / r[0], r[0]) if r and r[0] else (None, 0)




def kayit_baslangici(kayit):
    """Hiç kayıt tutmaya başlamadığımız an. Öncesi hakkında hiçbir şey iddia edilemez."""
    r = kayit.execute("SELECT MIN(zaman) FROM yoklama").fetchone()
    return datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S") if r and r[0] else None



def sefer_araligi(planlar):
    """Bu yön için planlanan kalkışlar arası ORTANCA aralık (dakika).

    ⚠️ NEDEN GEREKLİ: hizalama toleransı sabit olamaz. 500T'de sefer aralığı
    ~20 dk iken tolerans 18 dk'ydı; bu kadar geniş pencerede her plan komşusunun
    geçişini kapıyor ve eksik seferler görünmez oluyordu. Ölçüldü: 8 iptalden
    7'si kaçtı. Tolerans, aralığın YARISINDAN küçük olmalı ki bir geçiş iki
    plana birden uyamasın.
    """
    if len(planlar) < 3:
        return None
    araliklar = sorted((planlar[i][0] - planlar[i - 1][0]).total_seconds() / 60
                       for i in range(1, len(planlar)))
    return araliklar[len(araliklar) // 2]


def sapma_toleransi(planlar):
    aralik = sefer_araligi(planlar)
    if not aralik:
        return MAX_SAPMA_TAVAN_DK
    return max(MIN_SAPMA_DK, min(MAX_SAPMA_TAVAN_DK, aralik * SAPMA_ORANI))


def hizala(planlar, gecisler, tolerans=None):
    """Planlanan kalkışlarla gözlenen geçişleri SIRA KORUYARAK hizalar.

    ⚠️ NEDEN AÇGÖZLÜ EŞLEŞTİRME OLMAZ — ölçülerek görüldü:
      İlk sürüm "pencereye giren ilk geçişi al" diyordu. Sefer aralığı 20 dakika,
      pencere 35 dakika olunca bir geçiş birden çok plana uyuyor ve zincir kayıyor:
      16:23 geçişi 16:00 planına atanınca sonraki her şey bir slot kayıyordu.
      Sonuç: 98 hattında 2 yanlış alarm + gerçek iptali kaçırma.

    Doğrusu diziyi bir bütün olarak hizalamak. Otobüsler tarifedeki sırayı bozmaz
    (biri diğerini geçse bile kalkış sırası korunur), o yüzden SIRA KORUYAN bir
    hizalama — dizi hizalama algoritmalarının aynısı — doğru araç.

    Döner: [(plan_indeksi, gecis_indeksi | None)]
    """
    if tolerans is None:
        tolerans = sapma_toleransi(planlar)
    ceza = tolerans                        # boşluk bedeli toleransla aynı mertebede
    n, m = len(planlar), len(gecisler)
    # dp[i][j] = ilk i plan ve ilk j geçiş hizalandığında en küçük toplam bedel
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    iz = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + ceza
        iz[i][0] = "plan"
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + ceza
        iz[0][j] = "gecis"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            fark = abs((gecisler[j - 1][0] - planlar[i - 1][0]).total_seconds()) / 60
            secenekler = [(dp[i - 1][j] + ceza, "plan"),
                          (dp[i][j - 1] + ceza, "gecis")]
            if fark <= tolerans:
                secenekler.append((dp[i - 1][j - 1] + fark, "esle"))
            dp[i][j], iz[i][j] = min(secenekler)

    sonuc, i, j = [], n, m
    while i > 0 or j > 0:
        adim = iz[i][j]
        if adim == "esle":
            sonuc.append((i - 1, j - 1)); i -= 1; j -= 1
        elif adim == "plan":
            sonuc.append((i - 1, None)); i -= 1
        else:
            j -= 1
    return list(reversed(sonuc))



# ─────────────────────────────────────────────────────────────────────────────
# İPTAL / GPS KARANLIĞI AYRIMI
# ─────────────────────────────────────────────────────────────────────────────

KONTROL_ORANLARI = (0.40, 0.70)     # rotanın bu noktalarında da aranacak


def kontrol_noktasi(dizin, hat, yon, oran):
    """Rotanın verilen oranına en yakın durak → (sira, kod, mesafe, ad)."""
    try:
        mesafeler = rota.durak_mesafeleri(hat, yon)
        toplam = rota.rota_uzunlugu(hat, yon)
    except (KeyError, IndexError):
        return None
    if not toplam:
        return None
    kodlar = dict(dizin.execute(
        "SELECT sira, durak_kodu FROM hat_durak WHERE hat_kodu=? AND yon=?", (hat, yon)))
    hedef = oran * toplam
    aday = None
    for sira, ad, m, _ in mesafeler:
        if sira not in kodlar:
            continue
        if aday is None or abs(m - hedef) < abs(aday[2] - hedef):
            aday = (sira, kodlar[sira], m, ad)
    return aday


def durak_arasi_sure(kayit, hat, yon, durak_a, durak_b):
    """AYNI ARACIN A'dan B'ye geçişleri arasındaki ortanca süre (dakika).

    ⚠️ NEDEN TARİFEDEN HESAPLANMIYOR: gidiş+dönüşü tek sefer sayan varyantlarda
    (98_G_D7742 = 193 dk) sefer süresi tek bacağın iki katı. Oranla çarpınca
    varış saati tamamen kayardı. Kendi ölçtüğümüz geçişler bu sorunu hiç yaşamıyor.
    """
    farklar = [r[0] for r in kayit.execute("""
        SELECT (julianday(b.zaman) - julianday(a.zaman)) * 1440
          FROM gecis a JOIN gecis b
            ON a.kapino = b.kapino AND a.hat = b.hat AND a.yon = b.yon
         WHERE a.hat=? AND a.yon=? AND a.durak_kodu=? AND b.durak_kodu=?
           AND b.zaman > a.zaman
           AND (julianday(b.zaman) - julianday(a.zaman)) * 1440 < 180""",
        (hat, yon, durak_a, durak_b))]
    if len(farklar) < 3:
        return None
    farklar.sort()
    return farklar[len(farklar) // 2]


ILERI_TOLERANS_DK = 15       # kontrol noktasında bu kadar sapma kabul
KALKIS_ARAMA_DK = 30         # aracı kalkış durağında bu kadar geniş ararız


def ileride_belirdi_mi(kayit, dizin, hat, yon, plan_an, kalkis_durak_kodu,
                       tum_planlar, tum_gecisler):
    """Kalkışta görünmeyen sefer, rotanın İLERİSİNDE beliriyor mu?

    ⚠️ ZAMANLA EŞLEŞTİRME DENENDİ, ÇÖKTÜ. İlk sürüm planları kontrol noktasına
    kaydırıp orada da hizalıyordu. Ama sefer aralığı 20 dk iken yolculuk süresi
    ±15 dk oynuyor; bu belirsizlikte her geçiş her plana uyuyor. 26 Ağustos 18:00
    iptali bu yüzden yanlışlıkla "GPS karanlığı" sayıldı.

    ⭐ DOĞRU SİNYAL ZAMAN DEĞİL, ARAÇ KİMLİĞİ. Her geçişte kapı numarası var.
    Sefer yapılmış ama kalkışta GPS'i susmuşsa, o araç ileride görünür ve
    KALKIŞ DURAĞINDA HİÇ GÖRÜNMEMİŞ olur. Aradığımız tam olarak bu: kontrol
    noktasından geçen ama kalkışta izi olmayan araç.

    Döner: (belirdi_mi, kanıt_metni)
    """
    for oran in KONTROL_ORANLARI:
        nokta = kontrol_noktasi(dizin, hat, yon, oran)
        if not nokta:
            continue
        _, kod, mesafe, ad = nokta
        gecikme = durak_arasi_sure(kayit, hat, yon, kalkis_durak_kodu, kod)
        if gecikme is None:
            continue

        hedef = plan_an + timedelta(minutes=gecikme)
        adaylar = kayit.execute(
            "SELECT zaman, kapino FROM gecis WHERE hat=? AND yon=? AND durak_kodu=?"
            " AND zaman >= ? AND zaman <= ?",
            (hat, yon, kod,
             (hedef - timedelta(minutes=ILERI_TOLERANS_DK)).strftime("%Y-%m-%d %H:%M:%S"),
             (hedef + timedelta(minutes=ILERI_TOLERANS_DK)).strftime("%Y-%m-%d %H:%M:%S"))
        ).fetchall()

        for zaman, kapino in adaylar:
            gecis_ani = datetime.strptime(zaman, "%Y-%m-%d %H:%M:%S")
            kalkis_tahmini = gecis_ani - timedelta(minutes=gecikme)
            # Bu araç kalkış durağından geçmiş mi? Geniş pencereyle arıyoruz —
            # emin olamıyorsak "GPS karanlığı" DEMEMEYİ tercih ediyoruz.
            gorundu = kayit.execute(
                "SELECT COUNT(*) FROM gecis WHERE hat=? AND yon=? AND durak_kodu=?"
                " AND kapino=? AND zaman >= ? AND zaman <= ?",
                (hat, yon, kalkis_durak_kodu, kapino,
                 (kalkis_tahmini - timedelta(minutes=KALKIS_ARAMA_DK)).strftime("%Y-%m-%d %H:%M:%S"),
                 (kalkis_tahmini + timedelta(minutes=KALKIS_ARAMA_DK)).strftime("%Y-%m-%d %H:%M:%S"))
            ).fetchone()[0]
            if gorundu == 0:
                return True, ("araç %s · %s'de %s'den geçti ama kalkış durağında"
                              " hiç görünmedi" % (kapino, gecis_ani.strftime("%H:%M"), ad.strip()))
    return False, None



def esleme_taze_mi(kayit, hat, plan_an, sinir_dk=ESLEME_TAZELIK_DK):
    """Bu kalkış sırasında hattın araç eşlemesi taze miydi?

    Taze değilse hangi araçların o hatta olduğunu bilmiyorduk demektir; geçiş
    görmememiz seferin yapılmadığını değil, BİZİM BAKMADIĞIMIZI gösterir.
    """
    r = kayit.execute(
        "SELECT COUNT(*) FROM arac_hat WHERE hat=? AND zaman >= ? AND zaman <= ?",
        (hat,
         (plan_an - timedelta(minutes=sinir_dk)).strftime("%Y-%m-%d %H:%M:%S"),
         (plan_an + timedelta(minutes=sinir_dk)).strftime("%Y-%m-%d %H:%M:%S"))).fetchone()
    return bool(r and r[0])


def degerlendir(hat, tarih):
    """Bir hattın bir günündeki tüm planlı kalkışlarını değerlendirir."""
    dizin = sqlite3.connect(str(VERI / "dizin.db"))
    kayit = sqlite3.connect(str(VERI / "kayit.db"))
    gt = gun_tipi(tarih)

    duraklar = {}
    for yon in ("G", "D"):
        d = kalkis_durak(dizin, hat, yon)
        if d:
            duraklar[yon] = d

    planlar = planli_kalkislar(dizin, hat, tarih)
    gun = datetime.strptime(tarih, "%Y%m%d")
    kayit_bas = kayit_baslangici(kayit)
    sonuc = []

    # Hizalama YÖN BAZINDA yapılır: G ve D ayrı diziler, kendi durakları var.
    for yon in ("G", "D"):
        if yon not in duraklar:
            continue
        sira, durak_kodu, mesafe, durak_adi = duraklar[yon]
        yon_planlari = [(p, y, g) for p, y, g in planlar if y == yon]
        if not yon_planlari:
            continue
        aralik = sefer_araligi(yon_planlari)
        yogun = aralik is not None and aralik < YOGUN_HAT_ESIGI_DK
        gecisler = gozlenen_kalkislar(
            kayit, hat, yon, durak_kodu,
            gun - timedelta(hours=1), gun + timedelta(days=1, hours=2))

        for plan_i, gecis_i in hizala(yon_planlari, gecisler):
            plan_an, _, guzergah = yon_planlari[plan_i]
            bas = plan_an - timedelta(minutes=PENCERE_ONCE_DK)
            bit = plan_an + timedelta(minutes=PENCERE_SONRA_DK)
            kaps = kapsama(kayit, bas, bit)
            hat_canli = hatta_arac_var_miydi(kayit, hat, bas, bit)
            prior, prior_n = onceki_iptal_orani(dizin, hat, plan_an.hour, gt)

            if gecis_i is not None:
                t, k = gecisler[gecis_i]
                sapma = (t - plan_an).total_seconds() / 60
                durum = "yapildi"
                aciklama = "araç %s · %s'de %s'den geçti (%+.0f dk)" % (
                    k, t.strftime("%H:%M"), durak_adi.strip(), sapma)
            elif kayit_bas and bas < kayit_bas:
                # ⚠️ Kayıt tutmaya başlamadan önceki kalkış hakkında hiçbir şey
                #    söyleyemeyiz. Kapsama oranı yanıltıcı çıkabiliyor (pencerenin
                #    yarısı kayıt sonrasına düşünce eşiği geçiyor) — bu yüzden ayrı
                #    ve kesin bir kontrol. 26 Ağustos 16:00 kalkışı bu yüzden
                #    yanlışlıkla "hayalet" işaretlenmişti; kaydedici 16:03'te başlamıştı.
                durum = "bilinmiyor"
                aciklama = "kayıt %s'de başladı, bu kalkış öncesinde" % kayit_bas.strftime("%H:%M")
            elif kaps < KAPSAMA_ESIGI:
                durum = "bilinmiyor"
                aciklama = "o aralıkta yalnızca %%%.0f oranında bakabildik — kör kaldık" % (kaps * 100)
            elif hat_canli == 0:
                durum = "bilinmiyor"
                aciklama = "hattın hiçbir aracı görünmüyor — eşleme eksik olabilir"
            elif not esleme_taze_mi(kayit, hat, plan_an):
                durum = "bilinmiyor"
                aciklama = ("bu saatte hattın araç eşlemesi tazelenmemişti —"
                            " hangi araçların bu hatta olduğunu bilmiyorduk")
            elif yogun:
                durum = "bilinmiyor"
                aciklama = ("yoğun hat (sefer aralığı %.0f dk) — tek tek sefer iddiası"
                            " güvenilir değil, toplu servis düzeyine bakılmalı" % aralik)
            else:
                # ⭐ AYRIM: kalkışta yok — peki rotanın İLERİSİNDE var mı?
                belirdi, kanit = ileride_belirdi_mi(
                    kayit, dizin, hat, yon, plan_an, durak_kodu, yon_planlari, gecisler)
                if belirdi:
                    durum = "gps_karanligi"
                    aciklama = "kalkışta görünmedi, yolda belirdi — " + kanit
                else:
                    durum = "iptal"
                    aciklama = ("ne kalkışta ne ilerideki kontrol noktalarında görüldü;"
                                " hattın diğer araçları çalışıyordu (%d geçiş)" % hat_canli)

            sonuc.append({"plan": plan_an, "yon": yon, "guzergah": guzergah,
                          "durum": durum, "aciklama": aciklama, "kapsama": kaps,
                          "hat_canli": hat_canli, "prior": prior, "prior_n": prior_n})
    sonuc.sort(key=lambda x: x["plan"])
    dizin.close(); kayit.close()
    return sonuc


def dogrula(hat, tarih, sonuc):
    """Arşivdeki gerçekle karşılaştırır (arşiv ertesi gün doluyor)."""
    dizin = sqlite3.connect(str(VERI / "dizin.db"))
    gercek = {}
    for plan, durum, bas in dizin.execute(
            "SELECT plan_zaman, durum, bas_zaman FROM sefer WHERE hat_kodu=? AND tarih=?",
            (hat, tarih)):
        if plan:
            gercek[plan[11:16]] = (durum, bas)
    dizin.close()

    print("\n" + "=" * 74)
    print("  DOĞRULAMA — arşivdeki gerçekle karşılaştırma")
    print("=" * 74)
    tablo = {}
    for s in sonuc:
        g = gercek.get(s["plan"].strftime("%H:%M"))
        if not g:
            continue
        gercek_yapildi = g[0] == "T"
        bizim = s["durum"]
        # bizim tahminimiz: sefer yapıldı mı?
        tahmin = {"yapildi": True, "gps_karanligi": True,
                  "iptal": False, "bilinmiyor": None}[bizim]
        anahtar = (bizim, "yapıldı" if gercek_yapildi else "YAPILMADI (%s)" % g[0])
        tablo[anahtar] = tablo.get(anahtar, 0) + 1
        if bizim in ("iptal", "gps_karanligi") or not gercek_yapildi:
            dogru = "  " if tahmin is None else ("✅" if tahmin == gercek_yapildi else "❌")
            print("  plan %s · bizim: %-13s · arşiv: %-16s %s"
                  % (s["plan"].strftime("%H:%M"), bizim,
                     "yapıldı" if gercek_yapildi else "YAPILMADI (%s)" % g[0], dogru))
    print("\n  özet:")
    for (bizim, gercek_d), n in sorted(tablo.items()):
        print("    bizim '%-11s' · arşiv '%-16s' → %d kalkış" % (bizim, gercek_d, n))



def servis_duzeyi(hat, yon, saat_once=1.0, an=None):
    """Yoğun hatlar için: son N saatte beklenen kadar sefer geçti mi?

    Tek tek "bu kalkış yapıldı mı" sorusu yoğun hatlarda cevaplanamıyor (yukarı bak),
    ama "servis normal mi" sorusu cevaplanabiliyor ve yolcunun asıl merak ettiği de bu.
    """
    an = an or datetime.now()
    dizin = sqlite3.connect(str(VERI / "dizin.db"))
    kayit = sqlite3.connect(str(VERI / "kayit.db"))
    bas = an - timedelta(hours=saat_once)
    gt = gun_tipi(an.strftime("%Y%m%d"))

    beklenen = dizin.execute(
        "SELECT COUNT(*) FROM tarife WHERE hat_kodu=? AND yon=? AND gun_tipi=?"
        " AND saat >= ? AND saat <= ?",
        (hat, yon, gt, bas.strftime("%H:%M"), an.strftime("%H:%M"))).fetchone()[0]
    d = kalkis_durak(dizin, hat, yon)
    gerceklesen = 0
    if d:
        gerceklesen = kayit.execute(
            "SELECT COUNT(*) FROM gecis WHERE hat=? AND yon=? AND durak_kodu=?"
            " AND zaman >= ? AND zaman <= ?",
            (hat, yon, d[1], bas.strftime("%Y-%m-%d %H:%M:%S"),
             an.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()[0]
    dizin.close(); kayit.close()
    if not beklenen:
        return None
    return {"beklenen": beklenen, "gerceklesen": gerceklesen,
            "oran": gerceklesen / beklenen}


if __name__ == "__main__":
    hat = sys.argv[1] if len(sys.argv) > 1 else "98"
    tarih = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y%m%d")
    sonuc = degerlendir(hat, tarih)

    print("\n" + "=" * 74)
    print("  %s hattı · %s · %d planlı kalkış" % (hat, tarih, len(sonuc)))
    print("=" * 74)
    for s in sonuc:
        isaret = {"yapildi": "✅", "iptal": "⛔", "gps_karanligi": "📡",
                  "bilinmiyor": "· "}[s["durum"]]
        print("  %s %s  yön %s  %-11s  %s"
              % (isaret, s["plan"].strftime("%H:%M"), s["yon"], s["durum"], s["aciklama"]))
    sayim = {}
    for s in sonuc:
        sayim[s["durum"]] = sayim.get(s["durum"], 0) + 1
    print("\n  " + " · ".join("%s: %d" % (k, v) for k, v in sorted(sayim.items())))

    if "--dogrula" in sys.argv:
        dogrula(hat, tarih, sonuc)

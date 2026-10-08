"""
GPS KARANLIĞI TAHMİN KAYDEDİCİSİ — ve ertesi gün arşivle doğrulaması.

⚠️ NEDEN VAR: `yoldaki_gorunmeyenler()` (Bölüm 51) "bu kalkış yolda ama konum
bildirmiyor" diyor. Bu iddia şu an istek geldiğinde hesaplanıp UÇUYOR — hiçbir
yerde durmuyor. Yarın arşiv indiğinde kıyaslayacak bir şey olmaz.

  Bu, `yoklama` tablosu dersinin aynısı (Bölüm 7): ölçmediğin şeyi
  sonradan doğrulayamazsın. Tahmin, verildiği anda yazılmalı.

İDDİA NE: "hat X, yön Y, saat HH:MM kalkışı YOLA ÇIKTI ama görünmüyor."
ARŞİV NE DER: o seferin `durum` alanı — T (yapıldı) / I,YK,B (yapılmadı).

  iddia 'yolda'  + arşiv T      → ✅ DOĞRU  (sefer gerçekten yapıldı, GPS susmuş)
  iddia 'yolda'  + arşiv I/YK   → ❌ YANLIŞ (sefer hiç yapılmamış, biz "geliyor" dedik)

⚠️ İkinci yanlış türü daha zararlı: yolcuya "otobüs geliyor" deyip gelmemesi.

ÇALIŞTIRMA:
    python3 gps_izleyici.py               bir tarama · iddiaları kaydeder
    python3 gps_izleyici.py --dogrula 20260901    o günün iddialarını arşivle kıyasla
"""

import sqlite3
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import durakta_ne_var as DNV
import duyurular
import rota
import sure_modeli
import yon_tespit

VERI = Path(__file__).parent / "veri"
EN_AZ_ARALIK_DK = DNV.GPS_EN_AZ_ARALIK_DK    # sık seferli hatta iddia yok (Bölüm 25)
ESLESME_TOLERANS_DK = 8                       # görünen aracı kalkışa bağlama payı


def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS gps_tahmin (
            id INTEGER PRIMARY KEY,
            tarih TEXT, hat TEXT, yon TEXT, kalkis TEXT,   -- iddia edilen sefer
            gun_tipi TEXT,
            ilk_iddia TEXT, son_iddia TEXT, iddia_sayisi INTEGER DEFAULT 1,
            yolda_sefer INTEGER,      -- o an yolda sayılan sefer adedi
            gorunen_arac INTEGER,     -- o an görünen araç adedi
            tahmini_kalkis_yasi REAL, -- kalkışın üstünden geçen dakika
            arsiv_durum TEXT,         -- ertesi gün doldurulur: T / I / YK / B
            dogru INTEGER             -- 1 = sefer gerçekten yapıldı (iddia tuttu)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_gps_tekil
            ON gps_tahmin (tarih, hat, yon, kalkis);
        CREATE INDEX IF NOT EXISTS ix_gps_tarih ON gps_tahmin (tarih);
    """)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────

def _kalkislar(dz, hat, yon, gt, bas, son):
    return [r[0][:5] for r in dz.execute(
        "SELECT saat FROM tarife WHERE hat_kodu=? AND yon=? AND gun_tipi=?"
        " AND saat >= ? AND saat < ? ORDER BY saat", (hat, yon, gt, bas, son))]


def hat_taramasi(k, dz, hat, an, gt, iptaller):
    """Bir hattın iki yönü için 'yolda ama görünmüyor' seferlerini bulur.

    ⭐ Görünen aracın hangi kalkışa ait olduğu, aracın rota üzerindeki yerinden
    GERİYE giderek kestiriliyor: "şu ana kadar bu kadar yol gitmişse, şu saatte
    kalkmış olmalı". Sonra sıra bozulmadan eşleştiriliyor (Bölüm 24 dersi:
    açgözlü eşleştirme çöküyor, sıra koruyan hizalama doğru araç).
    """
    try:
        araclar = yon_tespit.hattaki_araclar(hat, an) or []
    except Exception:
        return []

    sonuc = []
    for yon in ("G", "D"):
        try:
            mesafeler = [x[2] for x in rota.durak_mesafeleri(hat, yon)]
        except Exception:
            continue
        if len(mesafeler) < 3:
            continue
        son_sira = len(mesafeler)

        r = sure_modeli.varis_suresi(k, hat, yon, 1, son_sira, an)
        if not r:
            continue
        tur_dk = r[0]
        bas = (an - timedelta(minutes=tur_dk)).strftime("%H:%M")
        simdi = an.strftime("%H:%M")
        if bas >= simdi:
            continue                     # gece yarısını aşıyor, karıştırma
        kalkislar = _kalkislar(dz, hat, yon, gt, bas, simdi)
        if len(kalkislar) < 2:
            continue
        dk = lambda s: int(s[:2]) * 60 + int(s[3:5])
        aralik = statistics.median([dk(b) - dk(a) for a, b in zip(kalkislar, kalkislar[1:])])
        if aralik < EN_AZ_ARALIK_DK:
            continue                     # sık seferli — ayırt edilemez (Bölüm 25)

        # iptali duyurulanlar yolda sayılmaz
        yolda = [s for s in kalkislar
                 if not (iptaller and (hat, yon, s) in iptaller.get("kesin", {}))]
        if not yolda:
            continue

        # görünen araçların KESTİRİLEN kalkış saatleri
        gorunen = []
        for a in araclar:
            if a.get("yon") != yon:
                continue
            try:
                arac_m, sapma = rota.yol_uzerinde(hat, yon, a["boylam"], a["enlem"])
            except Exception:
                continue
            if sapma > DNV.YAKIN_SAPMA_M:
                continue
            # araç kaçıncı durakta? oraya kadar kaç dakika sürer? → kalkış = şimdi - o
            import bisect
            i = max(2, bisect.bisect_right(mesafeler, arac_m))
            rr = sure_modeli.varis_suresi(k, hat, yon, 1, i, an - timedelta(minutes=30))
            if not rr:
                continue
            gorunen.append((an - timedelta(minutes=rr[0])).strftime("%H:%M"))
        gorunen.sort()

        # ⭐⭐ ÖNCE SAYMA KURALI — kaç sefer görünmüyor?
        # ⚠️ İlk sürüm bunu atlayıp doğrudan sıra eşleştirmesi yapıyordu ve saçmalıyordu:
        #    "522 · yolda 6 sefer · görünen 9 araç" diye iddia üretiyordu. Dokuz araç
        #    görünürken altı seferin hiçbiri karanlıkta olamaz. Kestirilen kalkış
        #    saatleri gürültülü olunca tolerans içinde eşleşemiyor, sefer boşta kalıyordu.
        #
        #    Bölüm 33 dersi: tek tek atama yerine SAYMAK daha sağlam.
        #    Adet buradan gelir; sıra eşleştirmesi yalnızca HANGİLERİ olduğunu seçer.
        karanlik_adet = max(0, len(yolda) - len(gorunen))
        if karanlik_adet == 0:
            continue

        # Hangileri? Görünen araçların kestirilen kalkışlarına EN UZAK olanlar.
        uzaklik = []
        for s in yolda:
            if gorunen:
                d = min(abs(dk(g) - dk(s)) for g in gorunen)
            else:
                d = 10 ** 6
            uzaklik.append((d, s))
        uzaklik.sort(reverse=True)
        for _, s in uzaklik[:karanlik_adet]:
            sonuc.append({
                "hat": hat, "yon": yon, "kalkis": s,
                "yolda_sefer": len(yolda), "gorunen_arac": len(gorunen),
                "kalkis_yasi": (dk(simdi) - dk(s)),
            })
    return sonuc


def tara():
    k = sqlite3.connect(str(VERI / "kayit.db"), timeout=120)
    k.execute("PRAGMA busy_timeout=120000")
    dz = sqlite3.connect(str(VERI / "dizin.db"), timeout=120)
    tablo_kur(k)

    an = datetime.now()
    gt = DNV.gun_tipi(an)
    bugun = an.strftime("%Y-%m-%d")
    z = an.strftime("%Y-%m-%d %H:%M:%S")
    try:
        iptaller = duyurular.iptal_haritasi(k, dz)
    except Exception:
        iptaller = {"kesin": {}, "belirsiz": {}, "gunluk": {}}

    hatlar = [r[0] for r in dz.execute("SELECT DISTINCT hat_kodu FROM tarife")]
    yeni = tazelenen = 0
    for hat in hatlar:
        for c in hat_taramasi(k, dz, hat, an, gt, iptaller):
            try:
                k.execute(
                    "INSERT INTO gps_tahmin (tarih, hat, yon, kalkis, gun_tipi,"
                    " ilk_iddia, son_iddia, yolda_sefer, gorunen_arac, tahmini_kalkis_yasi)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (bugun, c["hat"], c["yon"], c["kalkis"], gt, z, z,
                     c["yolda_sefer"], c["gorunen_arac"], c["kalkis_yasi"]))
                yeni += 1
            except sqlite3.IntegrityError:
                k.execute("UPDATE gps_tahmin SET son_iddia=?, iddia_sayisi=iddia_sayisi+1"
                          " WHERE tarih=? AND hat=? AND yon=? AND kalkis=?",
                          (z, bugun, c["hat"], c["yon"], c["kalkis"]))
                tazelenen += 1
    k.commit()
    print("%s  %d hat tarandı · +%d yeni iddia · %d tazelendi"
          % (z[11:], len(hatlar), yeni, tazelenen))
    k.close(); dz.close()


# ─────────────────────────────────────────────────────────────────────────────
# DOĞRULAMA — ertesi gün arşivle
# ─────────────────────────────────────────────────────────────────────────────

def dogrula(tarih_yyyymmdd):
    """O günün 'GPS karanlığı' iddialarını arşivdeki gerçekle kıyaslar."""
    k = sqlite3.connect(str(VERI / "kayit.db"), timeout=120)
    dz = sqlite3.connect(str(VERI / "dizin.db"), timeout=120)
    tablo_kur(k)
    tarih = "%s-%s-%s" % (tarih_yyyymmdd[:4], tarih_yyyymmdd[4:6], tarih_yyyymmdd[6:])

    arsiv_var = dz.execute("SELECT COUNT(*) FROM sefer WHERE tarih=?",
                           (tarih_yyyymmdd,)).fetchone()[0]
    if not arsiv_var:
        print("⚠️  %s arşivi henüz inmemiş. Önce: python3 gunluk.py %s"
              % (tarih_yyyymmdd, tarih_yyyymmdd))
        return

    iddialar = k.execute(
        "SELECT id, hat, yon, kalkis FROM gps_tahmin WHERE tarih=?", (tarih,)).fetchall()
    if not iddialar:
        print("⚠️  %s için kayıtlı iddia yok." % tarih)
        return

    # arşivi (hat, yon, HH:MM) -> durum diye indeksle
    gercek = {}
    for hat, yon, plan, durum in dz.execute(
            "SELECT hat_kodu, yon, plan_zaman, durum FROM sefer WHERE tarih=?",
            (tarih_yyyymmdd,)):
        if plan and len(plan) >= 16:
            gercek[(hat, yon, plan[11:16])] = durum

    dogru = yanlis = bulunamadi = 0
    yanlis_ornek = []
    for _id, hat, yon, kalkis in iddialar:
        durum = gercek.get((hat, yon, kalkis))
        if durum is None:
            bulunamadi += 1
            k.execute("UPDATE gps_tahmin SET arsiv_durum=NULL, dogru=NULL WHERE id=?", (_id,))
            continue
        ok = 1 if durum == "T" else 0
        dogru += ok
        yanlis += 1 - ok
        if not ok and len(yanlis_ornek) < 8:
            yanlis_ornek.append((hat, yon, kalkis, durum))
        k.execute("UPDATE gps_tahmin SET arsiv_durum=?, dogru=? WHERE id=?",
                  (durum, ok, _id))
    k.commit()

    n = dogru + yanlis
    print("\n" + "=" * 66)
    print("  GPS KARANLIĞI DOĞRULAMASI — %s" % tarih)
    print("=" * 66)
    print("  iddia edilen sefer      : %d" % len(iddialar))
    print("  arşivde bulunan         : %d" % n)
    print("  arşivde bulunamayan     : %d   (tarife/arşiv eşleşmedi)" % bulunamadi)
    if n:
        print()
        print("  ✅ sefer GERÇEKTEN yapıldı : %5d   (%%%.1f)" % (dogru, 100 * dogru / n))
        print("     → GPS susmuş, biz doğru söyledik: 'otobüs geliyor'")
        print("  ❌ sefer YAPILMAMIŞ        : %5d   (%%%.1f)" % (yanlis, 100 * yanlis / n))
        print("     → 'geliyor' dedik, gelmedi. Yolcuyu boşuna beklettik.")
    if yanlis_ornek:
        print("\n  yanlış iddia örnekleri:")
        for h, y, s, d in yanlis_ornek:
            print("     %-6s yön %s  %s  arşiv: %s" % (h, y, s, d))
    print("=" * 66 + "\n")
    k.close(); dz.close()


def gecmis_tara(tarih_yyyymmdd, adim_dk=30, bas_saat=6, son_saat=23):
    """⭐ GERİYE DÖNÜK TARAMA — yarını beklemeden yöntemi sınamak için.

    Konum, araç→hat eşlemesi ve geçişler geçmişe dönük duruyor; `hattaki_araclar`
    zaten bir `an` parametresi alıyor. Yani geçmiş bir günde, o gün ne iddia
    edeceksek birebir üretip AYNI GÜNÜN arşiviyle kıyaslayabiliyoruz.

    ⚠️ Bir kayırma var, açıkça bilinsin: süre modeli BUGÜNKÜ veriyle kurulu ve
    o günü de içeriyor. Yani model o günü "görmüş" oluyor. Gerçek zamanlı
    kullanımda model o günü görmemiş olacak. Bu ölçüm bu yüzden iyimser taraflı;
    yarınki canlı doğrulama asıl sınav.
    """
    k = sqlite3.connect(str(VERI / "kayit.db"), timeout=180)
    k.execute("PRAGMA busy_timeout=180000")
    dz = sqlite3.connect(str(VERI / "dizin.db"), timeout=180)
    tablo_kur(k)
    tarih = "%s-%s-%s" % (tarih_yyyymmdd[:4], tarih_yyyymmdd[4:6], tarih_yyyymmdd[6:])
    gun = datetime.strptime(tarih, "%Y-%m-%d")
    gt = DNV.gun_tipi(gun)

    k.execute("DELETE FROM gps_tahmin WHERE tarih=?", (tarih,))
    hatlar = [r[0] for r in dz.execute("SELECT DISTINCT hat_kodu FROM tarife")]
    toplam = 0
    an = gun.replace(hour=bas_saat)
    while an.hour <= son_saat and an.day == gun.day:
        z = an.strftime("%Y-%m-%d %H:%M:%S")
        yeni = 0
        for hat in hatlar:
            for c in hat_taramasi(k, dz, hat, an, gt, None):
                try:
                    k.execute(
                        "INSERT INTO gps_tahmin (tarih, hat, yon, kalkis, gun_tipi,"
                        " ilk_iddia, son_iddia, yolda_sefer, gorunen_arac,"
                        " tahmini_kalkis_yasi) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (tarih, c["hat"], c["yon"], c["kalkis"], gt, z, z,
                         c["yolda_sefer"], c["gorunen_arac"], c["kalkis_yasi"]))
                    yeni += 1
                except sqlite3.IntegrityError:
                    pass
        k.commit()
        toplam += yeni
        print("  %s → +%d iddia (toplam %d)" % (an.strftime("%H:%M"), yeni, toplam))
        an += timedelta(minutes=adim_dk)
    print("\n%s için %d iddia üretildi.\n" % (tarih, toplam))
    k.close(); dz.close()


if __name__ == "__main__":
    if "--gecmis" in sys.argv:
        i = sys.argv.index("--gecmis")
        gecmis_tara(sys.argv[i + 1])
        dogrula(sys.argv[i + 1])
    elif "--dogrula" in sys.argv:
        i = sys.argv.index("--dogrula")
        dogrula(sys.argv[i + 1] if len(sys.argv) > i + 1
                else (datetime.now() - timedelta(days=1)).strftime("%Y%m%d"))
    else:
        tara()

"""
PARÇA HAVUZU — ham geçişi bir kez işle, özeti sonsuza kadar biriktir.

⭐ NEDEN VAR (3 Eylül, Mehmet'in fikri):
  *"geçmiş verilerden veri elde ettiğimiz zaman geçmiş verileri silsek, o değerin
    üstüne yeni verileri ekleyip bir hesaplama yapsak nasıl olur"*

  Doğru fikir. Şu ana kadar `sure_modeli.kur()` her saat ham `gecis` tablosundan
  SIFIRDAN hesap yapıyordu — bu yüzden ham veriyi tutmak zorundaydık.
  Ham veri günde 0,44 GB büyüyor ve 3 Eylül'de diski doldurup sistemi öldürdü.

  ÖLÇÜLDÜ — ham veride ne kadar tekrar var:
      ham gecis            14.988.104 satır · 3,57 GB (veri + 4 indeks)
      içindeki bilgi        6.516.481 süre değeri · 712.911 kovada
  Yani satırların çoğu, aynı kovaya düşen tekrarlar. Bilgi ham veriden 5 kat küçük.

⭐ TASARIM — kova başına TEK satır, gözlemler BLOB'da paketli

  Ölçüldü (60.000 gerçek kova ile):
      gözlem başına ayrı satır + indeks : 405 bayt/kova
      kova başına 1 satır · BLOB        :  43 bayt/kova   ← 9,4 kat küçük

  Her gözlem BLOB içinde 4 BAYT:
      2 bayt  süre, desisaniye  (0–6553,5 sn · parça sınırı 25 dk = 15000 ds)
      2 bayt  gün numarası      (epoch günü · 2079'a kadar yeter)

  ⚠️ Gün numarası NEDEN tutuluyor: `pencere_ayarla()` "kaç günlük geçmiş en iyi
     tahmini veriyor" diye ölçüyor (2, 3, 5, 7, 10, 14, 21 gün). Gözlemin tarihi
     olmasa o mekanizma çalışmaz ve "her geçen gün daha iyi" iddiası çöker.
     Yani havuz, mevcut pencere mantığını BOZMUYOR — aynı mantığı ham veri
     olmadan sürdürüyor.

⚠️ KOVA SINIRI — kayan pencere, kayıp değil
  Kova başına en fazla KOVA_SINIRI gözlem tutuluyor; taşınca EN ESKİLER atılıyor.
  Bu bir kayıp değil, zaten var olan tasarım: model hâlihazırda 5 günlük pencere
  kullanıyor, yani eski gözlemler şu an da hesaba girmiyor.
  Ölçüldü: kovaların %99'unda 20'den az gözlem var, en kalabalık kovada 277.
  Sınır 120 → hiçbir kova bugün sınıra dayanmıyor, ama boyut ÜST SINIRA bağlanıyor.

ÇALIŞTIRMA
    python3 parca_havuz.py doldur      ham gecis'ten havuzu artımlı besle
    python3 parca_havuz.py ozet        havuzun durumu
"""

import sqlite3
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

VERI = Path(__file__).parent / "veri"

MAX_PARCA_DK = 25         # sure_modeli ile AYNI olmalı
MAX_ATLAMA_SIRA = 1       # yalnızca ardışık duraklar
KOVA_SINIRI = 120         # kova başına en fazla gözlem (en eskiler atılır)
EPOK = datetime(2026, 1, 1)   # gün numarasının başlangıcı


def gun_no(t):
    return (t.date() - EPOK.date()).days


def gun_tipi(t):
    return "C" if t.weekday() == 5 else ("P" if t.weekday() == 6 else "I")


# ─────────────────────────────────────────────────────────────────────────────
# BLOB PAKETLEME — gözlem başına 4 bayt
# ─────────────────────────────────────────────────────────────────────────────

def paketle(gozlemler):
    """[(sure_dk, gun_no), ...] → BLOB. Süre desisaniyeye çevrilir."""
    duz = []
    for dk, g in gozlemler:
        ds = int(round(dk * 600))               # dakika → desisaniye
        duz.append(min(65535, max(0, ds)))
        duz.append(min(65535, max(0, g)))
    return struct.pack("<%dH" % len(duz), *duz)


def coz(blob):
    """BLOB → [(sure_dk, gun_no), ...]"""
    if not blob:
        return []
    n = len(blob) // 2
    v = struct.unpack("<%dH" % n, blob[:n * 2])
    return [(v[i] / 600.0, v[i + 1]) for i in range(0, n - 1, 2)]


# ─────────────────────────────────────────────────────────────────────────────

def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS parca_havuz (
            hat      TEXT NOT NULL,
            yon      TEXT NOT NULL,
            sira     INTEGER NOT NULL,   -- bu duraktan bir SONRAKİNE
            gun_tipi TEXT NOT NULL,
            saat     INTEGER NOT NULL,
            adet     INTEGER NOT NULL,   -- BLOB'daki gözlem sayısı
            sureler  BLOB NOT NULL,      -- gözlem başına 4 bayt: süre + gün no
            PRIMARY KEY (hat, yon, sira, gun_tipi, saat)
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS durum (anahtar TEXT PRIMARY KEY, deger TEXT);
    """)
    db.commit()


def durum_oku(db, anahtar, varsayilan=None):
    r = db.execute("SELECT deger FROM durum WHERE anahtar=?", (anahtar,)).fetchone()
    return r[0] if r else varsayilan


def durum_yaz(db, anahtar, deger):
    db.execute("INSERT OR REPLACE INTO durum (anahtar, deger) VALUES (?,?)",
               (anahtar, str(deger)))


# ─────────────────────────────────────────────────────────────────────────────

def doldur(hepsi=False, sessiz=False):
    """Ham `gecis` tablosundan havuzu besler. ARTIMLI: en son işlenen andan
    itibaren okur, `durum.havuz_islenen` içinde işaretler.

    ⚠️ Tekrar çalıştırılırsa aynı gözlemi iki kez eklemez — sınır zamanı
       veritabanında tutuluyor, hangi süreç çalıştırmış olursa olsun.
    """
    db = sqlite3.connect(str(VERI / "kayit.db"), timeout=300)
    db.execute("PRAGMA busy_timeout=300000")
    tablo_kur(db)

    bas = "2000-01-01 00:00:00" if hepsi else (
        durum_oku(db, "havuz_islenen") or "2000-01-01 00:00:00")
    son = db.execute("SELECT MAX(zaman) FROM gecis").fetchone()[0]
    if not son:
        print("gecis tablosu boş.")
        return
    # ⚠️ Parça, iki ardışık geçişten oluşuyor. Sınırda kalan parçayı kaçırmamak
    #    için bir miktar GERİYE dönülüyor (bir parça en fazla MAX_PARCA_DK sürer).
    okuma_bas = (datetime.strptime(bas, "%Y-%m-%d %H:%M:%S")
                 - timedelta(minutes=MAX_PARCA_DK + 5)).strftime("%Y-%m-%d %H:%M:%S")

    if not sessiz:
        print("havuz besleniyor: %s → %s" % (okuma_bas[:16], son[:16]))

    hatlar = [r[0] for r in db.execute(
        "SELECT DISTINCT hat FROM gecis WHERE zaman > ?", (okuma_bas,))]
    if not sessiz:
        print("%d hat işlenecek\n" % len(hatlar))

    yeni_gozlem = dokunulan_kova = 0
    for i, hat in enumerate(hatlar, 1):
        kova = {}
        for yon in ("G", "D"):
            satir = db.execute(
                "SELECT kapino, zaman, sira FROM gecis"
                " WHERE hat=? AND yon=? AND zaman > ? ORDER BY kapino, zaman",
                (hat, yon, okuma_bas)).fetchall()
            onceki = None
            for kapino, zaman, sira in satir:
                an = datetime.strptime(zaman, "%Y-%m-%d %H:%M:%S")
                if (onceki and onceki[0] == kapino
                        and sira - onceki[2] == MAX_ATLAMA_SIRA):
                    dk = (an - onceki[1]).total_seconds() / 60
                    if 0 < dk <= MAX_PARCA_DK:
                        t0 = onceki[1]
                        kova.setdefault((yon, onceki[2], gun_tipi(t0), t0.hour),
                                        []).append((dk, gun_no(t0)))
                onceki = (kapino, an, sira)

        for (yon, sira, gt, saat), yeni in kova.items():
            r = db.execute(
                "SELECT sureler FROM parca_havuz"
                " WHERE hat=? AND yon=? AND sira=? AND gun_tipi=? AND saat=?",
                (hat, yon, sira, gt, saat)).fetchone()
            var = coz(r[0]) if r else []
            # ⚠️ Mükerrer engelleme: aynı (süre, gün) çifti zaten varsa eklenmez.
            #    Artımlı çalışmada sınır bölgesi iki kez okunuyor (yukarıya bak).
            mevcut = set(var)
            eklenen = [g for g in yeni if g not in mevcut]
            if not eklenen:
                continue
            hepsi_g = var + eklenen
            # taşarsa EN ESKİLER atılır (gün numarasına göre)
            if len(hepsi_g) > KOVA_SINIRI:
                hepsi_g.sort(key=lambda x: x[1])
                hepsi_g = hepsi_g[-KOVA_SINIRI:]
            db.execute(
                "INSERT OR REPLACE INTO parca_havuz"
                " (hat,yon,sira,gun_tipi,saat,adet,sureler) VALUES (?,?,?,?,?,?,?)",
                (hat, yon, sira, gt, saat, len(hepsi_g), paketle(hepsi_g)))
            yeni_gozlem += len(eklenen)
            dokunulan_kova += 1

        if i % 50 == 0:
            db.commit()
            if not sessiz:
                print("  %d/%d hat · +%d gözlem" % (i, len(hatlar), yeni_gozlem))

    durum_yaz(db, "havuz_islenen", son)
    db.commit()
    r = db.execute("SELECT COUNT(*), SUM(adet) FROM parca_havuz").fetchone()
    if sessiz:
        # ⚠️ Döngüden çağrılırken TEK SATIR — log şişmesin ama İZ KALSIN.
        #    Tamamen susan bir adım çöktüğünde fark edilmez; 3 Eylül'de
        #    kaydedici tam böyle sessizce ölmüştü (Bölüm 59).
        print("  havuz: +%s gözlem · %s kova · toplam %s gözlem"
              % ("{:,}".format(yeni_gozlem).replace(",", "."),
                 "{:,}".format(dokunulan_kova).replace(",", "."),
                 "{:,}".format(r[1] or 0).replace(",", ".")))
    else:
        print("\n" + "=" * 58)
        print("  +%d yeni gözlem · %d kova güncellendi" % (yeni_gozlem, dokunulan_kova))
        print("  havuz toplamı: %s kova · %s gözlem"
              % ("{:,}".format(r[0]).replace(",", "."),
                 "{:,}".format(r[1] or 0).replace(",", ".")))
        print("=" * 58)
    db.close()


def ozet():
    db = sqlite3.connect(str(VERI / "kayit.db"), timeout=60)
    tablo_kur(db)
    r = db.execute("SELECT COUNT(*), SUM(adet), AVG(adet), MAX(adet),"
                   " SUM(LENGTH(sureler)) FROM parca_havuz").fetchone()
    b = lambda n: "{:,}".format(int(n or 0)).replace(",", ".")
    print("── PARÇA HAVUZU ──")
    print("   kova            : %s" % b(r[0]))
    print("   gözlem          : %s" % b(r[1]))
    print("   kova başına     : ort %.1f · en çok %s" % (r[2] or 0, b(r[3])))
    print("   BLOB toplamı    : %.1f MB" % ((r[4] or 0) / 1e6))
    print("   son işlenen an  : %s" % durum_oku(db, "havuz_islenen", "—"))
    g = db.execute("SELECT MIN(zaman), MAX(zaman), COUNT(*) FROM gecis").fetchone()
    print("\n── ham gecis (karşılaştırma) ──")
    print("   %s satır · %s → %s" % (b(g[2]), (g[0] or "—")[:16], (g[1] or "—")[:16]))
    db.close()


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "ozet"
    if komut == "doldur":
        doldur(hepsi="--hepsi" in sys.argv, sessiz="--sessiz" in sys.argv)
    else:
        ozet()

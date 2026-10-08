"""
SÜRELER — geçmiş arşivden gerçekleşen seferleri indirir.

NEDEN VAR:
  İki soruyu birden cevaplayan tek kaynak bu:
    1) "98 bu saatte gerçekte kaç dakika sürüyor?"   → varış tahmininin temeli
    2) "Bu kalkış geçmişte kaç kez yapılmadı?"       → iptal tahmininin ön olasılığı
  Arşiv her ikisini de taşıyor: hem gerçek başlama/bitiş zamanı, hem SGOREVDURUM.

⚠️ NEDEN ELDEKİ `gercek_sure_hat_saat.csv` KULLANILMIYOR:
  Eski projeden gelen o dosya YÖN AYIRMIYOR ve "bacak sorunu"nu içeriyor —
  bazı hatlarda bir kayıt gidiş+dönüşü birden sayıyor. Ölçüldü (1. seans):
      98 · yön D → 5 sefer · ortalama  71 dk · aralık  64-79   (tutarlı, tek yön)
      98 · yön G → 45 sefer · ortalama 187 dk · aralık 73-244  (karışık)
  Aynı hattın seferi 74 ile 217 dakika arasında olamaz. O dosya bu iş için bozuk.
  Süreleri yönüyle birlikte kendimiz hesaplıyoruz.

KAYNAK:
  ibb/ibb360.asmx → GetIettArsivGorev_json (Tarih, yyyyMMdd)
  ⚠️ BUGÜN BOŞ DÖNER — arşiv ertesi gün doluyor (Bölüm 2.1). Dün ve öncesi çekilir.

ÇALIŞTIRMA:
    python3 sureler.py [gun_sayisi]      # varsayılan 14
  Yarıda kesilirse tekrar çalıştır; çekilmiş günleri atlar.

ÇIKTI:  veri/dizin.db → sefer tablosu
"""

import re
import sys
import time
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from durak_dizini import soap_json, veritabani_kur

YOL = "ibb/ibb360.asmx"
SURE_ALT, SURE_UST = 5, 400        # dışındakiler bozuk kayıt (ölçüldü, eski proje)
GUNLER_ARASI_SN = 2


def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sefer (
            tarih        TEXT NOT NULL,    -- yyyyMMdd, arşivin sorulduğu gün
            hat_kodu     TEXT,
            guzergah     TEXT,             -- "98_D_D0"
            yon          TEXT,             -- guzergah'ın orta harfi: G / D
            arac         TEXT,
            plan_zaman   TEXT,             -- planlanan başlangıç
            bas_zaman    TEXT,             -- gerçek başlangıç (iptalde boş)
            bit_zaman    TEXT,
            sure_dk      REAL,             -- bitiş - başlangıç (filtrelenmiş)
            plan_saat    INTEGER,          -- planlanan kalkışın saati (0-23)
            gun_tipi     TEXT,             -- I hafta içi · C cumartesi · P pazar
            durum        TEXT              -- T tamamlandı · I iptal · YK · A · B
        );
        CREATE INDEX IF NOT EXISTS ix_sefer_hat  ON sefer (hat_kodu, yon, plan_saat);
        CREATE INDEX IF NOT EXISTS ix_sefer_gun  ON sefer (tarih);
        CREATE TABLE IF NOT EXISTS arsiv_gun (
            tarih   TEXT PRIMARY KEY,
            kayit   INTEGER,
            cekildi TEXT
        );
    """)
    db.commit()


def _zaman(deger):
    """/Date(1786096228000)/ → datetime. Boş/bozuksa None."""
    if not deger:
        return None
    m = re.search(r"/Date\((-?\d+)", str(deger))
    if not m:
        return None
    d = datetime.fromtimestamp(int(m.group(1)) / 1000)
    return d if d.year > 2001 else None      # 2000-12-31 = boş değerin epoch karşılığı


def gun_tipi(tarih_metni):
    g = datetime.strptime(tarih_metni, "%Y%m%d").weekday()
    return "C" if g == 5 else ("P" if g == 6 else "I")


def gunu_cek(db, tarih):
    kayitlar = soap_json(YOL, "GetIettArsivGorev_json", {"Tarih": tarih})
    gt = gun_tipi(tarih)
    satirlar = []
    for k in kayitlar:
        guzergah = k.get("SGUZERGAHKODU") or ""
        parca = guzergah.split("_")
        bas, bit = _zaman(k.get("DTBASLAMAZAMANI")), _zaman(k.get("DTBITISZAMANI"))
        plan = _zaman(k.get("DTPLANLANANBASLANGICZAMANI"))

        sure = None
        if bas and bit:
            d = (bit - bas).total_seconds() / 60
            if SURE_ALT <= d <= SURE_UST:      # negatif ve milyonluk süreler var
                sure = d

        satirlar.append((
            tarih, k.get("SHATKODU"), guzergah,
            parca[1] if len(parca) > 1 else None,
            k.get("SKAPINUMARA"),
            plan.isoformat(sep=" ") if plan else None,
            bas.isoformat(sep=" ") if bas else None,
            bit.isoformat(sep=" ") if bit else None,
            sure, plan.hour if plan else None, gt, k.get("SGOREVDURUM")))

    db.execute("DELETE FROM sefer WHERE tarih=?", (tarih,))   # tekrar çekimde çiftlenmesin
    db.executemany("INSERT INTO sefer (tarih,hat_kodu,guzergah,yon,arac,plan_zaman,"
                   "bas_zaman,bit_zaman,sure_dk,plan_saat,gun_tipi,durum)"
                   " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", satirlar)
    db.execute("INSERT OR REPLACE INTO arsiv_gun (tarih, kayit, cekildi) VALUES (?,?,?)",
               (tarih, len(satirlar), datetime.now().isoformat(sep=" ", timespec="seconds")))
    db.commit()
    return len(satirlar)


def calistir(gun_sayisi=14):
    db = veritabani_kur()
    tablo_kur(db)

    bugun = datetime.now().date()
    # bugün boş döner (arşiv ertesi gün doluyor) → dünden geriye
    tarihler = [(bugun - timedelta(days=i)).strftime("%Y%m%d")
                for i in range(1, gun_sayisi + 1)]
    bitmis = {r[0] for r in db.execute("SELECT tarih FROM arsiv_gun")}
    kalan = [t for t in tarihler if t not in bitmis]

    print("istenen %d gün · zaten çekilmiş %d · çekilecek %d\n"
          % (gun_sayisi, len(tarihler) - len(kalan), len(kalan)))

    for i, tarih in enumerate(kalan, 1):
        try:
            basla = time.time()
            n = gunu_cek(db, tarih)
            print("  %s (%s)  %6d kayıt  ·  %.0f sn  [%d/%d]"
                  % (tarih, gun_tipi(tarih), n, time.time() - basla, i, len(kalan)))
        except Exception as e:
            print("  %s  HATA: %s" % (tarih, str(e)[:90]))
        time.sleep(GUNLER_ARASI_SN)

    ozet(db)
    db.close()


def ozet(db):
    print("\n" + "=" * 64)
    n_gun, n_sefer = db.execute(
        "SELECT COUNT(DISTINCT tarih), COUNT(*) FROM sefer").fetchone()
    print("  %d gün · %d sefer kaydı" % (n_gun, n_sefer))
    print("\n  durum dağılımı:")
    for d, n in db.execute("SELECT durum, COUNT(*) FROM sefer"
                           " GROUP BY durum ORDER BY 2 DESC"):
        print("    %-4s %7d  %%%.1f" % (d, n, 100.0 * n / n_sefer))
    print("\n  98 hattı · yön bazında gerçek süre:")
    for yon, n, ort, en_az, en_cok in db.execute(
            "SELECT yon, COUNT(*), AVG(sure_dk), MIN(sure_dk), MAX(sure_dk)"
            " FROM sefer WHERE hat_kodu='98' AND sure_dk IS NOT NULL"
            " GROUP BY yon"):
        print("    yön %s · %4d sefer · ortalama %5.1f dk · aralık %.0f-%.0f"
              % (yon, n, ort, en_az, en_cok))
    print("=" * 64)


if __name__ == "__main__":
    sys.exit(calistir(int(sys.argv[1]) if len(sys.argv) > 1 else 14))

"""
GEÇMİŞ HAT TAHMİNİ — geometrik eşlemeyi geriye dönük üretir.

NEDEN VAR:
  Geometrik tahmin kaydediciye 28 Ağustos 10:30'da bağlandı. Ama doğrulama ancak
  ARŞİVİ OLAN bir gün için yapılabiliyor ve arşiv ertesi gün doluyor. Yani
  "geometrik eşleme yanlış alarmı düşürdü mü?" sorusunu yarını beklemeden
  cevaplamak için, tahmini dünün konum verisi üzerinde yeniden üretmek gerekiyor.

  27 Ağustos'un hem konumları (3,4 milyon kayıt) hem arşivi elimizde.

NE YAPAR:
  Verilen gün için, hareketli araçların hattını belirli aralıklarla geometriden
  çıkarır ve `arac_hat` tablosuna kaynak='geometri' olarak yazar.

⚠️ Kaydedici aynı anda çalışıyor; veritabanı kilidi için uzun timeout ve toplu
   yazma kullanılıyor.

    python3 gecmis_tahmin.py 20260827
"""

import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hat_tahmini

VERI = Path(__file__).parent / "veri"
ADIM_DK = 10               # her araç için kaç dakikada bir tahmin
YAZMA_TOPLU = 400          # bu kadar satır birikince yaz (kilit süresini kısaltır)


def calistir(tarih):
    gun = datetime.strptime(tarih, "%Y%m%d")
    bas, bit = gun, gun + timedelta(days=1)
    db = sqlite3.connect(str(VERI / "kayit.db"), timeout=60)
    db.execute("PRAGMA busy_timeout=60000")

    print("ızgara kuruluyor...")
    t0 = time.time()
    hat_tahmini.izgara()
    print("  %.1f sn\n" % (time.time() - t0))

    # o gün hangi araçlar hareket etmiş
    araclar = [r[0] for r in db.execute(
        "SELECT kapino FROM filo_konum WHERE zaman >= ? AND zaman < ?"
        " GROUP BY kapino HAVING COUNT(*) >= 20",
        (bas.strftime("%Y-%m-%d %H:%M:%S"), bit.strftime("%Y-%m-%d %H:%M:%S")))]
    print("%d araç işlenecek · adım %d dk\n" % (len(araclar), ADIM_DK))

    yazilacak, toplam, karar, t0 = [], 0, 0, time.time()
    for sira, kapino in enumerate(araclar, 1):
        # aracın o gün bildirim yaptığı anlar
        zamanlar = [r[0] for r in db.execute(
            "SELECT zaman FROM filo_konum WHERE kapino=? AND zaman >= ? AND zaman < ?"
            " ORDER BY zaman", (kapino, bas.strftime("%Y-%m-%d %H:%M:%S"),
                                bit.strftime("%Y-%m-%d %H:%M:%S")))]
        if len(zamanlar) < hat_tahmini.MIN_IZ:
            continue
        son_an = None
        for z in zamanlar:
            an = datetime.strptime(z, "%Y-%m-%d %H:%M:%S")
            if son_an and (an - son_an).total_seconds() < ADIM_DK * 60:
                continue
            son_an = an
            toplam += 1
            try:
                iz = hat_tahmini.arac_izi(db, kapino, an)
                t = hat_tahmini.tahmin_et(iz)
            except Exception:
                continue
            if t:
                karar += 1
                yazilacak.append((z, kapino, t[0], "%s_%s_?" % (t[0], t[1]), "geometri"))

        if len(yazilacak) >= YAZMA_TOPLU:
            db.executemany("INSERT OR IGNORE INTO arac_hat (zaman, kapino, hat,"
                           " guzergahkodu, kaynak) VALUES (?,?,?,?,?)", yazilacak)
            db.commit()
            yazilacak = []

        if sira % 200 == 0:
            gecen = time.time() - t0
            kalan = gecen / sira * (len(araclar) - sira)
            print("  %4d/%d araç · %d tahmin · %d karar (%%%.0f) · tahmini kalan %.0f dk"
                  % (sira, len(araclar), toplam, karar,
                     100.0 * karar / max(toplam, 1), kalan / 60))

    if yazilacak:
        db.executemany("INSERT OR IGNORE INTO arac_hat (zaman, kapino, hat,"
                       " guzergahkodu, kaynak) VALUES (?,?,?,?,?)", yazilacak)
        db.commit()

    print("\n" + "=" * 60)
    print("  %d tahmin denendi · %d karar verildi (%%%.0f)"
          % (toplam, karar, 100.0 * karar / max(toplam, 1)))
    r = db.execute("SELECT COUNT(*), COUNT(DISTINCT hat) FROM arac_hat"
                   " WHERE kaynak='geometri' AND zaman >= ? AND zaman < ?",
                   (bas.strftime("%Y-%m-%d %H:%M:%S"),
                    bit.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()
    print("  o güne yazılan geometrik eşleme: %d · %d hat" % r)
    print("=" * 60)
    db.close()


if __name__ == "__main__":
    calistir(sys.argv[1] if len(sys.argv) > 1 else
             (datetime.now() - timedelta(days=1)).strftime("%Y%m%d"))

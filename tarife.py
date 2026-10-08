"""
TARİFE — hangi hat, hangi gün tipinde, saat kaçta kalkıyor.

NEDEN VAR:
  "Hayalet sefer" = tarifede olup ortada görünmeyen kalkış. Yani tanımın kendisi
  tarifeye dayanıyor: plan olmadan "eksik" diye bir şey söylenemez. Kaydedici
  gerçeği topluyor, bu betik planı getiriyor; ikisinin FARKI ürünün ana fikri.

KAYNAK:
  UlasimAnaVeri/PlanlananSeferSaati.asmx → GetPlanlananSeferSaati_json (HatKodu)

  Alanlar: SHATKODU, HATADI, SGUZERAH (evet, serviste böyle yazılı — 'G' eksik),
           SYON, SGUNTIPI, GUZERGAH_ISARETI, SSERVISTIPI, DT

  SGUNTIPI:  I = hafta içi · C = cumartesi · P = pazar
  DT:        "06:15" metni — kalkış saati

⚠️ Tarife TARİHE değil GÜN TİPİNE bağlı. Yani "25 Ağustos'ta ne planlanmıştı"
   sorusunun cevabı yok; "hafta içi ne planlanır" var. Belirli bir günün gerçek
   planı ancak arşiv görev kaydından (GetIettArsivGorev_json) okunabiliyor.

ÇALIŞTIRMA:
    python3 tarife.py         # yarıda kesilirse kaldığı yerden devam eder

ÇIKTI:  veri/dizin.db → tarife tablosu
"""

import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from durak_dizini import soap_json, veritabani_kur, BEKLEME_MERDIVENI, ISTEK_ARASI_SN

YOL = "UlasimAnaVeri/PlanlananSeferSaati.asmx"


def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS tarife (
            hat_kodu     TEXT NOT NULL,
            yon          TEXT,          -- G / D
            gun_tipi     TEXT,          -- I hafta içi · C cumartesi · P pazar
            saat         TEXT,          -- "06:15"
            servis_tipi  TEXT,          -- Normal, ÖHO, OAS, Ara Dinlen ...
            guzergah     TEXT,
            guzergah_isareti TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_tarife_hat
            ON tarife (hat_kodu, gun_tipi, yon);
        -- 'şu an hangi kalkış yaklaşıyor' sorgusu saate göre süzecek:
        CREATE INDEX IF NOT EXISTS ix_tarife_saat
            ON tarife (gun_tipi, saat);
    """)
    # hangi hattın tarifesi çekildi — tekrar çalıştırınca atlamak için
    sutunlar = [r[1] for r in db.execute("PRAGMA table_info(hat)")]
    if "tarife_durum" not in sutunlar:
        db.execute("ALTER TABLE hat ADD COLUMN tarife_durum TEXT")
    db.commit()


def hattin_tarifesi(db, hat_kodu):
    satirlar = soap_json(YOL, "GetPlanlananSeferSaati_json", {"HatKodu": hat_kodu})
    if not satirlar:
        return 0
    db.executemany(
        "INSERT INTO tarife (hat_kodu, yon, gun_tipi, saat, servis_tipi, guzergah,"
        " guzergah_isareti) VALUES (?,?,?,?,?,?,?)",
        [(hat_kodu, s.get("SYON"), s.get("SGUNTIPI"), s.get("DT"),
          s.get("SSERVISTIPI"), s.get("SGUZERAH"), s.get("GUZERGAH_ISARETI"))
         for s in satirlar])
    return len(satirlar)


def calistir():
    db = veritabani_kur()
    tablo_kur(db)

    kalan = [r[0] for r in db.execute(
        "SELECT hat_kodu FROM hat WHERE tarife_durum IS NULL ORDER BY hat_kodu")]
    print("tarifesi çekilecek hat: %d\n" % len(kalan))

    basladi, ustuste_hata = time.time(), 0
    try:
        for i, hat in enumerate(kalan, 1):
            try:
                n = hattin_tarifesi(db, hat)
                db.execute("UPDATE hat SET tarife_durum=? WHERE hat_kodu=?",
                           ("ok" if n else "bos", hat))
                ustuste_hata = 0
            except Exception as e:
                ustuste_hata += 1
                print("  ! %-8s %s" % (hat, str(e)[:70]))
                if ustuste_hata >= 3:
                    bekle = BEKLEME_MERDIVENI[min(ustuste_hata - 3, len(BEKLEME_MERDIVENI) - 1)]
                    print("  ↳ %d saniye susuluyor" % bekle)
                    time.sleep(bekle)
                continue

            if i % 50 == 0 or i == len(kalan):
                db.commit()
                gecen = time.time() - basladi
                n_kalkis = db.execute("SELECT COUNT(*) FROM tarife").fetchone()[0]
                print("  %4d/%d  ·  %7d kalkış  ·  tahmini kalan %d dk"
                      % (i, len(kalan), n_kalkis, gecen / i * (len(kalan) - i) / 60 + 0.5))
            time.sleep(ISTEK_ARASI_SN)
    except KeyboardInterrupt:
        print("\ndurduruldu — tekrar çalıştırınca devam eder.")
    finally:
        db.commit()
        print("\n" + "=" * 56)
        print("  toplam kalkış :", db.execute("SELECT COUNT(*) FROM tarife").fetchone()[0])
        for gt, n in db.execute("SELECT gun_tipi, COUNT(*) FROM tarife"
                                " GROUP BY gun_tipi ORDER BY 2 DESC"):
            print("    gün tipi %-4s %d" % (gt, n))
        print("  tarifesi boş hat:",
              db.execute("SELECT COUNT(*) FROM hat WHERE tarife_durum='bos'").fetchone()[0])
        print("=" * 56)
        db.close()


if __name__ == "__main__":
    sys.exit(calistir())

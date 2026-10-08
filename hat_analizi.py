"""
HAT ANALİZİ — hangi hatlarda yöntem çalışıyor, hangilerinde çalışmıyor, NEDEN?

NEDEN VAR:
  Üç günlük doğrulamada precision %11-15 bandında tıkandı. Ama dağılım eşit değil:
  bazı hatlar (BA-2, 500L, UM73) sıfır yanlış alarm veriyor, bazıları (19EK, 147)
  düzinelerce. Bu farkın sebebini bulmak, ortalamayı yükseltmenin en hızlı yolu —
  çünkü ya düzeltilebilir bir kusur bulunur, ya da "yalnızca şu tip hatlarda göster"
  diyebileceğimiz net bir kural çıkar.

NE YAPAR:
  Her hat için doğrulama sonucunu (kapsanan/doğru/yanlış alarm) hattın ÖZELLİKLERİYLE
  yan yana koyar: sefer aralığı, rota uzunluğu, durak sayısı, güzergâh varyantı sayısı,
  günlük kalkış sayısı, araç sayısı, eşleme yoğunluğu.
  Sonra her özelliği "yanlış alarm oranı" ile ilişkilendirir.

    python3 hat_analizi.py 20260830
"""

import sqlite3
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hayalet
import rota

VERI = Path(__file__).parent / "veri"
EN_AZ_KALKIS = 20          # bundan az kalkışı kapsanan hat istatistiğe girmez


def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS hat_performans (
            tarih TEXT, hat TEXT,
            kapsanan INTEGER, dogru INTEGER,
            gercek_iptal INTEGER, yakalanan INTEGER, yanlis_alarm INTEGER, kacan INTEGER,
            sefer_araligi REAL, rota_km REAL, durak_sayisi INTEGER,
            varyant_sayisi INTEGER, gunluk_kalkis INTEGER, arac_sayisi INTEGER,
            esleme_saati INTEGER, gecis_sayisi INTEGER,
            PRIMARY KEY (tarih, hat)
        );
    """)
    db.commit()


def hat_ozellikleri(dizin, kayit, hat, tarih):
    o = {}
    gt = hayalet.gun_tipi(tarih)
    planlar = [(p, y, g) for p, y, g in hayalet.planli_kalkislar(dizin, hat, tarih)]
    o["gunluk_kalkis"] = len(planlar)
    araliklar = []
    for yon in ("G", "D"):
        yp = [p for p in planlar if p[1] == yon]
        a = hayalet.sefer_araligi(yp)
        if a:
            araliklar.append(a)
    o["sefer_araligi"] = statistics.mean(araliklar) if araliklar else None
    o["varyant_sayisi"] = dizin.execute(
        "SELECT COUNT(DISTINCT guzergah) FROM tarife WHERE hat_kodu=? AND gun_tipi=?",
        (hat, gt)).fetchone()[0]
    o["durak_sayisi"] = dizin.execute(
        "SELECT COUNT(*) FROM hat_durak WHERE hat_kodu=?", (hat,)).fetchone()[0]
    try:
        o["rota_km"] = max(rota.rota_uzunlugu(hat, y) for y in ("G", "D")
                           if hat in rota._rotalar() and y in rota._rotalar()[hat]) / 1000
    except (KeyError, ValueError):
        o["rota_km"] = None
    gun = "%s-%s-%s%%" % (tarih[:4], tarih[4:6], tarih[6:])
    o["arac_sayisi"] = kayit.execute(
        "SELECT COUNT(DISTINCT kapino) FROM arac_hat WHERE hat=? AND zaman LIKE ?",
        (hat, gun)).fetchone()[0]
    o["esleme_saati"] = kayit.execute(
        "SELECT COUNT(DISTINCT substr(zaman,12,2)) FROM arac_hat WHERE hat=? AND zaman LIKE ?",
        (hat, gun)).fetchone()[0]
    o["gecis_sayisi"] = kayit.execute(
        "SELECT COUNT(*) FROM gecis WHERE hat=? AND zaman LIKE ?", (hat, gun)).fetchone()[0]
    return o


def calistir(tarih):
    dizin = sqlite3.connect(str(VERI / "dizin.db"), timeout=60)
    kayit = sqlite3.connect(str(VERI / "kayit.db"), timeout=60)
    tablo_kur(kayit)
    gun = "%s-%s-%s%%" % (tarih[:4], tarih[4:6], tarih[6:])

    hatlar = [r[0] for r in kayit.execute(
        "SELECT hat FROM gecis WHERE zaman LIKE ? GROUP BY hat HAVING COUNT(*) >= 20", (gun,))]
    print("%d hat değerlendiriliyor...\n" % len(hatlar))

    yazilan = 0
    for i, hat in enumerate(hatlar, 1):
        try:
            sonuc = hayalet.degerlendir(hat, tarih)
        except Exception:
            continue
        gercek = {p[11:16]: d for p, d in dizin.execute(
            "SELECT plan_zaman, durum FROM sefer WHERE hat_kodu=? AND tarih=?", (hat, tarih)) if p}
        if not gercek:
            continue
        k = d = gi = ya = yal = ki = 0
        for s in sonuc:
            g = gercek.get(s["plan"].strftime("%H:%M"))
            if g is None or s["durum"] == "bilinmiyor":
                continue
            k += 1
            oldu = g == "T"
            gi += (not oldu)
            tahmin = s["durum"] in ("yapildi", "gps_karanligi")
            if tahmin == oldu:
                d += 1
                ya += (not oldu)
            elif s["durum"] == "iptal":
                yal += 1
            else:
                ki += 1
        if k < EN_AZ_KALKIS:
            continue
        o = hat_ozellikleri(dizin, kayit, hat, tarih)
        kayit.execute("""INSERT OR REPLACE INTO hat_performans VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tarih, hat, k, d, gi, ya, yal, ki, o["sefer_araligi"], o["rota_km"],
             o["durak_sayisi"], o["varyant_sayisi"], o["gunluk_kalkis"],
             o["arac_sayisi"], o["esleme_saati"], o["gecis_sayisi"]))
        yazilan += 1
        if i % 100 == 0:
            kayit.commit()
            print("  %d/%d hat" % (i, len(hatlar)))
    kayit.commit()
    print("\n%d hat tabloya yazıldı" % yazilan)
    rapor(kayit, tarih)
    dizin.close(); kayit.close()


def rapor(kayit, tarih):
    sat = kayit.execute("SELECT * FROM hat_performans WHERE tarih=?", (tarih,)).fetchall()
    ad = [d[0] for d in kayit.execute("SELECT * FROM hat_performans LIMIT 1").description]
    kayitlar = [dict(zip(ad, s)) for s in sat]
    for r in kayitlar:
        r["ya_orani"] = 100.0 * r["yanlis_alarm"] / r["kapsanan"]

    print("\n" + "=" * 72)
    print("  ÖZELLİK vs YANLIŞ ALARM ORANI")
    print("=" * 72)
    print("  Her özellik için hatlar dörde bölünüp ortalama yanlış alarm oranına bakıldı.")
    print("  Bir özellik ayırt ediciyse dilimler arasında belirgin fark olmalı.\n")

    for ozellik, etiket in (("sefer_araligi", "sefer aralığı (dk)"),
                            ("rota_km", "rota uzunluğu (km)"),
                            ("durak_sayisi", "durak sayısı"),
                            ("varyant_sayisi", "güzergâh varyantı"),
                            ("gunluk_kalkis", "günlük kalkış"),
                            ("arac_sayisi", "araç sayısı"),
                            ("esleme_saati", "eşleme yapılan saat"),
                            ("gecis_sayisi", "geçiş sayısı")):
        var = [r for r in kayitlar if r.get(ozellik) is not None]
        if len(var) < 20:
            continue
        var.sort(key=lambda r: r[ozellik])
        n = len(var) // 4
        print("  %-22s" % etiket, end="")
        for i in range(4):
            dilim = var[i*n:(i+1)*n] if i < 3 else var[3*n:]
            ort = statistics.mean(r["ya_orani"] for r in dilim)
            aralik = "%.0f-%.0f" % (dilim[0][ozellik], dilim[-1][ozellik])
            print("  %s:%%%.1f" % (aralik, ort), end="")
        print()

    print("\n" + "=" * 72)
    temiz = [r for r in kayitlar if r["yanlis_alarm"] == 0]
    kirli = sorted(kayitlar, key=lambda r: -r["ya_orani"])[:10]
    print("  TERTEMİZ HATLAR (0 yanlış alarm): %d / %d" % (len(temiz), len(kayitlar)))
    for r in sorted(temiz, key=lambda r: -r["kapsanan"])[:8]:
        print("    %-8s %3d kalkış · aralık %s dk · %s araç · %s varyant"
              % (r["hat"], r["kapsanan"],
                 "%.0f" % r["sefer_araligi"] if r["sefer_araligi"] else "?",
                 r["arac_sayisi"], r["varyant_sayisi"]))
    print("\n  EN BOZUK HATLAR:")
    for r in kirli[:8]:
        print("    %-8s %%%.0f yanlış alarm · %3d kalkış · aralık %s dk · %s araç · %s varyant"
              % (r["hat"], r["ya_orani"], r["kapsanan"],
                 "%.0f" % r["sefer_araligi"] if r["sefer_araligi"] else "?",
                 r["arac_sayisi"], r["varyant_sayisi"]))
    print("=" * 72)


if __name__ == "__main__":
    calistir(sys.argv[1] if len(sys.argv) > 1 else "20260830")

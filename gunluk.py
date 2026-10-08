"""
GÜNLÜK RUTİN — her sabah çalıştırılacak tek komut.

    python3 gunluk.py            # dünü işler
    python3 gunluk.py 20260827   # belirli bir günü işler

DÖRT İŞİ SIRAYLA YAPAR:
  1. Dünün arşivini indirir      → gerçek: hangi sefer yapıldı, hangisi iptal
  2. Yeni konum kayıtlarını işler → geçiş tablosunu büyütür
  3. SÜRE MODELİNİ TAZELER       → en iyi pencereyi ölçer, modeli yeniden kurar
  4. GENİŞ DOĞRULAMA             → tüm hatlarda tahminlerimizi gerçekle kıyaslar

⭐ 3. adım, "her geçen gün daha isabetli olsun" isteğinin mekanizması: model
   donmuş bir tablo değil, her sabah dünkü veriyle yeniden kuruluyor. Üstelik
   kaç günlük pencerenin en iyi olduğu da her gün yeniden ölçülüyor — bugün
   2 gün kazanırken üç hafta sonra 7 gün kazanabilir.

⚠️ Arşiv ERTESİ GÜN doluyor (ölçüldü — Bölüm 2.1). Bugünü sormak boş döner;
   bu yüzden varsayılan "dün".

Doğrulama neden değerli: tahmini biz kalkıştan önce, yalnızca konum verisinden
veriyoruz. Arşiv cevabı ertesi gün söylüyor. Yani her gün, cevabı görmeden
verilmiş bir sınavın kâğıdı okunuyor.
"""

import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gecisler
import hayalet
import sure_modeli
import sureler

VERI = Path(__file__).parent / "veri"
EN_AZ_KAPSANAN = 5          # bu kadar kalkışı kapsanmayan hat rapora girmez


def baslik(metin):
    print("\n" + "=" * 72)
    print("  " + metin)
    print("=" * 72)


def adim1_arsiv(tarih):
    baslik("1/5 · ARŞİV — %s gününün gerçeği indiriliyor" % tarih)
    db = sureler.veritabani_kur()
    sureler.tablo_kur(db)
    var = db.execute("SELECT kayit FROM arsiv_gun WHERE tarih=?", (tarih,)).fetchone()
    if var:
        print("  zaten indirilmiş (%d kayıt) — atlanıyor" % var[0])
    else:
        # ⚠️ TEKRAR DENEME (2 Eylül'de eklendi): rutin bu adımda `HTTP 503`
        #    alıp TEK denemede pes etti ve günün doğrulaması hiç koşmadı —
        #    elle tekrar çalıştırınca ilk denemede indi. 503/500 İETT tarafında
        #    geçici; gece de iki kez görüldü (02:34, 06:34).
        #    Bu adım başarısız olursa 4/5 ve 5/5 doğrulamaları da anlamsızlaşıyor,
        #    yani günün tüm sınavı tek geçici hataya bağlı kalıyordu.
        for deneme in range(1, 4):
            try:
                n = sureler.gunu_cek(db, tarih)
                print("  %d sefer kaydı indirildi%s"
                      % (n, "" if deneme == 1 else "  (%d. denemede)" % deneme))
                if n == 0:
                    print("  ⚠️ BOŞ DÖNDÜ — arşiv henüz dolmamış olabilir (ertesi gün dolar)")
                break
            except Exception as e:
                print("  deneme %d başarısız: %s" % (deneme, str(e)[:110]))
                if deneme < 3:
                    time.sleep(30)
                else:
                    print("  ❌ üç denemede de indirilemedi — doğrulama adımları atlanacak")
    db.close()


def adim2_gecisler():
    baslik("2/5 · GEÇİŞLER — yeni konum kayıtları işleniyor")
    try:
        gecisler.isle(hepsi=False)
    except Exception as e:
        print("  ❌ %s" % str(e)[:150])



def adim3_sure_modeli(tarih):
    baslik("3/5 · SÜRE MODELİ — kayan pencere ayarlanıyor ve model tazeleniyor")
    try:
        pencere = sure_modeli.pencere_ayarla(tarih)
        print()
        sure_modeli.kur(pencere)
    except Exception as e:
        print("  ❌ %s" % str(e)[:160])


def adim4_dogrulama(tarih):
    baslik("4/5 · GENİŞ DOĞRULAMA — %s" % tarih)
    kayit = sqlite3.connect(str(VERI / "kayit.db"))
    dizin = sqlite3.connect(str(VERI / "dizin.db"))

    # O gün geçiş gözlemlediğimiz hatlar
    hatlar = [r[0] for r in kayit.execute(
        "SELECT hat, COUNT(*) FROM gecis WHERE zaman LIKE ? GROUP BY hat"
        " HAVING COUNT(*) >= 20 ORDER BY COUNT(*) DESC",
        (datetime.strptime(tarih, "%Y%m%d").strftime("%Y-%m-%d") + "%",))]
    if not hatlar:
        print("  o güne ait yeterli geçiş gözlemi yok.")
        kayit.close(); dizin.close()
        return
    print("  %d hatta yeterli gözlem var, değerlendiriliyor...\n" % len(hatlar))

    toplam = {"kapsanan": 0, "dogru": 0, "yanlis_alarm": 0,
              "kacan_iptal": 0, "yakalanan_iptal": 0, "gercek_iptal": 0}
    satirlar = []

    for hat in hatlar:
        try:
            sonuc = hayalet.degerlendir(hat, tarih)
        except Exception:
            continue
        gercek = {}
        for plan, durum in dizin.execute(
                "SELECT plan_zaman, durum FROM sefer WHERE hat_kodu=? AND tarih=?",
                (hat, tarih)):
            if plan:
                gercek[plan[11:16]] = durum
        if not gercek:
            continue

        k = d = ya = ki = yi = gi = 0
        for s in sonuc:
            g = gercek.get(s["plan"].strftime("%H:%M"))
            if g is None or s["durum"] == "bilinmiyor":
                continue
            k += 1
            oldu = g == "T"
            if not oldu:
                gi += 1
            tahmin = s["durum"] in ("yapildi", "gps_karanligi")
            if tahmin == oldu:
                d += 1
                if not oldu:
                    yi += 1
            else:
                if s["durum"] == "iptal":
                    ya += 1
                else:
                    ki += 1
        if k < EN_AZ_KAPSANAN:
            continue
        satirlar.append((hat, k, d, gi, yi, ya, ki))
        for anahtar, deger in zip(
                ["kapsanan", "dogru", "gercek_iptal", "yakalanan_iptal",
                 "yanlis_alarm", "kacan_iptal"], [k, d, gi, yi, ya, ki]):
            toplam[anahtar] += deger

    if not satirlar:
        print("  değerlendirilebilir hat çıkmadı (kapsama yetersiz).")
        kayit.close(); dizin.close()
        return

    satirlar.sort(key=lambda r: -r[1])
    print("  %-8s %8s %8s %8s %8s %8s %8s" %
          ("hat", "kapsanan", "doğru", "iptal", "yakalanan", "yanlış", "kaçan"))
    print("  " + "-" * 66)
    for hat, k, d, gi, yi, ya, ki in satirlar[:30]:
        print("  %-8s %8d %8d %8d %8d %8d %8d" % (hat, k, d, gi, yi, ya, ki))

    print("\n  " + "-" * 66)
    k, d = toplam["kapsanan"], toplam["dogru"]
    print("  TOPLAM  · %d hat · %d kalkış kapsandı · %d doğru (%%%.1f)"
          % (len(satirlar), k, d, 100.0 * d / k if k else 0))
    gi, yi = toplam["gercek_iptal"], toplam["yakalanan_iptal"]
    print("  İPTAL   · gerçekte %d · yakalanan %d (%%%.0f) · kaçan %d · yanlış alarm %d"
          % (gi, yi, 100.0 * yi / gi if gi else 0, toplam["kacan_iptal"], toplam["yanlis_alarm"]))
    print("\n  ⚠️ Yanlış alarm sayısı en önemli sütun: 'iptal' deyip otobüs gelirse")
    print("     yolcu uygulamayı bir daha açmaz.")
    kayit.close(); dizin.close()


def adim5_gps_karanligi(tarih):
    """⭐ 'Yolda ama görünmüyor' iddialarını arşivdeki gerçekle kıyaslar.

    Bu adım ancak `gps_izleyici.py` gün boyunca iddiaları KAYDETTİYSE anlamlı.
    Tahmin verildiği anda yazılmazsa ertesi gün kıyaslanacak bir şey kalmıyor —
    `yoklama` tablosu dersinin aynısı (Bölüm 7).
    """
    baslik("5/5 · GPS KARANLIĞI — 'yolda ama görünmüyor' iddiaları")
    try:
        import gps_izleyici
        gps_izleyici.dogrula(tarih)
    except Exception as e:
        print("  ❌ %s" % str(e)[:160])


if __name__ == "__main__":
    tarih = sys.argv[1] if len(sys.argv) > 1 else \
        (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    print("\nGÜNLÜK RUTİN · hedef gün: %s · çalıştırma: %s"
          % (tarih, datetime.now().strftime("%d.%m.%Y %H:%M")))
    adim1_arsiv(tarih)
    adim2_gecisler()
    adim3_sure_modeli(tarih)
    adim4_dogrulama(tarih)
    adim5_gps_karanligi(tarih)
    print()

"""
SÜRE MODELİ — durak arası gerçek süreleri SAAT SAAT öğrenir.

NEDEN VAR — ürünün asıl vaadi bu:
  "98 Bakırköy'den 23:00'te kalktı, Sefaköy'e ne zaman varır?" sorusunun cevabı
  saat 14:00'teki cevapla AYNI OLAMAZ. Trafik farklı, duraklarda inen-binen farklı.

  İlk sürüm bunu yapmıyordu: hattın tek bir ortanca süresini alıp rota oranıyla
  çarpıyordu (ortanca hata 2,4 dk). Yani "yolun %28'ini yaptıysa sürenin de %28'ini
  harcamıştır" varsayımı — oysa şehir içi bölüm ağır, çevre yolu hızlı.

NASIL ÇALIŞIR:
  `gecis` tablosunda hangi aracın hangi duraktan kaçta geçtiği yazıyor. Aynı aracın
  ARDIŞIK iki durak geçişi bir "parça süresi" verir. Bunlar toplanıp
  (hat, yön, parça, gün tipi, saat) kırılımında ortancası alınıyor.

  Sonra A durağından B durağına süre = aradaki parçaların toplamı. ⭐ Toplarken SAAT
  İLERLETİLİYOR: 23:00'te kalkan otobüs 40 dakika sonra 23:40'ın parça sürelerini
  yaşar. Uzun hatlarda bu fark büyük.

⚠️ Veri az olan parçalarda hat ortalamasına düşülüyor; uydurulmuyor, işaretleniyor.

    python3 sure_modeli.py kur          # modeli geçmiş veriden kur
    python3 sure_modeli.py sina         # isabetini ölç
"""

import sqlite3
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

VERI = Path(__file__).parent / "veri"

MAX_PARCA_DK = 25          # iki komşu durak arası bundan uzunsa kayıt bozuk/kopuk
MIN_ORNEK = 4              # bir parça-saat için en az bu kadar gözlem
MAX_ATLAMA_SIRA = 1        # yalnızca ardışık duraklar (sıra farkı 1)

# ⭐ KAYAN PENCERE — 31 Ağustos'ta ölçülerek eklendi.
#   "Tüm geçmişi biriktir, ortancasını al" YANLIŞ çıktı:
#       2 günlük veriyle eğitim → ortanca hata 2,82 dk
#       3 günlük veriyle eğitim → ortanca hata 3,29 dk   ← daha KÖTÜ
#   EWMA da denendi (α=0,5 ve 0,7), havuzu geçemedi.
#   Doğru pencere veri biriktikçe DEĞİŞECEĞİ için sabitlenmiyor:
#   her gün birkaç pencere denenip en iyisi seçiliyor (bkz. pencere_ayarla).
VARSAYILAN_PENCERE = 2     # gün · ayarlama yapılmamışsa
# ⭐ 21 EKLENDİ (3 Eylül): ham `gecis` artık 28 günde budanıyor (kaydedici.buda),
#   yani en fazla 21 günlük pencere GÜVENLE denenebilir. Sınırı 14'te bırakmak,
#   "her geçen gün daha iyi tahmin" iddiasına tavan koyardı: model daha uzun
#   geçmişin işe yarayıp yaramadığını hiç SINAYAMAZDI.
#   Veri o kadar birikmemişse uzun pencereler kısa olanla aynı sonucu verir
#   (ölçüldü: 5/7/10/14 aynı çıkıyordu) — zararsız, sadece bekliyor.
DENENEN_PENCERELER = (2, 3, 5, 7, 10, 14, 21)


def gun_tipi(t):
    return "C" if t.weekday() == 5 else ("P" if t.weekday() == 6 else "I")


def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS parca_sure (
            hat       TEXT NOT NULL,
            yon       TEXT NOT NULL,
            sira      INTEGER NOT NULL,   -- bu duraktan bir SONRAKİNE
            gun_tipi  TEXT NOT NULL,
            saat      INTEGER NOT NULL,
            ortanca   REAL, p10 REAL, p90 REAL, n INTEGER,
            PRIMARY KEY (hat, yon, sira, gun_tipi, saat)
        );
        -- saat kırılımı olmayan yedek: parçanın gün geneli ortancası
        CREATE TABLE IF NOT EXISTS parca_sure_genel (
            hat TEXT, yon TEXT, sira INTEGER, gun_tipi TEXT,
            ortanca REAL, n INTEGER,
            PRIMARY KEY (hat, yon, sira, gun_tipi)
        );
        CREATE INDEX IF NOT EXISTS ix_gecis_arac ON gecis (kapino, hat, yon, zaman);
    """)
    db.commit()


def kur(pencere_gun=None):
    """⭐ ARTIMLI MİMARİ (4 Eylül) — ham veriden değil, HAVUZDAN besleniyor.

    ⚠️ ESKİDEN: her çağrıda ham `gecis` tablosu baştan taranıyordu. Bu yüzden
       ham veriyi tutmak zorundaydık; günde 0,44 GB büyüyordu ve 3 Eylül'de
       diski doldurup sistemi öldürdü (Bölüm 59).

    ⭐ ŞİMDİ: `parca_havuz` ham geçişi BİR KEZ işleyip gözlemleri kova başına
       paketli saklıyor (gözlem başına 4 bayt). Ölçüldü:
           ham gecis (veri+4 indeks) : 3,58 GB
           parca_havuz (aynı bilgi)  : 0,11 GB   ← 33 kat küçük
       Ham veri artık yalnızca son birkaç gün için tutuluyor; model tüm geçmişi
       havuzdan hatırlıyor. Mehmet'in fikri: "geçmiş veriden değeri çıkar, ham
       veriyi sil, yeni gelen veriyi o değerin üstüne ekle."

    Gün penceresi mekanizması AYNEN korunuyor: havuzda her gözlemin gün numarası
    da duruyor, `pencere_ayarla()` hâlâ 2/3/5/7/10/14/21 günü deneyebiliyor.
    """
    import parca_havuz as PH
    db = sqlite3.connect(str(VERI / "kayit.db"), timeout=120)
    db.execute("PRAGMA busy_timeout=120000")
    tablo_kur(db)
    PH.tablo_kur(db)

    if pencere_gun is None:
        pencere_gun = secili_pencere(db)
    esik_gun = PH.gun_no(datetime.now()) - pencere_gun
    print("kayan pencere: son %d gün (havuzdan)\n" % pencere_gun)

    hatlar = [r[0] for r in db.execute("SELECT DISTINCT hat FROM parca_havuz")]
    print("%d hat işlenecek\n" % len(hatlar))
    toplam_parca = 0

    for i, hat in enumerate(hatlar, 1):
        kova, kova_genel = {}, {}
        for yon, sira, gt, saat, blob in db.execute(
                "SELECT yon, sira, gun_tipi, saat, sureler FROM parca_havuz WHERE hat=?",
                (hat,)):
            for dk, g in PH.coz(blob):
                if g < esik_gun:          # pencerenin dışında kalan eski gözlem
                    continue
                kova.setdefault((yon, sira, gt, saat), []).append(dk)
                kova_genel.setdefault((yon, sira, gt), []).append(dk)

        satirlar = []
        for (yon, sira, gt, saat), v in kova.items():
            if len(v) < MIN_ORNEK:
                continue
            v.sort()
            satirlar.append((hat, yon, sira, gt, saat, statistics.median(v),
                             v[len(v)//10], v[-max(1, len(v)//10)], len(v)))
        if satirlar:
            db.execute("DELETE FROM parca_sure WHERE hat=?", (hat,))
            db.executemany("INSERT OR REPLACE INTO parca_sure VALUES (?,?,?,?,?,?,?,?,?)", satirlar)
            toplam_parca += len(satirlar)

        genel = [(hat, yon, sira, gt, statistics.median(v), len(v))
                 for (yon, sira, gt), v in kova_genel.items() if len(v) >= MIN_ORNEK]
        if genel:
            db.execute("DELETE FROM parca_sure_genel WHERE hat=?", (hat,))
            db.executemany("INSERT OR REPLACE INTO parca_sure_genel VALUES (?,?,?,?,?,?)", genel)

        if i % 50 == 0:
            db.commit()
            print("  %d/%d hat · %d parça-saat" % (i, len(hatlar), toplam_parca))
    # Modelin ne zaman ve hangi veriye kadar kurulduğu — durum.sh bunu gösteriyor.
    # ⚠️ Bu damga olmadan modelin bayatladığı fark edilmiyordu: 1 Eylül 15:50'de
    #    model hâlâ 31 Ağustos verisiyle çalışıyordu ve kimse görmüyordu.
    db.execute("INSERT OR REPLACE INTO durum (anahtar, deger) VALUES ('sure_kurulum', ?)",
               (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    son = db.execute("SELECT MAX(zaman) FROM gecis").fetchone()[0]
    db.execute("INSERT OR REPLACE INTO durum (anahtar, deger) VALUES ('sure_veri_sonu', ?)",
               (son or "",))
    db.commit()
    print("\n" + "=" * 58)
    print("  parça-saat kaydı : %d" % db.execute("SELECT COUNT(*) FROM parca_sure").fetchone()[0])
    print("  parça (saatsiz)  : %d" % db.execute("SELECT COUNT(*) FROM parca_sure_genel").fetchone()[0])
    print("  kapsanan hat     : %d" % db.execute("SELECT COUNT(DISTINCT hat) FROM parca_sure").fetchone()[0])
    print("=" * 58)
    db.close()



# ─────────────────────────────────────────────────────────────────────────────
# KENDİNİ AYARLAMA
# ─────────────────────────────────────────────────────────────────────────────

def secili_pencere(db):
    """En son ayarlamada kazanan pencere. Hiç ayarlanmamışsa varsayılan."""
    db.execute("CREATE TABLE IF NOT EXISTS durum (anahtar TEXT PRIMARY KEY, deger TEXT)")
    r = db.execute("SELECT deger FROM durum WHERE anahtar='sure_pencere'").fetchone()
    try:
        return int(r[0]) if r else VARSAYILAN_PENCERE
    except (TypeError, ValueError):
        return VARSAYILAN_PENCERE


def pencere_ayarla(hedef_gun, ornek_hat=25, kaynak="havuz"):
    """Birkaç pencere boyunu DÜN üzerinde deneyip en iyisini seçer ve kaydeder.

    ⭐ Neden sabit pencere yok: doğru pencere veri biriktikçe değişir. Bugün 2 gün
    en iyiyken, üç hafta sonra 7 gün daha iyi olabilir (haftalık desenler oturur).
    Sistem bunu kendi ölçüp seçiyor — "her geçen gün daha isabetli olsun" isteğinin
    mekanizması bu.

    hedef_gun: 'YYYYMMDD' — üzerinde sınanacak gün (genelde dün)
    kaynak:    'havuz' (varsayılan) · 'ham' yalnızca doğrulama için — ham yol
               ayarı KAYDETMEZ, sadece ölçer.
    """
    import statistics as _st
    sys.path.insert(0, str(Path(__file__).parent))
    import hayalet, rota
    db = sqlite3.connect(str(VERI / "kayit.db"), timeout=120)
    db.execute("PRAGMA busy_timeout=120000")
    dz = sqlite3.connect(str(VERI / "dizin.db"), timeout=120)
    g = datetime.strptime(hedef_gun, "%Y%m%d")
    gun_str = g.strftime("%Y-%m-%d")

    hatlar = [r[0] for r in db.execute(
        "SELECT hat FROM gecis WHERE zaman LIKE ? GROUP BY hat"
        " ORDER BY COUNT(*) DESC LIMIT ?", (gun_str + "%", ornek_hat))]

    # gerçek: aynı aracın kalkış durağı → orta durak süresi
    gercek = []
    for hat in hatlar:
        for yon in ("G", "D"):
            kd = hayalet.kalkis_durak(dz, hat, yon)
            if not kd:
                continue
            try:
                toplam = rota.rota_uzunlugu(hat, yon)
                dm = rota.durak_mesafeleri(hat, yon)
            except Exception:
                continue
            kodlar = dict(dz.execute(
                "SELECT sira,durak_kodu FROM hat_durak WHERE hat_kodu=? AND yon=?", (hat, yon)))
            aday = [(s, kodlar[s]) for s, ad, m, _ in dm
                    if s in kodlar and 0.35 < m / toplam < 0.75]
            if not aday:
                continue
            os_, od = aday[len(aday) // 2]
            if os_ <= kd[0]:
                continue
            for z, kap in db.execute(
                    "SELECT zaman,kapino FROM gecis WHERE hat=? AND yon=? AND durak_kodu=?"
                    " AND zaman LIKE ?", (hat, yon, kd[1], gun_str + "%")):
                r2 = db.execute(
                    "SELECT zaman FROM gecis WHERE hat=? AND yon=? AND durak_kodu=? AND kapino=?"
                    " AND zaman > ? ORDER BY zaman LIMIT 1", (hat, yon, od, kap, z)).fetchone()
                if not r2:
                    continue
                t0 = datetime.strptime(z, "%Y-%m-%d %H:%M:%S")
                fi = (datetime.strptime(r2[0], "%Y-%m-%d %H:%M:%S") - t0).total_seconds() / 60
                if 1 < fi < 180:
                    gercek.append((hat, yon, kd[0], os_, t0, fi))
    if len(gercek) < 200:
        print("  ayarlama için yeterli gözlem yok (%d)" % len(gercek))
        p = secili_pencere(db)
        db.close(); dz.close()
        return p

    print("  %d gerçek sefer üzerinde %d pencere deneniyor  (kaynak: %s)\n"
          % (len(gercek), len(DENENEN_PENCERELER), kaynak))

    # ⭐⭐ AYARLAYICI HAVUZA TAŞINDI (4 Eylül) — B'nin A'dan kopması
    #
    # ⚠️ ASIL SEBEP HIZ DEĞİL, BAĞIMSIZLIK. Bu işlev ham `gecis` tablosuna
    #    bağlı kaldığı sürece `GECIS_SAKLAMA_GUN` düşürülemiyordu: 21 günlük
    #    pencereyi sınayabilmek için 21 günlük HAM veri tutmak gerekiyordu
    #    (kaydedici.py buda() içindeki 28 gün gerekçesi tam olarak buydu).
    #    Havuz gün numarasını zaten taşıyor — bu yüzden konmuştu (Bölüm 60).
    #    Artık ayarlayıcı havuzdan besleniyor; ham verinin ömrü ayarlayıcıyı
    #    kısıtlamıyor. İki karar birbirinden koptu:
    #        A · GECIS_SAKLAMA_GUN  ham veri kaç gün tutulur (diğer okuyucular)
    #        B · sure_pencere       model kaç günlük geçmişle kurulur (burası)
    #
    # ⚠️ KOVA SINIRI YANLILIĞI — ölçüldü, ihmal edilebilir (4 Eylül):
    #    Havuzda kova başına en fazla PH.KOVA_SINIRI (120) gözlem var; taşınca
    #    en eskiler atılıyor. Sınıra dayanan 4.023 kova (tümünün %0,19) ve
    #    yarısı yalnızca son 5 günü kapsıyor — o kovalarda uzun pencere kısa
    #    pencereyle aynı sonucu verir. Ama o kovalar ZATEN 120 gözlemle doymuş;
    #    uzun pencerenin katacağı bir şey yok. Farkı seyrek kovalar yaratıyor
    #    (havuzun %93'ü, 1–19 gözlem) ve orada sınır hiç devreye girmiyor.
    #
    # YAN FAYDA: eskiden her pencere için ham tablo yeniden taranıyordu
    #    (7 pencere × ~25 hat = ~175 tam tarama). Artık hat×yön başına BİR
    #    havuz okuması yapılıyor, pencereler bellekte süzülüyor.
    import parca_havuz as PH
    PH.tablo_kur(db)
    hedef_gt = PH.gun_tipi(g)
    hedef_gn = PH.gun_no(g)
    ikili = list(dict.fromkeys((h, y) for h, y, _, _, _, _ in gercek))

    havuz = {}          # (hat,yon) -> [(sira, saat, sure_dk, gun_no), ...]
    if kaynak == "havuz":
        for hat, yon in ikili:
            kayit = []
            for sira, saat, blob in db.execute(
                    "SELECT sira, saat, sureler FROM parca_havuz"
                    " WHERE hat=? AND yon=? AND gun_tipi=?", (hat, yon, hedef_gt)):
                for dk, gn in PH.coz(blob):
                    kayit.append((sira, saat, dk, gn))
            havuz[(hat, yon)] = kayit

    def model_havuz(pen):
        """Havuzdaki gözlemlerden `pen` günlük pencereyle parça modeli kurar."""
        alt = hedef_gn - pen
        model = {}
        for anahtar, kayit in havuz.items():
            kova, gen = {}, {}
            for sira, saat, dk, gn in kayit:
                # ⚠️ hedef gün modele GİRMEZ — sınav günü eğitime karışırsa
                #    ölçüm kendi kendini doğrular (veri sızıntısı).
                if gn < alt or gn >= hedef_gn:
                    continue
                kova.setdefault((sira, saat), []).append(dk)
                gen.setdefault(sira, []).append(dk)
            model[anahtar] = (
                {a: _st.median(v) for a, v in kova.items() if len(v) >= 3},
                {a: _st.median(v) for a, v in gen.items() if len(v) >= 3})
        return model

    def model_ham(pen):
        """ESKİ YOL — ham `gecis`ten kurar. Yalnızca doğrulama için duruyor;
        havuz yolu doğrulandıktan sonra silinecek (Bölüm 61 madde 2 deseni)."""
        bas = (g - timedelta(days=pen)).strftime("%Y-%m-%d %H:%M:%S")
        bit = g.strftime("%Y-%m-%d %H:%M:%S")
        model = {}
        for hat, yon in ikili:
            kova, gen = {}, {}
            onc = None
            for kap, z, sr in db.execute(
                    "SELECT kapino,zaman,sira FROM gecis WHERE hat=? AND yon=?"
                    " AND zaman >= ? AND zaman < ? ORDER BY kapino,zaman", (hat, yon, bas, bit)):
                an = datetime.strptime(z, "%Y-%m-%d %H:%M:%S")
                if onc and onc[0] == kap and sr - onc[2] == 1:
                    dk = (an - onc[1]).total_seconds() / 60
                    if 0 < dk <= MAX_PARCA_DK and gun_tipi(onc[1]) == gun_tipi(g):
                        kova.setdefault((onc[2], onc[1].hour), []).append(dk)
                        gen.setdefault(onc[2], []).append(dk)
                onc = (kap, an, sr)
            model[(hat, yon)] = (
                {a: _st.median(v) for a, v in kova.items() if len(v) >= 3},
                {a: _st.median(v) for a, v in gen.items() if len(v) >= 3})
        return model

    sonuclar = {}
    for pen in DENENEN_PENCERELER:
        model = model_havuz(pen) if kaynak == "havuz" else model_ham(pen)
        hatalar = []
        for hat, yon, sb, ss, t0, fi in gercek:
            saatli, gen = model.get((hat, yon), ({}, {}))
            t = 0.0; tamam = True
            for s in range(sb, ss):
                o = t0 + timedelta(minutes=t)
                v = saatli.get((s, o.hour)) or gen.get(s)
                if v is None:
                    tamam = False; break
                t += v
            if tamam:
                hatalar.append(abs(t - fi))
        if len(hatalar) >= 100:
            sonuclar[pen] = (_st.median(hatalar), len(hatalar))
            print("    %2d gün → ortanca hata %.2f dk (%d tahmin)" % (pen, sonuclar[pen][0], len(hatalar)))
    if not sonuclar:
        p = secili_pencere(db)
        db.close(); dz.close()
        return p
    en_iyi = min(sonuclar.items(), key=lambda kv: kv[1][0])[0]
    # ⚠️ Yalnızca gerçek yol (havuz) ayarı kaydeder. 'ham' bir doğrulama
    #    koşusudur; sonucu yazsaydı karşılaştırma canlı ayarı bozardı.
    if kaynak == "havuz":
        db.execute("INSERT OR REPLACE INTO durum (anahtar,deger) VALUES ('sure_pencere',?)", (str(en_iyi),))
        db.execute("INSERT OR REPLACE INTO durum (anahtar,deger) VALUES ('sure_pencere_tarih',?)", (hedef_gun,))
        db.commit()
    else:
        print("  (doğrulama koşusu — ayar KAYDEDİLMEDİ)")
    print("\n  ⭐ seçilen pencere: %d gün (ortanca hata %.2f dk)" % (en_iyi, sonuclar[en_iyi][0]))
    db.close(); dz.close()
    return en_iyi


# ─────────────────────────────────────────────────────────────────────────────
# TAHMİN
# ─────────────────────────────────────────────────────────────────────────────

_onbellek = {}


# ⚠️⚠️ İLK PARÇA KİRLİ — ölçüldü, düzeltiliyor (1 Eylül, 4. seans)
#
# `gecis` tablosunda 1→2 geçişi yalnızca sefere ÇIKAN araçları içermiyor: peronda
# bekleyen, tur arası dinlenen, oraya gelip duran araçların geçişleri de aynı
# kovaya düşüyor. Sonuç, ilk parçanın ölçülen süresinin peron beklemesiyle
# şişmesi:
#
#     parça 1→2 : ortanca 4,77 dk     ← komşularının 4 KATI
#     parça 2→3 : ortanca 1,15 dk
#     parça 3→4 : ortanca 1,07 dk
#     hatların %79'unda ilk parça, komşularının 2 katından uzun
#
# Bu fazlalık tahmine SABİT bir hata olarak biniyor ve rota boyunca hiç
# kaybolmuyor. Ölçüldü (31 Ağustos · 81.696 gerçek durak geçişi):
#
#     hata rota konumuna göre:  %0 → 5,6 dk   %50 → 5,8 dk   %90 → 6,2 dk
#     yani hata birikmiyor, BAŞTA doğuyor.
#
# Düzeltme p10'a doğru harmanlama. Ağırlık ölçülerek seçildi:
#
#     ağırlık   |hata|   ≤3dk   sapma
#      şu anki   5,9 dk   %27   +0,2
#      0,15      4,2      %42   −2,8
#      0,45      4,4      %38   −1,6   ← seçildi
#      0,60      4,7      %36   −1,1
#
# ⚠️ 0,45 seçildi çünkü yalnızca hatayı değil YÖNÜNÜ de gözetiyor: kalan −1,6 dk
#    sapma tahmini biraz ERKEN yapıyor. Yolcu için güvenli yön bu — otobüsü
#    kaçırmaktansa birkaç dakika fazla beklemek yeğdir.
#
# ⚠️ Asıl çözüm veri düzeyinde: `gecisler.py` peronda bekleyen aracı sefere
#    çıkmış saymamalı. O daha büyük bir iş; şimdilik model düzeyinde düzeltiliyor.
ILK_PARCA_AGIRLIK = 0.45


def _parcalar(db, hat, yon, gt):
    anahtar = (hat, yon, gt)
    if anahtar in _onbellek:
        return _onbellek[anahtar]
    saatli = {}
    ilk_p10 = {}
    for sira, saat, ort, p10 in db.execute(
            "SELECT sira, saat, ortanca, p10 FROM parca_sure"
            " WHERE hat=? AND yon=? AND gun_tipi=?", (hat, yon, gt)):
        saatli[(sira, saat)] = ort
        if sira == 1 and p10 is not None:
            ilk_p10[saat] = p10
    genel = dict(db.execute(
        "SELECT sira, ortanca FROM parca_sure_genel WHERE hat=? AND yon=? AND gun_tipi=?",
        (hat, yon, gt)))

    # ── ilk parçayı peron beklemesinden arındır ──
    w = ILK_PARCA_AGIRLIK
    for saat, p10 in ilk_p10.items():
        ort = saatli.get((1, saat))
        if ort is not None and ort > p10:
            saatli[(1, saat)] = p10 + w * (ort - p10)
    if 1 in genel:
        # p10 yoksa: 2. parçanın süresi alt sınır olarak kullanılıyor
        alt = genel.get(2, genel[1])
        if genel[1] > alt:
            genel[1] = alt + w * (genel[1] - alt)

    _onbellek[anahtar] = (saatli, genel)
    return saatli, genel


def varis_suresi(db, hat, yon, sira_bas, sira_son, kalkis_ani):
    """sira_bas durağından sira_son durağına tahmini süre (dakika).

    ⭐ Saat ilerletilerek toplanır: otobüs yolda ilerledikçe içinde bulunduğu saat
    değişir, o saatin parça süreleri kullanılır. 23:00'te kalkan bir otobüsün
    40. dakikasında yaşadığı trafik 23:40'ın trafiğidir.

    Döner: (dakika, kaç_parça_saatli_veriden, kaç_parça_yedekten) · yoksa None
    """
    if sira_son <= sira_bas:
        return None
    gt = gun_tipi(kalkis_ani)
    saatli, genel = _parcalar(db, hat, yon, gt)
    if not genel:
        return None

    toplam = 0.0
    saatli_n = yedek_n = 0
    for s in range(sira_bas, sira_son):
        o_an = kalkis_ani + timedelta(minutes=toplam)
        v = saatli.get((s, o_an.hour))
        if v is not None:
            saatli_n += 1
        else:
            v = genel.get(s)
            if v is None:
                return None                 # bu parça hiç gözlenmemiş
            yedek_n += 1
        toplam += v
    return toplam, saatli_n, yedek_n


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kur":
        kur(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif len(sys.argv) > 2 and sys.argv[1] == "ayarla":
        pencere_ayarla(sys.argv[2], kaynak=(sys.argv[3] if len(sys.argv) > 3 else "havuz"))
    else:
        print(__doc__)

"""
GEÇİŞLER — araçların duraklardan GERÇEKTE kaçta geçtiğini konum izinden çıkarır.

NEDEN VAR — projenin en önemli kararlarından biri:
  Tarife, bir durakta ne olduğunu güvenilir biçimde anlatmıyor. Ölçüldü
  (Otobüs Takip Uygulaması PROJE DURUMU Bölüm 21): 98 hattının hafta içi tarifesi Sefaköy'de D yönünde
  06:40 ile 23:00 arası SIFIR kalkış gösteriyor; gerçekte **23 dakikada bir**
  otobüs geçiyor. Sebep, gündüz seferlerinin gidiş+dönüşü tek kayıt sayan bir
  varyanta (98_G_D7742) yazılması — dönüş bacağı tarifede görünmüyor.

  Formülle türetmek denendi, tutmadı: tur süresi 160-244 dk arasında oynuyor.
  Bu yüzden geçişleri TAHMİN ETMİYORUZ, ÖLÇÜYORUZ.

NASIL ÇALIŞIR:
  Her aracın konum izi rotaya izdüşürülür. İz, durağın rota üzerindeki mesafesini
  geçtiği anda geçiş kaydedilir; tam an iki ölçüm arasında ara değerle bulunur.

  ⚠️ Yön, `guzergahkodu` etiketinden DEĞİL gerçek hareketten belirlenir
  (yon_tespit.py) — etiket 98'de araçların yarısında yanlıştı.

ÇALIŞTIRMA:
    python3 gecisler.py            # yeni konum kayıtlarını işler
    python3 gecisler.py --hepsi    # baştan hesaplar

ÇIKTI: veri/kayit.db → gecis tablosu
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rota
import yon_tespit

VERI = Path(__file__).parent / "veri"
MAX_SAPMA_M = 250          # rotadan bu kadar uzak ölçüm izi koparır
MAX_ATLAMA_M = 6000        # iki ölçüm arası bu kadar atladıysa arada boşluk var,
                           # geçiş anı güvenilir hesaplanamaz
MIN_IZ = 3

# ⚠️ ARTIMLI ÇALIŞMADA BULUNAN HATA (1 Eylül):
#   İşlenecek pencere kısa olduğunda (örn. 76 dakika) araç→hat eşlemesi de yalnızca
#   o pencerede aranıyordu. Bir hattın araçlarının çoğu daha önce eşlenmiş olduğu
#   için hiç taranmıyor, geçiş sayısı dörtte bire düşüyordu (188 bin → 50 bin).
#   Konumlar yeni pencereden alınır ama EŞLEME daha geriye bakar.
ESLEME_GERIYE_SAAT = 4

# ⚠️⚠️ İZ PENCERESİ GERİYE TAŞINIYOR (7 Eylül) — çıkarım veriminin kökü
#
#   1 Eylül'de bu betik "günde bir tam tarama"dan "10 dakikada bir artımlı"ya
#   geçti (Bölüm 40). Eşleme 4 saat geriye taşındı ama İZ taşınmadı; iz hâlâ
#   yalnızca yeni pencereden okunuyordu. İki kayıp doğdu:
#
#   1. MIN_IZ ELEMESİ — 10 dakikalık pencerede araç başına ortalama 3,6 konum
#      kaydı düşüyor, eşik ise 3. ÖLÇÜLDÜ (4 Eylül): pencerelerin %36'sı
#      MIN_IZ'e takılıp TAMAMEN eleniyordu (591 pencerede tek kayıt vardı).
#      Tam gün taramasında aracın izi tek parça olduğu için bu eşik hiç
#      devreye girmiyordu.
#
#   2. PENCERE SINIRI — her pencerenin ilk adımı, bir öncekinin SON ölçümüne
#      ihtiyaç duyar ama `zaman > baslangic` onu dışarıda bırakıyordu.
#      Günde 144 pencere = araç başına 144 kayıp adım.
#
#   ÖLÇÜLEN ETKİ: verim (gecis/filo_konum) 0,80'den 0,50'ye düştü — yani ham
#   veri diskte duruyor ama çıkarım onu göremiyor. Bölüm 40'ın kendi ölçümü de
#   bunu söylüyordu: tam tarama 188.170 geçiş, artımlı 49.842 (dörtte biri).
#
#   ÇÖZÜM: `parca_havuz.py` aynı sorunu zaten böyle çözüyor — okuma penceresini
#   geriye taşıyor. Mükerrer kayıt riski yok: `INSERT OR IGNORE` ve
#   `UNIQUE (hat, yon, durak_kodu, kapino, zaman)` üst üste binen pencereleri
#   sessizce yutuyor.
IZ_GERIYE_DK = 30          # iz bu kadar geriye taşınır (pencerenin 3 katı)


def tablo_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS gecis (
            zaman       TEXT NOT NULL,     -- durağın önünden geçtiği an
            hat         TEXT NOT NULL,
            yon         TEXT NOT NULL,
            durak_kodu  TEXT NOT NULL,
            sira        INTEGER,
            kapino      TEXT NOT NULL,
            kesin       INTEGER,           -- 1: iki ölçüm yakın · 0: boşluktan tahmin
            UNIQUE (hat, yon, durak_kodu, kapino, zaman)
        );
        -- ⚠️ ix_gecis_durak (durak_kodu, zaman) KALDIRILDI (3 Eylül): kodda
        --    durak_kodu'nu TEK BAŞINA süzen hiçbir sorgu yok — durakta_ne_var,
        --    hayalet ve sure_modeli hepsi hat+yon ile birlikte soruyor, onları
        --    ix_gecis_durak_hat karşılıyor. Ölü ağırlıktı: 0,59 GB.
        CREATE INDEX IF NOT EXISTS ix_gecis_hat   ON gecis (hat, yon, zaman);
        CREATE TABLE IF NOT EXISTS durum (anahtar TEXT PRIMARY KEY, deger TEXT);
    """)
    db.commit()


def hat_duraklari(dizin, hat, yon):
    """Hattın duraklarını rota üzerindeki mesafeleriyle döndürür."""
    try:
        mesafeler = rota.durak_mesafeleri(hat, yon)
    except (KeyError, IndexError):
        return []
    kodlar = dizin.execute(
        "SELECT sira, durak_kodu FROM hat_durak WHERE hat_kodu=? AND yon=? ORDER BY sira",
        (hat, yon)).fetchall()
    esle = dict(kodlar)
    return [(sira, esle[sira], m) for sira, _, m, _ in mesafeler if sira in esle]


def arac_gecisleri(hat, kapino, iz, duraklar):
    """Aracın izinden geçtiği durakları ve geçiş anlarını çıkarır.

    ⚠️ İKİ DENEME ÖNCE ÇÖZÜLDÜ, kayda değer:
      1) Tüm iz için TEK yön belirlenmişti → araç gün boyu gidip geldiği için
         31 geçişin 11'i bulundu.
      2) İz "bacaklara" bölünüp gruplanmıştı → gruplama sınırlarında adım kaybı
         ve yön yanlılığı oluştu, 8'e düştü.
      3) Çalışan yöntem: GRUPLAMA YOK. Her ölçüm çifti bağımsız değerlendirilir;
         adım, iki rotadan ilerlemesi DAHA BÜYÜK olanına atanır.

    Neden işe yarıyor: G ve D rotaları birbirinin tersi. Araç D'de ilerliyorsa
    G izdüşümü geriler. Yani adım başına karar zaten belirgin; ayrıca gruplamaya
    ve durum tutmaya gerek yok.
    """
    olcumler = []
    for zaman, enlem, boylam, _ in iz:
        an = datetime.strptime(zaman, "%Y-%m-%d %H:%M:%S")
        nokta = {}
        for yon in duraklar:
            try:
                nokta[yon] = rota.yol_uzerinde(hat, yon, boylam, enlem)
            except (KeyError, IndexError):
                nokta[yon] = None
        olcumler.append((an, nokta))

    sonuc = []
    for i in range(1, len(olcumler)):
        (t0, n0), (t1, n1) = olcumler[i - 1], olcumler[i]
        if (t1 - t0).total_seconds() > 900:
            continue                        # 15 dk'dan uzun boşluk — geçiş anı uydurma olur

        adimlar = {}
        for yon in duraklar:
            a, b = n0.get(yon), n1.get(yon)
            if not a or not b or max(a[1], b[1]) > MAX_SAPMA_M:
                continue
            if b[0] > a[0]:                 # bu rotada İLERİ gitmiş
                adimlar[yon] = (a[0], b[0])
        if not adimlar:
            continue
        # adımı, ilerlemesi daha büyük olan rotaya ata
        yon = max(adimlar.items(), key=lambda kv: kv[1][1] - kv[1][0])[0]
        m0, m1 = adimlar[yon]
        atlama = m1 - m0

        for sira, kod, mesafe in duraklar[yon]:
            if m0 < mesafe <= m1:
                an = t0 + (t1 - t0) * ((mesafe - m0) / atlama)
                sonuc.append((an.strftime("%Y-%m-%d %H:%M:%S"), hat, yon, kod,
                              sira, kapino, 1 if atlama <= MAX_ATLAMA_M else 0))
    return sonuc


def isle(hepsi=False):
    db = sqlite3.connect(str(VERI / "kayit.db"), timeout=60)
    # ⚠️ Kaydedici aynı veritabanına saniye saniye yazıyor. Uzun yazma işlemleri
    #    28 Ağustos'ta onu kilitleyip ÇÖKERTTİ (18 dk veri kaybı). İki koruma:
    #    busy_timeout → kilitte hata vermek yerine bekle
    #    sık commit   → kilidi uzun tutma (aşağıda, her hatta bir)
    db.execute("PRAGMA busy_timeout=60000")
    tablo_kur(db)
    dizin = sqlite3.connect(str(VERI / "dizin.db"))

    baslangic = "2000-01-01" if hepsi else (
        db.execute("SELECT deger FROM durum WHERE anahtar='gecis_son'").fetchone()
        or ["2000-01-01"])[0]
    bitis = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("işlenecek aralık: %s → %s\n" % (baslangic, bitis))

    # Bu aralıkta hangi hatlarda araç görülmüş?
    esleme_bas = (datetime.strptime(baslangic, "%Y-%m-%d %H:%M:%S")
                  - timedelta(hours=ESLEME_GERIYE_SAAT)).strftime("%Y-%m-%d %H:%M:%S") \
        if baslangic > "2001" else baslangic
    # İz okuma sınırı — eşleme gibi geriye taşınıyor (gerekçe IZ_GERIYE_DK'da).
    iz_bas = (datetime.strptime(baslangic, "%Y-%m-%d %H:%M:%S")
              - timedelta(minutes=IZ_GERIYE_DK)).strftime("%Y-%m-%d %H:%M:%S") \
        if baslangic > "2001" else baslangic

    hatlar = [r[0] for r in db.execute(
        "SELECT DISTINCT hat FROM arac_hat WHERE zaman > ? AND zaman <= ?"
        " UNION SELECT DISTINCT hat FROM konum WHERE damga > ? AND damga <= ?",
        (esleme_bas, bitis, esleme_bas, bitis))]
    print("%d hatta araç görülmüş\n" % len(hatlar))

    toplam = 0
    for i, hat in enumerate(hatlar, 1):
        duraklar = {y: hat_duraklari(dizin, hat, y) for y in ("G", "D")}
        if not any(duraklar.values()):
            continue
        araclar = {r[0] for r in db.execute(
            "SELECT DISTINCT kapino FROM arac_hat WHERE hat=? AND zaman > ? AND zaman <= ?"
            " UNION SELECT DISTINCT kapino FROM konum WHERE hat=? AND damga > ? AND damga <= ?",
            (hat, esleme_bas, bitis, hat, esleme_bas, bitis))}
        for kapino in araclar:
            iz = db.execute(
                "SELECT zaman, enlem, boylam FROM konum_birlesik"
                " WHERE kapino=? AND zaman > ? AND zaman <= ? AND enlem IS NOT NULL"
                " ORDER BY zaman", (kapino, iz_bas, bitis)).fetchall()
            if len(iz) < MIN_IZ:
                continue
            iz = [(z, e, b, None) for z, e, b in iz]
            satirlar = arac_gecisleri(hat, kapino, iz, duraklar)
            if satirlar:
                db.executemany(
                    "INSERT OR IGNORE INTO gecis (zaman, hat, yon, durak_kodu, sira,"
                    " kapino, kesin) VALUES (?,?,?,?,?,?,?)", satirlar)
                toplam += len(satirlar)
        db.commit()          # her hatta bir: kilit kısa tutulsun
        if i % 25 == 0:
            print("  %d/%d hat · %d geçiş" % (i, len(hatlar), toplam))

    db.execute("INSERT OR REPLACE INTO durum (anahtar, deger) VALUES ('gecis_son', ?)", (bitis,))
    db.commit()
    print("\n" + "=" * 56)
    print("  bu turda çıkarılan geçiş: %d" % toplam)
    print("  tabloda toplam          : %d"
          % db.execute("SELECT COUNT(*) FROM gecis").fetchone()[0])
    print("  kapsanan durak          : %d"
          % db.execute("SELECT COUNT(DISTINCT durak_kodu) FROM gecis").fetchone()[0])
    print("=" * 56)
    dizin.close(); db.close()


if __name__ == "__main__":
    isle("--hepsi" in sys.argv)

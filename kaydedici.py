"""
KAYDEDİCİ v2 — ŞEHİR GENELİ. Tüm İstanbul filosunu dakikada bir kaydeder.

NEDEN DEĞİŞTİ (v1 hat bazlıydı, 2 hat izliyordu):
  Kota ölçüldü: SAATTE 100 İSTEK, tam saatte sıfırlanıyor (Otobüs Takip Uygulaması PROJE DURUMU Bölüm 17).
  Hat bazlı sorgu hat başına dakikada 1 istek ister → 2 hat = saatte 120 → kota aşılıyor,
  her saatin son 8 dakikası kör kalıyordu. 26/27 Ağustos gecesi bunun bedeli ödendi:
  23:30 otobüsü Sefaköy'den 23:52'de geçti, kör pencere 23:52-00:01'di.

  GetFiloAracKonum_json parametresiz çağrılınca TEK İSTEKTE 6.911 aracın hepsini
  veriyor (konum + HIZ + kapı no + plaka). Dakikada 1 istek = saatte 60.
  Yani 2 hat yerine TÜM ŞEHİR, üstelik kotanın yarısıyla.

  ⚠️ Bedeli: bu serviste HAT KODU YOK. Araç→hat eşlemesi ayrıca kurulmalı.
  Kalan kotayla (saatte ~30 istek) hatlar sırayla sorgulanıp eşleme tazeleniyor.

ÜÇ TABLO:
  filo_konum  şehir geneli konumlar (yalnızca HAREKETLİ araçlar — garajdakiler elenir)
  arac_hat    hangi araç hangi hatta — dönüşümlü hat sorgularından, ZAMAN DAMGALI
              (araçlar hat değiştiriyor: 14 günde araçların %90'ı birden fazla hatta)
  yoklama     yapılan her sorgunun kendisi — "baktık ve boştu" ile "bakmadık" farkı

ÇALIŞTIRMA:
    caffeinate -i python3 kaydedici.py
  Ctrl+C ile durur, kaldığı yerden devam eder.
"""

import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hat_tahmini

# ─────────────────────────────────────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────────────────────────────────────

SAATLIK_BUTCE = 95            # ölçülen kota 100; 5 istek elle sorgulara pay
HAT_SORGUSU_YEDEGI = 12       # bütçede bu kadar kalınca hat sorgularını kes,
                              # şehir görüntüsünü koru (o daha değerli)
PERIYOT_SN = 60
SANIYE_HIZASI = 8
HAT_SORGU_ARALIGI_TUR = 2     # kaç turda bir hat sorgusu (2 → saatte ~30 istek)

ONCELIKLI_HATLAR = ["98", "98AB", "98S", "500T"]   # her 5. hat sorgusunda biri
ONCELIK_SIKLIGI = 5

HAREKET_ESIGI_M = 30          # bu kadar kıpırdamayan araç her turda yazılmaz
DURAN_ARAC_NABZI_DK = 10      # ama duran araç da bu aralıkla bir kez yazılır — nedeni aşağıda
SAKLAMA_GUN = 10              # bundan eski filo_konum kayıtları budanır
GECIS_SAKLAMA_GUN = 14        # ham geçişler — gerekçesi buda()'da (7 Eylül: 28→14)

# ⚠️ DİSK GÖZCÜSÜ (3 Eylül) — disk dolunca kaydedici sessizce ölmüştü, 7 sa kayıp.
UYARI_GB = 5.0                # bu eşiğin altında günlüğe uyarı yazılır
ACIL_GB  = 3.0                # bu eşiğin altında ACİL BUDAMA yapılır
DISK_KONTROL_TUR = 10         # kaç turda bir bakılır (10 tur = 10 dakika)

# ⭐ GEOMETRİK HAT TAHMİNİ — 3. seansta eklendi.
#   Servisten hat kimliği günde ancak bir tur geliyordu (hat×saat kapsaması %2,2)
#   ve bu, geniş doğrulamada 1.487 yanlış alarma yol açtı. Aracın izini rota
#   geometrisiyle eşleştirmek kotaya hiç dokunmuyor ve %93,7 isabetli.
#   Her tur, tahmini en eski olan araçlardan bir dilim işleniyor (~17 ms/araç).
TAHMIN_PER_TUR = 220
TAHMIN_TAZELEME_DK = 10       # bir aracın tahmini bu aralıkla yenilenir

VERITABANI = Path(__file__).parent / "veri" / "kayit.db"
BASE, NS = "https://api.ibb.gov.tr/iett/", "http://tempuri.org/"
BEKLEME_MERDIVENI = [180, 300, 600, 900, 1800]


# ─────────────────────────────────────────────────────────────────────────────
# SERVİS
# ─────────────────────────────────────────────────────────────────────────────

def soap(yol, metot, parametreler):
    govde = "".join("<%s>%s</%s>" % (k, v, k) for k, v in parametreler.items())
    zarf = ('<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Body><%s xmlns="%s">%s</%s></soap:Body></soap:Envelope>'
            % (metot, NS, govde, metot))
    istek = urllib.request.Request(
        BASE + yol, data=zarf.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": NS + metot})
    with urllib.request.urlopen(istek, timeout=45) as cevap:
        kok = ET.fromstring(cevap.read())
    sonuc = next((e for e in kok.iter() if e.tag.endswith("Result")), None)
    return json.loads(sonuc.text) if (sonuc is not None and sonuc.text) else []


def sayi(deger):
    try:
        return float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# KOTA SAYACI
# ─────────────────────────────────────────────────────────────────────────────

class Butce:
    """Saatlik istek bütçesi. Kota TAM SAATTE sıfırlandığı için sayaç da öyle.

    ⚠️ Sayaç bellekte DEĞİL, `yoklama` tablosundan okunuyor. Sebep: betik saat
    ortasında yeniden başlatılırsa bellekteki sayaç sıfırlanır, o saat içinde
    zaten harcanmış istekler unutulur ve kota aşılır. Tablo ise ne yapıldığını
    hatırlıyor — hangi süreç yapmış olursa olsun.
    """

    def __init__(self, sinir, db):
        self.sinir = sinir
        self.db = db
        self.saat = None
        self.harcanan = 0

    def _tazele(self):
        simdi = datetime.now().strftime("%Y-%m-%d %H")
        if simdi != self.saat:
            self.saat = simdi
            r = self.db.execute("SELECT COUNT(*) FROM yoklama WHERE substr(zaman,1,13)=?",
                                (simdi,)).fetchone()
            self.harcanan = r[0] if r else 0

    def kalan(self):
        self._tazele()
        return self.sinir - self.harcanan

    def harca(self, adet=1):
        self._tazele()
        self.harcanan += adet


# ─────────────────────────────────────────────────────────────────────────────
# VERİTABANI
# ─────────────────────────────────────────────────────────────────────────────

def veritabani_kur():
    VERITABANI.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(VERITABANI), timeout=90)
    # ⚠️ 28 Ağustos: gecisler.py uzun yazma yaparken kaydedici "database is locked"
    #    alıp ÇÖKTÜ ve 18 dakika veri kaybedildi. İki koruma:
    #    WAL   → okuyucular yazarı beklemez, kilit çekişmesi çok azalır
    #    busy_timeout → kilit varsa hata vermek yerine bekler
    db.execute("PRAGMA busy_timeout=90000")
    # ⚠️⚠️ WAL SINIRI (3 Eylül): `kayit.db-wal` 4,4 GB'a şişip diski doldurdu.
    #    Sürekli okuyucu (döngüler, sunucu) olduğu için otomatik checkpoint
    #    tamamlanamıyor, WAL sınırsız büyüyor.
    #    ⚠️ `journal_size_limit` BAĞLANTI BAŞINA ayarlanır, dosyada SAKLANMAZ —
    #       2 Eylül'de elle ayarlanmıştı, o bağlantı kapanınca ayar da gitti.
    #       Bu yüzden yazar bağlantının kurulduğu yere konuldu.
    #    autocheckpoint da sıklaştırıldı: 1000 → 400 sayfa (~1,6 MB).
    db.execute("PRAGMA journal_size_limit=268435456")   # 256 MB üstünü kırp
    db.execute("PRAGMA wal_autocheckpoint=400")
    try:
        db.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # WAL'a geçiş kısa bir dışlayıcı kilit ister; başka bir iş yazıyorsa
        # olmuyor. Zorunlu değil — busy_timeout tek başına da çökmeyi önlüyor.
        # Bir sonraki başlatmada denenecek.
        pass
    db.executescript("""
        CREATE TABLE IF NOT EXISTS filo_konum (
            zaman   TEXT NOT NULL,     -- servisin verdiği an (tarih + Saat)
            kapino  TEXT NOT NULL,
            enlem   REAL, boylam REAL,
            hiz     REAL,              -- aracın kendi bildirdiği hız (km/sa)
            UNIQUE (kapino, zaman)
        );
        CREATE INDEX IF NOT EXISTS ix_filo_zaman ON filo_konum (zaman);
        -- ⚠️ ix_filo_arac (kapino, zaman) KALDIRILDI (3 Eylül): yukarıdaki
        --    UNIQUE (kapino, zaman) kısıtı SQLite'ta zaten aynı indeksi
        --    kuruyor (sqlite_autoindex_filo_konum_1). Tam kopyaydı: 0,78 GB.
        --    Sorgu planları doğrulandı, araç izi sorgusu autoindex'i kullanıyor.

        CREATE TABLE IF NOT EXISTS arac_hat (
            zaman        TEXT NOT NULL,
            kapino       TEXT NOT NULL,
            hat          TEXT NOT NULL,
            guzergahkodu TEXT,
            UNIQUE (kapino, zaman)
        );
        CREATE INDEX IF NOT EXISTS ix_arachat_arac ON arac_hat (kapino, zaman);
        CREATE INDEX IF NOT EXISTS ix_arachat_hat  ON arac_hat (hat, zaman);

        CREATE TABLE IF NOT EXISTS yoklama (
            id INTEGER PRIMARY KEY, zaman TEXT, hat TEXT, sonuc TEXT,
            arac_sayisi INTEGER, yeni_kayit INTEGER, aciklama TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_yoklama_zaman ON yoklama (zaman);

        CREATE TABLE IF NOT EXISTS durum (anahtar TEXT PRIMARY KEY, deger TEXT);
    """)
    # kaynak sütunu: 'servis' (hat sorgusu, gerçek) | 'geometri' (rota eşleştirme, %94)
    if "kaynak" not in [r[1] for r in db.execute("PRAGMA table_info(arac_hat)")]:
        db.execute("ALTER TABLE arac_hat ADD COLUMN kaynak TEXT")
        db.execute("UPDATE arac_hat SET kaynak='servis' WHERE kaynak IS NULL")
    db.commit()
    return db


def durum_oku(db, anahtar, varsayilan=None):
    r = db.execute("SELECT deger FROM durum WHERE anahtar=?", (anahtar,)).fetchone()
    return r[0] if r else varsayilan


def durum_yaz(db, anahtar, deger):
    db.execute("INSERT OR REPLACE INTO durum (anahtar, deger) VALUES (?,?)",
               (anahtar, str(deger)))


# ─────────────────────────────────────────────────────────────────────────────
# ŞEHİR GENELİ ANLIK GÖRÜNTÜ
# ─────────────────────────────────────────────────────────────────────────────

_son_konum = {}          # kapino -> (enlem, boylam) · hareket süzgeci için
_son_yazim = {}          # kapino -> datetime  · duran araç nabzı için
_son_tahmin = {}         # kapino -> datetime  · geometrik hat tahmini için


SAAT_SAPMA_SINIRI_SN = 1800      # bundan uzak damga = aracın saati bozuk, kayda alınmaz


def _zaman_damgasi(saat_metni, simdi):
    """Servis yalnızca 'HH:MM:SS' veriyor; TARİHİ BİZ EKLİYORUZ.

    ⚠️ İki tuzak var, ikisi de ölçülerek bulundu:

    1) GECE YARISI DÖNÜŞÜ. Saat 00:01'de "23:59" bildiren araç dünden kalmadır.
       Gün kaydırması yalnızca 12 SAATTEN fazla sapma varsa yapılır — daha gevşek
       bir eşik (ilk sürümde 5 dakikaydı) saati ileri kaçık araçları bir gün
       geriye itiyordu ve 507 uydurma "dünkü" kayıt üretmişti.

    2) SAATİ BOZUK ARAÇLAR. 10:00'da "23:55" bildiren araçlar var. Bunlar gerçek
       gözlem değil; zaman serisini kirletmemeleri için tamamen reddediliyor.
    """
    if not saat_metni:
        return None
    try:
        s, d, sn = (int(x) for x in saat_metni.split(":"))
    except ValueError:
        return None
    try:
        damga = simdi.replace(hour=s, minute=d, second=sn, microsecond=0)
    except ValueError:
        return None
    if damga - simdi > timedelta(hours=12):
        damga -= timedelta(days=1)          # gece yarısını yeni geçtik
    elif simdi - damga > timedelta(hours=12):
        damga += timedelta(days=1)          # araç gece yarısını bizden önce gördü
    if abs((damga - simdi).total_seconds()) > SAAT_SAPMA_SINIRI_SN:
        return None                         # saati bozuk araç
    return damga.strftime("%Y-%m-%d %H:%M:%S")


def _uzaklik_m(a, b):
    """Kaba metre farkı — yalnızca 'kıpırdadı mı' sorusu için, hassasiyet gerekmiyor."""
    return (((a[0] - b[0]) * 111000) ** 2 + ((a[1] - b[1]) * 83000) ** 2) ** 0.5


def sehir_goruntusu(db, simdi):
    """Tüm filoyu tek istekte çeker, HAREKETLİ olanları yazar.

    Neden hareketsizler elenmiyor da yazılmıyor: 6.911 aracın ~4.300'ü garajda
    duruyor ve dakikada bir aynı koordinatı bildiriyor. Hepsini saklamak günde
    ~800 MB üretirdi ve hiçbir sorusuna cevap vermezdi."""
    filo = soap("FiloDurum/SeferGerceklesme.asmx", "GetFiloAracKonum_json", {})
    satirlar = []
    for a in filo:
        kapino = a.get("KapiNo")
        enlem, boylam = sayi(a.get("Enlem")), sayi(a.get("Boylam"))
        if not kapino or enlem is None or boylam is None:
            continue
        onceki = _son_konum.get(kapino)
        kipirdadi = (onceki is None
                     or _uzaklik_m(onceki, (enlem, boylam)) >= HAREKET_ESIGI_M)
        # ⭐ DURAN ARAÇ NABZI — neden gerekli:
        #   Hareketsizleri tamamen elesek "peronda bekleyen araç" ile "GPS'i sönmüş
        #   araç" ayırt edilemez hâle gelir; ikisi de "yeni satır yok" görünür.
        #   Oysa uygulamanın bütün mesele bu ayrım. O yüzden duran araç da
        #   DURAN_ARAC_NABZI_DK aralığıyla bir kez yazılır: yerinde durduğu ama
        #   HÂLÂ BİLDİRDİĞİ kayda geçsin.
        son_yazim = _son_yazim.get(kapino)
        nabiz_zamani = (son_yazim is None or
                        (simdi - son_yazim).total_seconds() >= DURAN_ARAC_NABZI_DK * 60)
        if not kipirdadi and not nabiz_zamani:
            continue
        if kipirdadi:
            _son_konum[kapino] = (enlem, boylam)
        _son_yazim[kapino] = simdi
        damga = _zaman_damgasi(a.get("Saat"), simdi)
        if damga:
            satirlar.append((damga, kapino, enlem, boylam, sayi(a.get("Hiz"))))

    once = db.total_changes
    db.executemany("INSERT OR IGNORE INTO filo_konum (zaman, kapino, enlem, boylam, hiz)"
                   " VALUES (?,?,?,?,?)", satirlar)
    return len(filo), len(satirlar), db.total_changes - once, [r[1] for r in satirlar]


# ─────────────────────────────────────────────────────────────────────────────
# ARAÇ → HAT EŞLEMESİ (dönüşümlü hat sorgusu)
# ─────────────────────────────────────────────────────────────────────────────

def hat_sirasi(db):
    """Sorgulanacak hatların sırası. Öncelikli hatlar araya serpiştirilir."""
    tumu = durum_oku(db, "hat_listesi")
    if not tumu:
        dizin = VERITABANI.parent / "dizin.db"
        if dizin.exists():
            d = sqlite3.connect(str(dizin))
            hatlar = [r[0] for r in d.execute(
                "SELECT hat_kodu FROM hat WHERE durum='ok' ORDER BY hat_kodu")]
            d.close()
        else:
            hatlar = list(ONCELIKLI_HATLAR)
        tumu = ",".join(hatlar)
        durum_yaz(db, "hat_listesi", tumu)
    return tumu.split(",")


def sonraki_hat(db, sayac):
    """Her ONCELIK_SIKLIGI sorgudan biri öncelikli hatlara ayrılır."""
    if sayac % ONCELIK_SIKLIGI == 0:
        return ONCELIKLI_HATLAR[(sayac // ONCELIK_SIKLIGI) % len(ONCELIKLI_HATLAR)]
    hatlar = hat_sirasi(db)
    imlec = int(durum_oku(db, "hat_imleci", "0"))
    hat = hatlar[imlec % len(hatlar)]
    durum_yaz(db, "hat_imleci", imlec + 1)
    return hat


def hat_eslemesi(db, hat, simdi):
    """Bir hattı sorup o anda üzerinde çalışan araçları kaydeder."""
    araclar = soap("FiloDurum/SeferGerceklesme.asmx", "GetHatOtoKonum_json", {"HatKodu": hat})
    z = simdi.strftime("%Y-%m-%d %H:%M:%S")
    satirlar = [(z, a["kapino"], hat, a.get("guzergahkodu"), "servis")
                for a in araclar if a.get("kapino")]
    db.executemany("INSERT OR IGNORE INTO arac_hat (zaman, kapino, hat, guzergahkodu,"
                   " kaynak) VALUES (?,?,?,?,?)", satirlar)
    return len(araclar)



# ─────────────────────────────────────────────────────────────────────────────
# GEOMETRİK HAT TAHMİNİ
# ─────────────────────────────────────────────────────────────────────────────

def hat_tahminleri(db, simdi, hareketli_kapilar):
    """Hareketli araçların bir dilimi için hattı GEOMETRİDEN çıkarır.

    Servisten gelen eşleme (kaynak='servis') gerçeğin kendisi ama günde bir tur
    geliyor. Bu, aynı boşluğu kotaya dokunmadan dolduruyor (kaynak='geometri').
    ⚠️ %6,3 yanlış atama payı var; bu yüzden kaynak ayrı işaretleniyor ve
    emin olunmayan durumda hiç yazılmıyor.
    """
    aday = [k for k in hareketli_kapilar
            if (k not in _son_tahmin
                or (simdi - _son_tahmin[k]).total_seconds() >= TAHMIN_TAZELEME_DK * 60)]
    aday.sort(key=lambda k: _son_tahmin.get(k, datetime.min))
    aday = aday[:TAHMIN_PER_TUR]
    if not aday:
        return 0

    z = simdi.strftime("%Y-%m-%d %H:%M:%S")
    satirlar = []
    for kapino in aday:
        _son_tahmin[kapino] = simdi
        try:
            iz = hat_tahmini.arac_izi(db, kapino, simdi)
            t = hat_tahmini.tahmin_et(iz)
        except Exception:
            continue
        if t:
            satirlar.append((z, kapino, t[0], "%s_%s_?" % (t[0], t[1]), "geometri"))
    if satirlar:
        db.executemany("INSERT OR IGNORE INTO arac_hat (zaman, kapino, hat,"
                       " guzergahkodu, kaynak) VALUES (?,?,?,?,?)", satirlar)
    return len(satirlar)


# ─────────────────────────────────────────────────────────────────────────────
# BUDAMA
# ─────────────────────────────────────────────────────────────────────────────

def disk_bos_gb():
    """Veritabanının bulunduğu diskte kaç GB boş var."""
    import shutil
    return shutil.disk_usage(str(VERITABANI.parent)).free / 1e9


def disk_gozcusu(db, son_acil):
    """⚠️⚠️ 3 EYLÜL SABAHI: disk 03:11'de doldu, kaydedici `database or disk is
    full` alıp 03:15'te ÖLDÜ. Yedi saat veri kaybedildi. Günlüğe hata yazdı ama
    kimse bakmadığı için sabaha kadar öyle kaldı.

    launchd artık ölen süreci geri getiriyor (Bölüm 57) — AMA DİSK DOLUYSA geri
    gelen süreç de yazamaz, aynı hatayla yine ölür. Yani asıl koruma burada:
    sistemin kendini kurtarması gerekiyor.

    İki kademe:
        < UYARI_GB   günlüğe belirgin uyarı — insan görürse müdahale etsin
        < ACIL_GB    ACİL BUDAMA: saklama süreleri geçici olarak yarıya iner,
                     en eski veri silinip yer açılır.

    ⭐ Acil budama bilinçli bir takas: eski veriyi kaybediyoruz ama SİSTEM YAŞIYOR.
       Alternatifi tüm akışın durması — bu sabah öyle oldu ve 7 saat kaybettik.
       Eski konum verisi zaten türetilmiş (gecis çıkarıldı); akan veri daha değerli.

    ⚠️ Acil budama günde en fazla BİR KEZ — disk hâlâ doluysa her turda silmeye
       çalışıp elimizdeki veriyi eritmesin.

    Döner: yeni `son_acil` tarihi.
    """
    bos = disk_bos_gb()
    if bos >= UYARI_GB:
        return son_acil

    bugun = datetime.now().date()
    if bos >= ACIL_GB or son_acil == bugun:
        print("   ⚠️  DİSK AZALIYOR: %.1f GB boş (uyarı eşiği %.0f GB)" % (bos, UYARI_GB))
        return son_acil

    print("   ⛔ DİSK KRİTİK: %.1f GB — ACİL BUDAMA" % bos)
    try:
        for tablo, gun in (("filo_konum", max(2, SAKLAMA_GUN // 2)),
                           ("gecis", max(7, GECIS_SAKLAMA_GUN // 2))):
            esik = (datetime.now() - timedelta(days=gun)).strftime("%Y-%m-%d %H:%M:%S")
            n = db.execute("DELETE FROM %s WHERE zaman < ?" % tablo, (esik,)).rowcount
            db.commit()
            print("      %s: %s satır silindi (%d günden eski)"
                  % (tablo, "{:,}".format(n).replace(",", "."), gun))
        # WAL'ı boşalt — yoksa silinen yer diske geri dönmez
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print("      sonuç: %.1f GB boş" % disk_bos_gb())
    except Exception as e:
        print("      ❌ acil budama başarısız: %s" % str(e)[:100])
    return bugun


def buda(db):
    """Eski kayıtları siler. İki tablo, iki ayrı ömür.

    ⚠️⚠️ 3 EYLÜL — DİSK DOLDU VE KAYDEDİCİ ÖLDÜ.
    `gecis` tablosu hiç budanmıyordu. Günde ~0,44 GB (veri + dört indeks) büyüdü,
    disk 03:11'de doldu, kaydedici `database or disk is full` alıp 03:15'te çöktü.
    Yedi saat konum verisi kaybedildi.

    NE KADAR GERİYE GEREK VAR — ölçüldü, tahmin değil:
        sure_modeli.DENENEN_PENCERELER  en fazla  14 gün
        durakta_ne_var.GOZLEM_GUN                  7 gün
        pencere_ayarla hedef gün + pencere        15 gün
    Yani 21 günden eski ham geçiş BUGÜN hiçbir sorguya girmiyor.

    ⭐⭐ 28 → 14 GÜN (7 Eylül, Mehmet'in kararı)

    28 gün konmuştu çünkü `pencere_ayarla()` ham `gecis`ten okuyordu ve 21 günlük
    pencereyi sınayabilmek için 21 günlük ham veri gerekiyordu. 4 Eylül'de o işlev
    PARÇA HAVUZUNA taşındı (sure_modeli.pencere_ayarla, kaynak="havuz"): havuz
    her gözlemin gün numarasını zaten taşıyor, dolayısıyla ayarlayıcı 21 günlük
    pencereyi ham veri olmadan da sınayabiliyor. Bağ koptu, gerekçe düştü.

    Kalan tek kısıt gerçek okuyucular:
        durakta_ne_var.GOZLEM_GUN                7 gün   ← en uzunu
        hayalet · gunluk · hat_analizi           1 gün
        parca_havuz beslemesi                   30 dakika
    8 gün ihtiyacı tam karşılardı; 14 seçildi çünkü emniyet payı bırakıyor ve
    haftalık desenleri elle incelemeye izin veriyor.

    ⚠️ 7 Eylül'de `gecisler.py` iz penceresi düzeltildi ve geçiş üretimi 4,6 kat
    arttı (elenen araç %31 → %1). Yani tablo artık daha hızlı büyüyor:
        14 gün ≈ 7,7 GB   ·   28 gün olsaydı ≈ 15,4 GB

    ⚠️ Silinen sayfalar dosyayı küçültmez (auto_vacuum kapalı) ama yeni veri
    onları YENİDEN KULLANIR — yani dosya büyümeyi durdurur. Amaç bu.
    """
    silinen = {}
    esik = (datetime.now() - timedelta(days=SAKLAMA_GUN)).strftime("%Y-%m-%d %H:%M:%S")
    silinen["filo_konum"] = db.execute(
        "DELETE FROM filo_konum WHERE zaman < ?", (esik,)).rowcount
    db.commit()

    esik_g = (datetime.now() - timedelta(days=GECIS_SAKLAMA_GUN)).strftime("%Y-%m-%d %H:%M:%S")
    silinen["gecis"] = db.execute(
        "DELETE FROM gecis WHERE zaman < ?", (esik_g,)).rowcount
    db.commit()
    return silinen


# ─────────────────────────────────────────────────────────────────────────────
# DÖNGÜ
# ─────────────────────────────────────────────────────────────────────────────


def _not_dus(db, zaman, hedef, aciklama):
    """Hata kaydını yazmaya çalışır; O DA başarısız olursa sessizce geçer.

    ⚠️ 28 Ağustos'ta süreç tam burada öldü: asıl yazma kilide takıldı, hatayı
    kaydetmek de aynı kilide takıldı ve istisna döngüyü kırdı. Kaydedicinin
    çökmemesi, tek bir kaydı yazmasından daha önemli.
    """
    try:
        db.execute("INSERT INTO yoklama (zaman, hat, sonuc, arac_sayisi, yeni_kayit,"
                   " aciklama) VALUES (?,?,'hata',NULL,0,?)", (zaman, hedef, aciklama[:200]))
        db.commit()
    except Exception:
        pass


def sonraki_tura_kadar_bekle():
    simdi = time.time()
    hedef = (simdi // PERIYOT_SN + 1) * PERIYOT_SN + SANIYE_HIZASI
    time.sleep(max(1.0, hedef - simdi))


def dongu():
    db = veritabani_kur()
    butce = Butce(SAATLIK_BUTCE, db)
    print("kaydedici v2 — ŞEHİR GENELİ")
    print("  şehir görüntüsü: dakikada 1 istek · hat eşlemesi: %d turda 1"
          % HAT_SORGU_ARALIGI_TUR)
    print("  saatlik bütçe: %d istek (ölçülen kota 100)" % SAATLIK_BUTCE)
    print("  veritabanı: %s\n  Ctrl+C ile durur\n" % VERITABANI)

    tur, hat_sayaci, ustuste_hata = 0, 0, 0
    son_budama = None
    son_acil_budama = None
    try:
        while True:
            sonraki_tura_kadar_bekle()
            tur += 1
            simdi = datetime.now()
            z = simdi.strftime("%Y-%m-%d %H:%M:%S")
            parcalar, hata_var = [], False

            # ── 1) ŞEHİR GÖRÜNTÜSÜ — bütçenin korunan kısmı ──────────────────
            if butce.kalan() > 0:
                try:
                    butce.harca()
                    toplam, hareketli, yeni, kapilar = sehir_goruntusu(db, simdi)
                    db.execute("INSERT INTO yoklama (zaman, hat, sonuc, arac_sayisi, yeni_kayit)"
                               " VALUES (?,'ŞEHİR','ok',?,?)", (z, toplam, yeni))
                    n_tahmin = hat_tahminleri(db, simdi, kapilar)
                    parcalar.append("şehir: %d araç · %d hareketli · +%d · hat tahmini +%d"
                                    % (toplam, hareketli, yeni, n_tahmin))
                except Exception as e:
                    hata_var = True
                    _not_dus(db, z, "ŞEHİR", str(e))
                    parcalar.append("şehir: HATA %s" % str(e)[:45])
            else:
                parcalar.append("şehir: bütçe bitti")

            # ── 2) HAT EŞLEMESİ — bütçenin esnek kısmı ───────────────────────
            if (tur % HAT_SORGU_ARALIGI_TUR == 0 and not hata_var
                    and butce.kalan() > HAT_SORGUSU_YEDEGI):
                hat = sonraki_hat(db, hat_sayaci)
                hat_sayaci += 1
                try:
                    butce.harca()
                    n = hat_eslemesi(db, hat, simdi)
                    db.execute("INSERT INTO yoklama (zaman, hat, sonuc, arac_sayisi, yeni_kayit)"
                               " VALUES (?,?,'ok',?,?)", (z, hat, n, n))
                    parcalar.append("hat %s: %d araç" % (hat, n))
                except Exception as e:
                    hata_var = True
                    _not_dus(db, z, hat, str(e))
                    parcalar.append("hat %s: HATA" % hat)

            try:
                db.commit()
            except Exception as e:
                print("   ↳ commit hatası (yok sayıldı): %s" % str(e)[:60])
            print("%s  [bütçe %2d/%d]  %s"
                  % (z[11:], butce.kalan(), SAATLIK_BUTCE, "  |  ".join(parcalar)))

            # ── 3) DİSK GÖZCÜSÜ ─────────────────────────────────────────────
            #    launchd ölen süreci geri getirir ama disk doluysa geri gelen
            #    süreç de yazamaz — bu yüzden kurtarma sürecin İÇİNDE olmalı.
            if tur % DISK_KONTROL_TUR == 0:
                son_acil_budama = disk_gozcusu(db, son_acil_budama)

            # ── 4) GÜNDE BİR BUDAMA ──────────────────────────────────────────
            if son_budama != simdi.date() and simdi.hour == 4:
                silinen = buda(db)
                son_budama = simdi.date()
                print("   ↳ budama: filo_konum %s · gecis %s satır silindi"
                      % ("{:,}".format(silinen["filo_konum"]).replace(",", "."),
                         "{:,}".format(silinen["gecis"]).replace(",", ".")))

            if hata_var:
                ustuste_hata += 1
                bekle = BEKLEME_MERDIVENI[min(ustuste_hata - 1, len(BEKLEME_MERDIVENI) - 1)]
                print("   ↳ %d tur üst üste hata · %d sn susuluyor" % (ustuste_hata, bekle))
                time.sleep(bekle)
            else:
                ustuste_hata = 0

    except KeyboardInterrupt:
        print("\ndurduruldu.")
    finally:
        db.commit()
        for etiket, sorgu in (("filo_konum", "SELECT COUNT(*) FROM filo_konum"),
                              ("arac_hat", "SELECT COUNT(*) FROM arac_hat"),
                              ("yoklama", "SELECT COUNT(*) FROM yoklama")):
            print("  %-12s %d" % (etiket, db.execute(sorgu).fetchone()[0]))
        db.close()


if __name__ == "__main__":
    sys.exit(dongu())

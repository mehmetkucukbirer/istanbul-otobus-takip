"""
DUYURU KAYDEDİCİSİ — İETT'nin canlı sefer iptali akışını yakalar ve saklar.

⭐ NEDEN VAR (1 Eylül, 4. seans):
  Bölüm 29-34'te iptali konum verisinden ÇIKARMAYA çalıştık; yedi hipotez denendi,
  precision %13'te tıkandı ve bunun bir "bilgi sınırı" olduğu sonucuna varıldı.
  Yanlış sonuçtu — sınır bilgide değil, baktığımız yerdeydi.

  Sahadaki akıllı durak ekranının turuncu şeridinde iptaller kalkış saatiyle
  yazıyordu (Bölüm 42). İzi sürüldü: İBB açık veri portalı İETT'nin 13 veri setini
  listeliyor ve içlerinden biri "IETT Announcements Web Service" —
  UlasimDinamikVeri/Duyurular.asmx. Bölüm 8'de BEŞ servis yolu taranmıştı;
  bu ALTINCISI listede hiç yoktu, o yüzden hiç sorulmadı.

  GetDuyurular_json parametresiz çağrılıyor ve iptali doğrudan veriyor:
      HATKODU · TIP · GUNCELLEME_SAATI · MESAJ
      "<KALKIŞ YERİ> dan Saat 14:28 de hareket etmesi planlanan seferimiz
       çesitli nedenlerle yapilamayacaktir."
  Yani tahmin etmeye gerek yok — OKUNUYOR. Üstelik kalkıştan ÖNCE.

⚠️ AKIŞ KAYAN PENCERE — bu betiğin var olma sebebi:
  14:29'da bakıldığında akışta yalnızca 14:00-16:12 arası iptaller vardı.
  Sabahki iptaller gitmiş. Servis arşiv tutmuyor; kaydetmezsek veri KAYBOLUYOR.
  (Konum verisiyle aynı durum — bu yüzden aynı çözüm: sürekli yoklama.)

⚠️ KOTAYI KAYDEDİCİYLE PAYLAŞIR:
  Her yoklama `yoklama` tablosuna yazılır. kaydedici.py'nin bütçe sayacı o
  tablodan okuyor (hangi süreç harcamış olursa olsun), dolayısıyla bu betiğin
  harcadığını görüp kendi hat sorgularını kendiliğinden kısar. Ek eşgüdüm yok.
  10 dakikada bir = saatte 6 istek.

ÇALIŞTIRMA:
    python3 duyurular.py          bir tur yoklar, yazar, çıkar
    python3 duyurular.py --ozet   yoklama yapmadan biriken veriyi özetler
"""

import html
import json
import re
import sqlite3
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

VERITABANI = Path(__file__).parent / "veri" / "kayit.db"
BASE, NS = "https://api.ibb.gov.tr/iett/", "http://tempuri.org/"
YOL, METOT = "UlasimDinamikVeri/Duyurular.asmx", "GetDuyurular_json"

SAATLIK_BUTCE = 95   # kaydedici.py ile aynı sınır; ölçülen kota 100 (Bölüm 17)


# ─────────────────────────────────────────────────────────────────────────────

def soap_duyuru():
    """Parametresiz SOAP çağrısı. Cevap gövdesi JSON metni olarak geliyor."""
    zarf = ('<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Body><%s xmlns="%s" /></soap:Body></soap:Envelope>' % (METOT, NS))
    istek = urllib.request.Request(
        BASE + YOL, data=zarf.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": NS + METOT})
    with urllib.request.urlopen(istek, timeout=45) as cevap:
        kok = ET.fromstring(cevap.read())
    sonuc = next((e for e in kok.iter() if e.tag.endswith("Result")), None)
    if sonuc is None or not sonuc.text:
        return []
    return json.loads(html.unescape(sonuc.text))


# ─────────────────────────────────────────────────────────────────────────────
# AYRIŞTIRMA
#
# Sefer iptali mesajının kalıbı (232/232 örnekte tuttu, %100):
#   "<KALKIŞ YERİ> dan Saat 14:28 de hareket etmesi planlanan seferimiz ..."
# Türkçe ekler değişiyor (dan/den/tan/ten), saat ayıracı bazen nokta.
# ⚠️ Kalıp tutmazsa satır ATILMAZ — ham MESAJ saklanır, kalkış alanları boş kalır.
#    Servis metnini değiştirirse veriyi kaybetmemek için.
# ─────────────────────────────────────────────────────────────────────────────

KALKIS = re.compile(r'^(.*?)\s+(?:d[ae]n|t[ae]n)\s+Saat\s+(\d{1,2})[:.](\d{2})\s', re.I)
KAYIT_SAATI = re.compile(r'(\d{1,2})[:.](\d{2})')


def ayristir(kayit):
    """Bir duyuru kaydından (kalkış yeri, kalkış saati) çıkarır. Bulamazsa (None, None)."""
    m = KALKIS.match((kayit.get("MESAJ") or "").strip())
    if not m:
        return None, None
    return m.group(1).strip(), "%02d:%s" % (int(m.group(2)), m.group(3))


def kayit_saati(kayit):
    """'Kayit Saati: 04:05' → '04:05'. Duyurunun sisteme girildiği an."""
    m = KAYIT_SAATI.search(kayit.get("GUNCELLEME_SAATI") or "")
    return "%02d:%s" % (int(m.group(1)), m.group(2)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# VERİTABANI
# ─────────────────────────────────────────────────────────────────────────────

def veritabani_kur():
    db = sqlite3.connect(str(VERITABANI), timeout=90)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS duyuru (
            id INTEGER PRIMARY KEY,
            tarih         TEXT,   -- yyyy-mm-dd, duyuruyu gördüğümüz gün
            hat           TEXT,
            tip           TEXT,   -- 'Sefer' (tek sefer iptali) | 'Günlük' (güzergâh vb.)
            kalkis_yeri   TEXT,   -- mesajdan ayrıştırıldı, Günlük tipte NULL
            kalkis_saati  TEXT,   -- 'HH:MM', Günlük tipte NULL
            kayit_saati   TEXT,   -- duyurunun İETT sistemine girildiği saat
            mesaj         TEXT,   -- ham metin, ayrıştırma değişirse diye
            ilk_gorulme   TEXT,   -- bizim ilk gördüğümüz an
            son_gorulme   TEXT,   -- akıştan düşene kadar son gördüğümüz an
            gorulme_sayisi INTEGER DEFAULT 1
        );
        -- Aynı duyuru her yoklamada tekrar geliyor; tekilleştirme anahtarı bu.
        -- Günlük tipte kalkış alanları boş olduğu için mesaj da anahtara giriyor.
        CREATE UNIQUE INDEX IF NOT EXISTS ix_duyuru_tekil
            ON duyuru (tarih, hat, tip, IFNULL(kalkis_saati,''), IFNULL(mesaj,''));
        CREATE INDEX IF NOT EXISTS ix_duyuru_hat  ON duyuru (hat, tarih);
        CREATE INDEX IF NOT EXISTS ix_duyuru_saat ON duyuru (tarih, kalkis_saati);

        CREATE TABLE IF NOT EXISTS yoklama (
            id INTEGER PRIMARY KEY, zaman TEXT, hat TEXT, sonuc TEXT,
            arac_sayisi INTEGER, yeni_kayit INTEGER, aciklama TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_yoklama_zaman ON yoklama (zaman);
    """)
    db.commit()
    return db


def butce_kalan(db):
    """Bu saatte kaç istek hakkımız kaldı. Sayaç `yoklama` tablosundan okunuyor —
    kaydedici.py de aynı tabloyu kullanıyor, yani bütçe ortak (Bölüm 20, Hata 2)."""
    saat = datetime.now().strftime("%Y-%m-%d %H")
    r = db.execute("SELECT COUNT(*) FROM yoklama WHERE substr(zaman,1,13)=?",
                   (saat,)).fetchone()
    return SAATLIK_BUTCE - (r[0] if r else 0)


def not_dus(db, zaman, sonuc, adet, yeni, aciklama=None):
    """Yoklamayı kaydet. ⚠️ Yazılamazsa sessizce geç — tek kaydı yazmak, sürecin
    ayakta kalmasından önemli değil (Bölüm 31'de öğrenildi: hata kaydetme yolunun
    kendisi kilide takılıp döngüyü kırmıştı)."""
    try:
        db.execute("INSERT INTO yoklama (zaman, hat, sonuc, arac_sayisi, yeni_kayit,"
                   " aciklama) VALUES (?,?,?,?,?,?)",
                   (zaman, "DUYURU", sonuc, adet, yeni, aciklama))
        db.commit()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────

def tur(db):
    simdi = datetime.now()
    z = simdi.strftime("%Y-%m-%d %H:%M:%S")
    bugun = simdi.strftime("%Y-%m-%d")

    kalan = butce_kalan(db)
    if kalan <= 0:
        print("%s  bütçe bitti (%d), yoklanmadı" % (z[11:], kalan))
        return

    try:
        kayitlar = soap_duyuru()
    except Exception as e:
        # Kota hatası ile "servis yok" aynı HTTP 500'ü döner; ayrım gövdede (Bölüm 8).
        not_dus(db, z, "hata", 0, 0, str(e)[:200])
        print("%s  HATA: %s" % (z[11:], str(e)[:120]))
        return

    yeni = guncellenen = 0
    for k in kayitlar:
        tip = (k.get("TIP") or "").strip()
        yer, saat = ayristir(k) if tip == "Sefer" else (None, None)
        satir = (bugun, (k.get("HATKODU") or "").strip(), tip, yer, saat,
                 kayit_saati(k), (k.get("MESAJ") or "").strip(), z, z)
        try:
            db.execute(
                "INSERT INTO duyuru (tarih, hat, tip, kalkis_yeri, kalkis_saati,"
                " kayit_saati, mesaj, ilk_gorulme, son_gorulme) VALUES (?,?,?,?,?,?,?,?,?)",
                satir)
            yeni += 1
        except sqlite3.IntegrityError:
            # Zaten var — ne zamandan beri akışta durduğunu izlemek için tazele.
            db.execute(
                "UPDATE duyuru SET son_gorulme=?, gorulme_sayisi=gorulme_sayisi+1"
                " WHERE tarih=? AND hat=? AND tip=? AND IFNULL(kalkis_saati,'')=?"
                " AND IFNULL(mesaj,'')=?",
                (z, bugun, satir[1], tip, saat or "", satir[6]))
            guncellenen += 1
    db.commit()

    sefer = sum(1 for k in kayitlar if (k.get("TIP") or "").strip() == "Sefer")
    not_dus(db, z, "ok", len(kayitlar), yeni)
    print("%s  [bütçe %d/%d]  duyuru: %d (%d sefer iptali) · +%d yeni · %d tazelendi"
          % (z[11:], kalan - 1, SAATLIK_BUTCE, len(kayitlar), sefer, yeni, guncellenen))


# ─────────────────────────────────────────────────────────────────────────────
# İPTAL HARİTASI — duyuruyu TARİFEDEKİ kalkışa bağlar
#
# ⚠️ NEDEN GEREKLİ: duyuru yalnızca (hat, kalkış yeri, kalkış saati) veriyor, YÖN
#    vermiyor. Tarifede aynı saatte iki yönde birden kalkış olabiliyor — ölçüldü,
#    312 duyurunun 65'i (%21) böyle. Yanlış yönü iptal işaretlemek, yolcuya yanlış
#    söylemek demek; bu uygulamanın tek kozu olan güveni yıkar.
#
#    Çözüm: duyurudaki kalkış yerini o yönün İLK DURAĞIYLA eşleştir.
#    Ölçüm: belirsiz 65 vakanın 59'u (%91) böyle çözüldü.
#    Kalan 6'sı hattın ucundan değil ARA duraktan kalkan kısa seferler —
#    onlarda yön İDDİA EDİLMİYOR (`belirsiz` kümesine düşüyorlar).
# ─────────────────────────────────────────────────────────────────────────────

import unicodedata

GUN_TIPI = {5: "C", 6: "P"}   # cumartesi / pazar · diğerleri "I" (hafta içi)


def sadelestir(s):
    """Türkçe harfleri ve noktalamayı düşürür. Duyuru metni şapkasız ve noktasız
    geliyor ('IGTOT'), durak adı ise tam yazılıyor ('İGTOT') — eşleşsinler diye."""
    if not s:
        return ""
    s = s.upper()
    for a, b in (("İ", "I"), ("Ş", "S"), ("Ğ", "G"), ("Ü", "U"),
                 ("Ö", "O"), ("Ç", "C"), ("Â", "A"), ("Î", "I")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", s)


_onbellek = {"anahtar": None, "deger": None}

# ⭐⭐ AKIŞTAN DÜŞEN DUYURU = GERİ ALINMIŞ SEFER (2 Eylül'de ölçüldü)
#
# İlk sürüm o günün TÜM duyurularını kullanıyordu. Ama duyuru sabah 04:05'te
# giriliyor ve sefer sonradan telafi edilirse akıştan DÜŞÜYOR. Ölçüldü
# (1 Eylül · 1.325 duyuru · arşivle kıyas):
#
#     duyurunun durumu          sayı    İSABET
#     kalkışa kadar durdu       1094    %66,0
#     12-45 dk önce düştü         77    %13,0   ← geri alınmış
#     45+ dk önce düştü          154    %10,4   ← geri alınmış
#
# Yani düşen duyuruya bakıp "iptal" demek, on vakanın dokuzunda yanlış.
# Süzgeç isabeti %56,5 → %66,0 çıkarıyor, kapsamadan yalnızca 1,1 puan alıyor.
#
# ⚠️ Tazelik eşiği yoklama aralığının (10 dk) iki buçuk katı: bir tur kaçsa
#    ya da makine kısa süre donsa duyuru yanlışlıkla "geri alındı" sayılmasın.
TAZELIK_DK = 25


def iptal_haritasi(kayit_db, dizin_db, tarih=None):
    """Bugünün duyurularını tarifedeki kalkışlara bağlar.

    Döner: {
      "kesin"   : {(hat, yon, 'HH:MM'): duyuru_dict}   yön çözüldü, güvenle söylenebilir
      "belirsiz": {(hat, 'HH:MM'): duyuru_dict}        yön çözülemedi, yön iddia etme
      "gunluk"  : {hat: [mesaj, ...]}                  güzergâh değişikliği vb.
    }
    Sonuç dakikada bir önbelleğe alınır — durak sorgusu 0,17 sn (Bölüm 39), bu
    haritayı her çağrıda yeniden kurmak o kazanımı yerdi.
    """
    simdi = datetime.now()
    tarih = tarih or simdi.strftime("%Y-%m-%d")
    anahtar = (tarih, simdi.strftime("%H:%M"))
    if _onbellek["anahtar"] == anahtar:
        return _onbellek["deger"]

    gt = GUN_TIPI.get(datetime.strptime(tarih, "%Y-%m-%d").weekday(), "I")

    # her (hat, yon) için ilk durak adı — yön çözümünün dayanağı
    ilk = {}
    for hat, yon, ad in dizin_db.execute("""
            SELECT hd.hat_kodu, hd.yon, dr.durak_adi FROM hat_durak hd
            JOIN durak dr ON dr.durak_kodu = hd.durak_kodu
            WHERE hd.sira = (SELECT MIN(sira) FROM hat_durak x
                             WHERE x.hat_kodu = hd.hat_kodu AND x.yon = hd.yon)"""):
        ilk[(hat, yon)] = sadelestir(ad)

    # Yalnızca ŞU AN akışta duran duyurular. Düşenler geri alınmış demektir.
    # Geçmiş bir gün sorgulanıyorsa (doğrulama) tazelik süzgeci uygulanmaz —
    # o gün akış zaten bitmiş, `son_gorulme` doğal olarak eski.
    if tarih == simdi.strftime("%Y-%m-%d"):
        esik = (simdi - timedelta(minutes=TAZELIK_DK)).strftime("%Y-%m-%d %H:%M:%S")
        kosul, par = " AND son_gorulme >= ?", (tarih, esik)
    else:
        kosul, par = "", (tarih,)

    kesin, belirsiz, gunluk = {}, {}, {}
    for hat, tip, yer, saat, mesaj in kayit_db.execute(
            "SELECT hat, tip, kalkis_yeri, kalkis_saati, mesaj FROM duyuru"
            " WHERE tarih = ?" + kosul, par):
        if tip != "Sefer" or not saat:
            gunluk.setdefault(hat, []).append(mesaj)
            continue
        kayit = {"hat": hat, "kalkis_yeri": yer, "kalkis_saati": saat, "mesaj": mesaj}
        yonler = [r[0] for r in dizin_db.execute(
            "SELECT DISTINCT yon FROM tarife WHERE hat_kodu=? AND gun_tipi=? AND saat LIKE ?",
            (hat, gt, saat + "%"))]
        if len(yonler) == 1:
            kesin[(hat, yonler[0], saat)] = kayit
        elif len(yonler) > 1:
            y = sadelestir(yer)
            # ilk 12 harf yeter: 'SABIHA GOKCEN HAVALIMANI' ile 'SABIHA GOKCEN' eşleşsin
            uyan = [yo for yo in yonler
                    if y and (y.startswith(ilk.get((hat, yo), "")[:12])
                              or ilk.get((hat, yo), "").startswith(y[:12]))]
            if len(uyan) == 1:
                kesin[(hat, uyan[0], saat)] = kayit
            else:
                belirsiz[(hat, saat)] = kayit
        # yonler boşsa: tarifede yok (yeni hat / dizin eskimiş) — sessizce atlanır

    _onbellek["anahtar"] = anahtar
    _onbellek["deger"] = {"kesin": kesin, "belirsiz": belirsiz, "gunluk": gunluk}
    return _onbellek["deger"]


def ozet(db):
    """Yoklama yapmadan biriken veriyi göster — kotaya dokunmaz."""
    r = db.execute("SELECT COUNT(*), COUNT(DISTINCT hat), MIN(ilk_gorulme),"
                   " MAX(son_gorulme) FROM duyuru").fetchone()
    print("toplam duyuru : %s   ayrı hat: %s" % (r[0], r[1]))
    print("ilk kayıt     : %s\nson kayıt     : %s" % (r[2], r[3]))
    print()
    for tip, n in db.execute("SELECT tip, COUNT(*) FROM duyuru GROUP BY tip"
                             " ORDER BY 2 DESC"):
        print("   %-10s %d" % (tip, n))
    print("\n── bugünkü sefer iptalleri, kalkış saatine göre ──")
    for saat, n in db.execute(
            "SELECT substr(kalkis_saati,1,2), COUNT(*) FROM duyuru"
            " WHERE tip='Sefer' AND tarih=date('now','localtime')"
            " GROUP BY 1 ORDER BY 1"):
        print("   %s:00  %s %d" % (saat, "█" * min(n, 60), n))


if __name__ == "__main__":
    db = veritabani_kur()
    if "--ozet" in sys.argv:
        ozet(db)
    else:
        tur(db)
    db.close()

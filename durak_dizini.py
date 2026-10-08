"""
DURAK DİZİNİ — "bu duraktan hangi hatlar geçer" sorusunu cevaplayabilmek için.

NEDEN VAR:
  Uygulamanın ana ekranı "bu duraktayım, ne gelecek". Bunun için durak → hat
  eşlemesi lazım. İETT'nin bu sorguyu yapan metodu (GetStopLines_json) geçitte
  KAPALI (ölçüldü, Otobüs Takip Uygulaması PROJE DURUMU.md Bölüm 8). Elimizde yalnızca ters yön var:
  DurakDetay_GYY_wYonAdi ile "şu hattın durakları neler" sorulabiliyor.

  Bu betik 783 hattın hepsini tek tek çekip ilişkiyi TERS ÇEVİRİYOR. Sonuçta
  durak kodundan hatlara tek sorguda ulaşılıyor. Tek seferlik iş; bittikten
  sonra dizin yerelde durur, servise bir daha sorulmaz.

ÇALIŞTIRMA:
    python3 durak_dizini.py

  Yarıda kesilirse tekrar çalıştır — bitmiş hatları atlar, kaldığı yerden devam eder.

ÇIKTI:  veri/dizin.db   (kaydedicinin kayit.db'sinden AYRI dosya —
                         kaydedici sürekli yazıyor, kilit çakışması olmasın)
"""

import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

VERITABANI = Path(__file__).parent / "veri" / "dizin.db"
BASE = "https://api.ibb.gov.tr/iett/"
NS = "http://tempuri.org/"
ISTEK_ARASI_SN = 0.15          # eski projede 0,12 sn ile 676 hat sorunsuz çekilmişti
BEKLEME_MERDIVENI = [60, 180, 300, 600]


# ─────────────────────────────────────────────────────────────────────────────
# SERVİS
# ─────────────────────────────────────────────────────────────────────────────

def _istek(yol, metot, parametreler):
    govde = "".join("<%s>%s</%s>" % (k, v, k) for k, v in parametreler.items())
    zarf = ('<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Body><%s xmlns="%s">%s</%s></soap:Body></soap:Envelope>'
            % (metot, NS, govde, metot))
    istek = urllib.request.Request(
        BASE + yol, data=zarf.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": NS + metot})
    with urllib.request.urlopen(istek, timeout=45) as cevap:
        return ET.fromstring(cevap.read())


def soap_json(yol, metot, parametreler):
    """Adı _json ile BİTEN metotlar: sonuç XML içine gömülü JSON."""
    sonuc = next((e for e in _istek(yol, metot, parametreler).iter()
                  if e.tag.endswith("Result")), None)
    return json.loads(sonuc.text) if (sonuc is not None and sonuc.text) else []


def soap_xml(yol, metot, parametreler):
    """Adı _json ile BİTMEYEN metotlar: düz XML, NewDataSet altında satırlar."""
    nds = next((e for e in _istek(yol, metot, parametreler).iter()
                if e.tag.endswith("NewDataSet")), None)
    if nds is None:
        return []
    return [{c.tag.split("}")[-1]: c.text for c in satir} for satir in nds]


# ─────────────────────────────────────────────────────────────────────────────
# VERİTABANI
# ─────────────────────────────────────────────────────────────────────────────

def veritabani_kur():
    VERITABANI.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(VERITABANI))
    db.executescript("""
        CREATE TABLE IF NOT EXISTS hat (
            hat_kodu      TEXT PRIMARY KEY,
            hat_adi       TEXT,
            tarife        TEXT,
            hat_uzunlugu  REAL,
            sefer_suresi  REAL,
            durum         TEXT     -- 'ok' | 'bos' | 'hata'  (çekim sonucu)
        );
        CREATE TABLE IF NOT EXISTS durak (
            durak_kodu  TEXT PRIMARY KEY,
            durak_adi   TEXT,
            enlem       REAL,
            boylam      REAL,
            ilce        TEXT,
            durak_tipi  TEXT
        );
        CREATE TABLE IF NOT EXISTS hat_durak (
            hat_kodu    TEXT NOT NULL,
            yon         TEXT NOT NULL,   -- 'G' | 'D'
            yon_adi     TEXT,
            sira        INTEGER NOT NULL,
            durak_kodu  TEXT NOT NULL,
            PRIMARY KEY (hat_kodu, yon, sira)
        );
        -- ASIL MESELE BU İNDEKS: durak kodundan hatlara tek sıçrayışta gitmeyi sağlar.
        CREATE INDEX IF NOT EXISTS ix_hat_durak_durak ON hat_durak (durak_kodu);
    """)
    db.commit()
    return db


def koordinat(x, y):
    """XKOORDINATI/YKOORDINATI hangisi enlem hangisi boylam belli değil.
    İstanbul'da enlem ~40-42, boylam ~27-30 → büyüklüğe bakarak ayırıyoruz."""
    def f(v):
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return None
    a, b = f(x), f(y)
    if a is None or b is None:
        return None, None
    return (a, b) if a > 39 else (b, a)      # (enlem, boylam)


# ─────────────────────────────────────────────────────────────────────────────
# ANA AKIŞ
# ─────────────────────────────────────────────────────────────────────────────

def hatlari_yaz(db):
    """783 hattın künyesini bir kerede çeker (HatKodu boş = hepsi)."""
    if db.execute("SELECT COUNT(*) FROM hat").fetchone()[0]:
        return
    print("hat listesi çekiliyor...")
    hatlar = soap_json("UlasimAnaVeri/HatDurakGuzergah.asmx", "GetHat_json", {"HatKodu": ""})
    def f(v):
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return None
    db.executemany(
        "INSERT OR IGNORE INTO hat (hat_kodu, hat_adi, tarife, hat_uzunlugu, sefer_suresi)"
        " VALUES (?,?,?,?,?)",
        [(h.get("SHATKODU"), h.get("SHATADI"), h.get("TARIFE"),
          f(h.get("HAT_UZUNLUGU")), f(h.get("SEFER_SURESI"))) for h in hatlar])
    db.commit()
    print("  %d hat kaydedildi\n" % len(hatlar))


def hattin_duraklarini_cek(db, hat_kodu):
    """Tek hattın durak listesini çeker ve iki tabloya yazar."""
    satirlar = soap_xml("ibb/ibb.asmx", "DurakDetay_GYY_wYonAdi", {"hat_kodu": hat_kodu})
    if not satirlar:
        return 0

    duraklar, baglar = [], []
    for s in satirlar:
        kod = s.get("DURAKKODU")
        if not kod:
            continue
        enlem, boylam = koordinat(s.get("XKOORDINATI"), s.get("YKOORDINATI"))
        duraklar.append((kod, s.get("DURAKADI"), enlem, boylam,
                         s.get("ILCEADI"), s.get("DURAKTIPI")))
        try:
            sira = int(s.get("SIRANO"))
        except (TypeError, ValueError):
            continue                       # sırasız kayıt rotaya oturtulamaz
        baglar.append((hat_kodu, s.get("YON"), s.get("YON_ADI"), sira, kod))

    db.executemany("INSERT OR IGNORE INTO durak"
                   " (durak_kodu, durak_adi, enlem, boylam, ilce, durak_tipi)"
                   " VALUES (?,?,?,?,?,?)", duraklar)
    db.executemany("INSERT OR REPLACE INTO hat_durak"
                   " (hat_kodu, yon, yon_adi, sira, durak_kodu) VALUES (?,?,?,?,?)", baglar)
    return len(baglar)


def calistir():
    db = veritabani_kur()
    hatlari_yaz(db)

    kalan = [r[0] for r in db.execute(
        "SELECT hat_kodu FROM hat WHERE durum IS NULL ORDER BY hat_kodu")]
    toplam = db.execute("SELECT COUNT(*) FROM hat").fetchone()[0]
    print("çekilecek hat: %d / %d   (bitmiş olanlar atlanıyor)\n" % (len(kalan), toplam))

    basladi = time.time()
    ustuste_hata = 0
    try:
        for i, hat in enumerate(kalan, 1):
            try:
                n = hattin_duraklarini_cek(db, hat)
                db.execute("UPDATE hat SET durum=? WHERE hat_kodu=?",
                           ("ok" if n else "bos", hat))
                ustuste_hata = 0
            except (urllib.error.HTTPError, urllib.error.URLError,
                    ET.ParseError, ValueError, OSError) as e:
                ustuste_hata += 1
                print("  ! %-8s hata: %s" % (hat, str(e)[:70]))
                if ustuste_hata >= 3:
                    # Üst üste hata = büyük ihtimalle kota. Israr cezayı uzatıyor.
                    bekle = BEKLEME_MERDIVENI[min(ustuste_hata - 3, len(BEKLEME_MERDIVENI) - 1)]
                    print("  ↳ %d saniye susuluyor" % bekle)
                    time.sleep(bekle)
                continue

            if i % 25 == 0 or i == len(kalan):
                db.commit()
                gecen = time.time() - basladi
                kalan_sn = gecen / i * (len(kalan) - i)
                n_bag = db.execute("SELECT COUNT(*) FROM hat_durak").fetchone()[0]
                n_durak = db.execute("SELECT COUNT(*) FROM durak").fetchone()[0]
                print("  %4d/%d  ·  %6d bağ  ·  %5d ayrı durak  ·  tahmini kalan %d dk"
                      % (i, len(kalan), n_bag, n_durak, kalan_sn / 60 + 0.5))
            time.sleep(ISTEK_ARASI_SN)
    except KeyboardInterrupt:
        print("\ndurduruldu — tekrar çalıştırınca kaldığı yerden devam eder.")
    finally:
        db.commit()
        ozet(db)
        db.close()


def ozet(db):
    print("\n" + "=" * 60)
    for etiket, sorgu in (
            ("hat (çekildi)", "SELECT COUNT(*) FROM hat WHERE durum='ok'"),
            ("hat (boş döndü)", "SELECT COUNT(*) FROM hat WHERE durum='bos'"),
            ("hat (çekilmedi)", "SELECT COUNT(*) FROM hat WHERE durum IS NULL"),
            ("ayrı durak", "SELECT COUNT(*) FROM durak"),
            ("hat-durak bağı", "SELECT COUNT(*) FROM hat_durak")):
        print("  %-18s %d" % (etiket, db.execute(sorgu).fetchone()[0]))
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(calistir())

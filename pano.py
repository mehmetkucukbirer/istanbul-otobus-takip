"""ADRES PANOSU — tünelin güncel adresini telefona dışarıdan duyurur.

⭐ NEDEN VAR (8 Ekim, Mehmet: *"her IP değişikliğinde neden otomatik olarak
kullanamıyoruz"*). Ücretsiz Cloudflare tüneli uzun bir kopuştan sonra yeniden
başlatılınca YENİ, rastgele bir adres alıyor (6-7 Ekim'de üç kez). Dışarıdaki
telefon eski adresi tutuyor ve yenisini öğrenmek için Mac'e sorması gerekiyor —
ama Mac'e ulaşmak için de yeni adres lazım. Tavuk-yumurta.

Pano bu döngüyü kırıyor: Mac her yeni adresi herkesin okuyabildiği SABİT bir
yere (ntfy.sh'ta gizli adlı bir konu) asıyor; telefon eski adrese ulaşamazsa
panoya bakıp yenisini alıyor. Tailscale ile farkı ve neden bu seçildiği:
PROJE DURUMU Bölüm 82.

⚠️⚠️ İLANLAR İMZALI. ntfy konuları herkese açık YAZILABİLİR: konunun adını
öğrenen biri sahte bir adres asarsa telefon o adrese gider ve X-Anahtar'ını
ORAYA gönderir — tek korumamız sızar. Bu yüzden her ilan erişim anahtarıyla
HMAC-SHA256 imzalanıyor; telefon imzası tutmayan ilanı yok sayıyor. Anahtarı
bilmeyen biri geçerli imza üretemez. İmzaya zaman damgası da giriyor: eski bir
ilanı yeniden asmak (tekrar saldırısı) daha yeni bir ilanı geçemez.

⚠️ ntfy mesajları 12 saat saklıyor. Adres uzun süre değişmezse pano BOŞALIR ve
tam ihtiyaç anında telefon hiçbir şey bulamaz. Bu yüzden aynı adres de
YENILEME_SAAT'te bir yeniden asılıyor.

⭐ BİLDİRİM (8 Ekim, 82.7). Adres GERÇEKTEN değişince Mehmet'in telefonuna okunur
bir bildirim de gidiyor — panodan AYRI, gizli adlı ikinci bir konuya
(veri/bildirim_konu.txt). Ayrı, çünkü pano imzalı JSON taşıyor ve 6 saatte bir
aynı adresi yeniden asıyor: panoya abone olmak günde 4 anlamsız bildirim demek.
Yalnız BİLGİ amaçlı (uygulama adresi kendisi buluyor). Mesajda anahtar YOK; bu
konuyu uygulama okumuyor, o yüzden buraya sahte mesaj asılması anahtarı sızdırmaz.

Kullanım:  python3 pano.py          → gerekiyorsa as (gözcü her turda çağırır)
           python3 pano.py --zorla  → hemen as
           python3 pano.py --dene   → deneme bildirimi gönder (abonelik sınaması)
"""
import hashlib
import hmac
import json
import re
import secrets
import sys
import time
import urllib.request
from pathlib import Path

VERI = Path(__file__).parent / "veri"
NTFY = "https://ntfy.sh"
#: Aynı adres bu kadar saatte bir yeniden asılır (ntfy 12 saat saklıyor).
YENILEME_SAAT = 6


def _gizli_ad(dosya, onek):
    """Bir ntfy konusunun gizli adı — ilk çağrıda üretilir, sonra hep aynı."""
    p = VERI / dosya
    if not p.exists() or not p.read_text().strip():
        # Tahmin edilemez ad: imza bütünlüğü korusa da, ad gizli kalırsa sahte
        # ilanlarla panoyu doldurmak (gürültü) de zorlaşır.
        p.write_text(onek + secrets.token_hex(12) + "\n")
        p.chmod(0o600)
    return p.read_text().strip()


def konu():
    """Panonun gizli adı."""
    return _gizli_ad("pano_konu.txt", "otobus-")


def bildirim_konu():
    """Bildirim konusunun gizli adı — panodan ayrı (birini bilen ötekini bilmesin)."""
    return _gizli_ad("bildirim_konu.txt", "otobus-bildirim-")


def imza(anahtar, adres, zaman):
    """Telefonla AYNI biçim: HMAC-SHA256(anahtar, "adres|zaman") → onaltılık."""
    return hmac.new(anahtar.encode(), ("%s|%d" % (adres, zaman)).encode(),
                    hashlib.sha256).hexdigest()


def guncel_adres():
    try:
        g = (VERI / "tunel.log").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    b = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", g)
    return b[-1] if b else None


def saglikli(adres):
    """Adres gerçekten cevap veriyor mu? Ölü adresi asmak telefonu yanıltırdı."""
    try:
        with urllib.request.urlopen(adres + "/saglik", timeout=15) as c:
            return c.status == 200
    except Exception:
        return False


def as_(adres):
    anahtar = (VERI / "anahtar.txt").read_text().strip()
    zaman = int(time.time())
    ilan = json.dumps({"adres": adres, "zaman": zaman, "imza": imza(anahtar, adres, zaman)})
    istek = urllib.request.Request("%s/%s" % (NTFY, konu()), data=ilan.encode(),
                                   method="POST", headers={"Title": "otobus-adres"})
    with urllib.request.urlopen(istek, timeout=15) as c:
        if c.status != 200:
            raise RuntimeError("ntfy %d" % c.status)
    (VERI / "pano_son.json").write_text(json.dumps({"adres": adres, "zaman": zaman}))
    return zaman


def bildir(adres, baslik="Otobüs takip · yeni adres"):
    """Telefona okunur bildirim. JSON olarak yayınlanıyor: HTTP başlıkları Türkçe
    harf taşıyamıyor (Title: Otobüs → latin-1 hatası)."""
    govde = json.dumps({
        "topic": bildirim_konu(),
        "title": baslik,
        "message": "Tünel yeni adres aldı:\n%s\n\nUygulama bunu kendisi buluyor; "
                   "bir şey yapman gerekmiyor." % adres,
        "tags": ["bus"],
    })
    istek = urllib.request.Request(NTFY, data=govde.encode(), method="POST",
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=15) as c:
        if c.status != 200:
            raise RuntimeError("ntfy %d" % c.status)


def gerekiyorsa_as(zorla=False):
    """Adres değiştiyse ya da son ilan eskidiyse (ve adres sağlıklıysa) asar."""
    adres = guncel_adres()
    if not adres:
        return "tünel adresi yok"
    try:
        son = json.loads((VERI / "pano_son.json").read_text())
    except Exception:
        son = {}
    eski = time.time() - son.get("zaman", 0) > YENILEME_SAAT * 3600
    if not zorla and son.get("adres") == adres and not eski:
        return "güncel"
    if not saglikli(adres):
        return "adres henüz cevap vermiyor — asılmadı"
    as_(adres)
    sonuc = "asıldı: %s" % adres
    # Bildirim yalnız adres GERÇEKTEN değişince — 6 saatlik tazeleme sessiz kalır.
    # Bildirim düşerse pano yine de asılmış sayılır (asıl iş o).
    if son.get("adres") != adres:
        try:
            bildir(adres)
            sonuc += " · bildirildi"
        except Exception as h:
            sonuc += " · bildirim gönderilemedi (%s)" % h
    return sonuc


if __name__ == "__main__":
    if "--dene" in sys.argv:
        bildir(guncel_adres() or "(tünel adresi yok)", baslik="Otobüs takip · deneme")
        print("deneme bildirimi gönderildi")
    else:
        print(gerekiyorsa_as(zorla="--zorla" in sys.argv))

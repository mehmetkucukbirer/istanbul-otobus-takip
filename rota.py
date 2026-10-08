"""
ROTA — durakları ve araçları gerçek yol çizgisine oturtan geometri modülü.

NEDEN VAR:
  "Otobüs durağa ne kadar uzakta?" sorusunun kuş uçuşu cevabı YANLIŞ. Otobüs
  yoldan gidiyor; viraj, kavşak, sapma hepsi mesafeye giriyor. Ayrıca kuş uçuşu
  mesafe aracın durağı GEÇİP GEÇMEDİĞİNİ de söyleyemez — 500 m ötede duran araç
  yaklaşıyor da olabilir, uzaklaşıyor da.

  Çözüm: hem durağı hem aracı rota çizgisi üzerine İZDÜŞÜRMEK. Böylece ikisi de
  "rotanın başından kaç metre sonra" diye tek bir sayıya dönüşür ve fark almak
  yeterli olur. Negatifse araç durağı geçmiştir.

VERİ:
  veri/rota_yollari.json  → hat/yön başına gerçek yol çizgisi (OSRM'den, [boylam, enlem])
  veri/guzergahlar.json   → hat/yön başına sıralı duraklar ([boylam, enlem, ad])

⚠️ Rota çizgisi sadeleştirilmiş (98'in D yönü 103 nokta, ~30 km). Metre metre
   kesinlik yok; dakika mertebesinde tahmin için yeterli.
⚠️ Eski projede 33 hatta OSRM sapması ölçülmüştü (en kötüsü 11R: API 18 km,
   çizim 45,8 km). O hatlarda mesafe hesabı güvenilmez.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

VERI = Path(__file__).parent / "veri"
DUNYA_YARICAPI_M = 6371008.8


# ─────────────────────────────────────────────────────────────────────────────
# TEMEL GEOMETRİ
# ─────────────────────────────────────────────────────────────────────────────

def _duzleme(boylam, enlem, enlem0):
    """Küre koordinatını yerel düzlem metresine çevirir (eşdikdörtgen yaklaşımı).

    İstanbul ölçeğinde (birkaç on km) hatası ihmal edilebilir, ama düzlemde
    çalışmak izdüşüm hesabını çok basitleştiriyor."""
    x = math.radians(boylam) * math.cos(math.radians(enlem0)) * DUNYA_YARICAPI_M
    y = math.radians(enlem) * DUNYA_YARICAPI_M
    return x, y


def _parca_izdusum(px, py, ax, ay, bx, by):
    """P noktasının AB parçası üzerindeki izdüşümü.
    Döner: (parça başından uzaklık m, P'nin parçaya dikey uzaklığı m, oran 0-1)"""
    dx, dy = bx - ax, by - ay
    uzunluk2 = dx * dx + dy * dy
    if uzunluk2 == 0:
        return 0.0, math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * dx + (py - ay) * dy) / uzunluk2
    t = max(0.0, min(1.0, t))              # parçanın dışına taşma
    ix, iy = ax + t * dx, ay + t * dy
    return t * math.sqrt(uzunluk2), math.hypot(px - ix, py - iy), t


# ─────────────────────────────────────────────────────────────────────────────
# ROTA
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _rotalar():
    return json.load(open(VERI / "rota_yollari.json", encoding="utf-8"))


@lru_cache(maxsize=1)
def _guzergahlar():
    return json.load(open(VERI / "guzergahlar.json", encoding="utf-8"))


@lru_cache(maxsize=2048)   # 1.495 hat-yön çifti var; 256 gündüz çalkalanıyordu
def yol(hat, yon):
    """Rota çizgisini düzlem metresine çevrilmiş hâlde döndürür.

    Döner: (noktalar [(x,y)...], kümülatif mesafeler [m...], referans enlem)"""
    ham = _rotalar()[hat][yon]
    enlem0 = sum(n[1] for n in ham) / len(ham)
    noktalar = [_duzleme(n[0], n[1], enlem0) for n in ham]
    kumulatif = [0.0]
    for i in range(1, len(noktalar)):
        (ax, ay), (bx, by) = noktalar[i - 1], noktalar[i]
        kumulatif.append(kumulatif[-1] + math.hypot(bx - ax, by - ay))
    return noktalar, kumulatif, enlem0


# ─────────────────────────────────────────────────────────────────────────────
# IZGARA — izdüşümü hızlandırmak için (7 Ekim)
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️⚠️ NEDEN VAR — Mehmet: *"gün içinde uygulamayı kullanmak istediğimde sunucu
#   yavaş çalışıyor"*. Profil (7 Ekim): durak isteğinin %90'ı `canli_araclar` →
#   `yon_bul` → `yol_uzerinde` zincirinde; tek istekte 468.667 `_parca_izdusum`
#   çağrısı. Eski yöntem her noktayı rotanın BÜTÜN parçalarıyla (ortalama 84)
#   tek tek kıyaslıyordu. Gündüz yükü (6 Ekim verisi, 3 durak × 3 saat):
#       eski     0,73 sn/istek
#       ızgara   0,40 sn/istek   → 1,8x
#
# ⚠️⚠️ SONUÇ BİREBİR AYNI — yaklaşık değil. Bu fonksiyon geçiş çıkarımında
#   (gecisler.py) ve yön tespitinde de kullanılıyor; yön tespiti sapmaların
#   ORTALAMASINI alıyor. Küçük bir sapma farkı bile geçiş verisini kaydırırdı.
#   Doğrulandı: 4.800 noktada (yakın + uzak karışık) sıfır fark.
#
#   Neden kesin: nokta P, (cx,cy) hücresinde. r halkasına kadar bakıldıysa,
#   bakılmamış her parçanın sınır kutusu bu karenin DIŞINDA kalıyor demektir;
#   o parçanın her noktası P'ye r·H'den KATI olarak uzak. Bulunan en iyi sapma
#   ≤ r·H ise uzaktaki hiçbir parça onu geçemez — durmak güvenli.
#   Eşitlikte en küçük indeks seçiliyor: eski döngü de ilk minimumu tutuyordu.
#
# Uzak noktalarda (rotadan >H sapma; gerçek çağrıların ~%14'ü) halka hızla
# tükenir ve kalan parçalara tek tek bakılır — eski yöntemle aynı maliyet.

#: Hücre kenarı (m). 150/250/400 denendi; gerçek yükte fark küçük, 250 seçildi.
HUCRE_M = 250.0
#: Bu kadar halkadan sonra kalan parçalara doğrudan bakılır (uzak noktalar).
MAX_HALKA = 1


@lru_cache(maxsize=2048)
def _izgara(hat, yon):
    """Her hücreye, sınır kutusu o hücreye değen parçaların indeksleri."""
    noktalar, _, _ = yol(hat, yon)
    izgara = {}
    for i in range(len(noktalar) - 1):
        (ax, ay), (bx, by) = noktalar[i], noktalar[i + 1]
        for gx in range(int(min(ax, bx) // HUCRE_M), int(max(ax, bx) // HUCRE_M) + 1):
            for gy in range(int(min(ay, by) // HUCRE_M), int(max(ay, by) // HUCRE_M) + 1):
                izgara.setdefault((gx, gy), []).append(i)
    return izgara


def yol_uzerinde(hat, yon, boylam, enlem):
    """Bir noktayı rotaya izdüşürür.

    Döner: (rota başından mesafe m, rotadan sapma m)
      · birinci sayı → 'bu nokta rotanın neresinde'
      · ikinci sayı  → 'bu nokta gerçekten rotanın üzerinde mi' (büyükse şüpheli)
    """
    noktalar, kumulatif, enlem0 = yol(hat, yon)
    px, py = _duzleme(boylam, enlem, enlem0)
    izgara = _izgara(hat, yon)
    cx, cy = int(px // HUCRE_M), int(py // HUCRE_M)

    bakildi, en_iyi = set(), None          # en_iyi = (sapma, indeks, mesafe)
    for r in range(MAX_HALKA + 1):
        for gx in range(cx - r, cx + r + 1):
            ys = range(cy - r, cy + r + 1) if gx in (cx - r, cx + r) else (cy - r, cy + r)
            for gy in ys:
                for i in izgara.get((gx, gy), ()):
                    if i in bakildi:
                        continue
                    bakildi.add(i)
                    (ax, ay), (bx, by) = noktalar[i], noktalar[i + 1]
                    ilerleme, sapma, _ = _parca_izdusum(px, py, ax, ay, bx, by)
                    if en_iyi is None or sapma < en_iyi[0] or (sapma == en_iyi[0] and i < en_iyi[1]):
                        en_iyi = (sapma, i, kumulatif[i] + ilerleme)
        if en_iyi is not None and en_iyi[0] <= r * HUCRE_M:
            return (en_iyi[2], en_iyi[0])

    for i in range(len(noktalar) - 1):     # uzak nokta: kalanlara tek tek
        if i in bakildi:
            continue
        (ax, ay), (bx, by) = noktalar[i], noktalar[i + 1]
        ilerleme, sapma, _ = _parca_izdusum(px, py, ax, ay, bx, by)
        if en_iyi is None or sapma < en_iyi[0] or (sapma == en_iyi[0] and i < en_iyi[1]):
            en_iyi = (sapma, i, kumulatif[i] + ilerleme)
    return (en_iyi[2], en_iyi[0]) if en_iyi else None


@lru_cache(maxsize=2048)   # 1.495 hat-yön çifti var; 256 gündüz çalkalanıyordu
def durak_mesafeleri(hat, yon):
    """Hattın her durağının rota başından uzaklığı.

    Döner: [(sıra, ad, mesafe_m, sapma_m), ...]  — sıra 1'den başlar
    """
    sonuc = []
    for i, (blm, enl, ad) in enumerate(_guzergahlar()[hat][yon], start=1):
        mesafe, sapma = yol_uzerinde(hat, yon, blm, enl)
        sonuc.append((i, ad, mesafe, sapma))
    return sonuc


def rota_uzunlugu(hat, yon):
    return yol(hat, yon)[1][-1]


def oran(hat, yon, sira):
    """Kaçıncı duraktaki yolcu, hattın toplam yolunun yüzde kaçını beklemiş olur?

    Varış tahmininin çekirdeği: sefer süresi × bu oran ≈ o durağa varış süresi.
    Durak SAYISINA göre değil MESAFEYE göre hesaplanır — duraklar eşit aralıklı değil.
    """
    d = durak_mesafeleri(hat, yon)
    toplam = rota_uzunlugu(hat, yon)
    return (d[sira - 1][2] / toplam) if toplam else 0.0

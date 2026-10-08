"""
HAT TAHMİNİ — aracın hangi hatta olduğunu GEOMETRİDEN çıkarır.

NEDEN VAR — projenin en büyük darboğazı:
  Şehir geneli servis (`GetFiloAracKonum_json`) 6.911 aracın konumunu tek istekte
  veriyor ama HAT KODU YOK. Hat kimliğini hatları tek tek sorarak öğreniyoruz ve
  kota (saatte 100 istek) buna günde ancak bir tur izin veriyor.

  Ölçüldü (28 Ağustos): 336 hattın 332'si gün boyunca YALNIZCA BİR KEZ eşlendi;
  hat×saat kapsaması %2,2. Bunun bedeli ilk geniş doğrulamada 6.291 kalkışta
  1.487 YANLIŞ ALARM oldu — kalkışların dörtte birinde "iptal" diyecektik.

  Yani: konumda 780 hattayız, hat kimliğinde 4 hattayız.

ÇÖZÜM:
  676 hattın gerçek yol geometrisi elimizde. Aracın son birkaç ölçümlük izini
  rotalarla karşılaştırıp hangisine oturduğunu buluyoruz. Kotaya hiç dokunmuyor.

NASIL:
  1. Rota noktalarından kaba bir IZGARA indeksi kurulur (hücre ~550 m).
     Aracın konumunun düştüğü hücreden aday hat/yön listesi okunur — 780 hattın
     hepsini denemek yerine avuç dolusu aday kalır.
  2. Her aday için izin tamamı o rotaya izdüşürülür ve iki şeye bakılır:
        SAPMA     — araç gerçekten o çizginin üstünde mi
        İLERLEME  — rota boyunca ileri mi gidiyor (yön de buradan çıkar)
  3. En iyi aday, ikinciden belirgin farkla öndeyse kabul edilir.
     ⚠️ Değilse HİÇBİR ŞEY DENMEZ. Ortak koridorlarda (Mecidiyeköy, E-5) birçok hat
     aynı yoldan geçer; oradaki araca hat atamak uydurma olur.

KULLANIM:
    python3 hat_tahmini.py --sina      # bilinen eşlemelerle isabet ölçer
    python3 hat_tahmini.py             # son ölçümler için tahmin üretir ve yazar
"""

import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rota

VERI = Path(__file__).parent / "veri"

HUCRE = 0.005              # ızgara hücresi, derece (~550 m)
MAX_SAPMA_M = 120          # ORTALAMA sapma sınırı
MAX_TEK_SAPMA_M = 320      # tek bir ölçüm bile bu kadar uzaklaşmamalı
MIN_ILERLEME_M = 250       # izin toplam ilerlemesi bundan azsa yön belirsiz
MIN_IZ = 4                 # en az bu kadar ölçüm olmadan karar verilmez
USTUNLUK = 3.2             # en iyi aday, ikinciden bu kat daha iyi olmalı
IZ_DK = 28                 # geriye kaç dakikalık iz kullanılacak
MIN_IZ_YOL_M = 800         # araç bu kadar yol katetmediyse ayırt edilemez


# ─────────────────────────────────────────────────────────────────────────────
# PARÇA IZGARASI — hızlı izdüşüm
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ NEDEN GEREKLİ: ilk sürüm her aday için TÜM rotayı tarıyordu. Bir araç-anı
#    ~5.600 izdüşüm demekti; kaydediciye bağlanınca saatler sürerdi.
#    Izgara artık hat değil ROTA PARÇASI düzeyinde: bir noktanın düştüğü hücreden
#    yalnızca yakındaki parçalar okunuyor, izdüşüm onlarla sınırlı kalıyor.

ENLEM0 = 41.05             # İstanbul için tek referans enlem — tüm rotalar aynı düzlemde
HUCRE_M = 600.0            # ızgara hücresi (metre)
DUNYA_R = 6371008.8

_rotalar_xy = None         # (hat,yon) -> (noktalar[(x,y)], kümülatif[m])
_parca_izgara = None       # (ci,cj) -> [(hat,yon,parça_indeksi)]


def _duzle(boylam, enlem):
    x = math.radians(boylam) * math.cos(math.radians(ENLEM0)) * DUNYA_R
    y = math.radians(enlem) * DUNYA_R
    return x, y


def _hucre(x, y):
    return int(x // HUCRE_M), int(y // HUCRE_M)


def _kur():
    global _rotalar_xy, _parca_izgara
    if _parca_izgara is not None:
        return
    ham = json.load(open(VERI / "rota_yollari.json", encoding="utf-8"))
    _rotalar_xy, _parca_izgara = {}, defaultdict(list)
    for hat, yonler in ham.items():
        for yon, noktalar in yonler.items():
            xy = [_duzle(b, e) for b, e in noktalar]
            kum = [0.0]
            for i in range(1, len(xy)):
                kum.append(kum[-1] + math.hypot(xy[i][0]-xy[i-1][0], xy[i][1]-xy[i-1][1]))
            _rotalar_xy[(hat, yon)] = (xy, kum)
            for i in range(len(xy) - 1):
                (ax, ay), (bx, by) = xy[i], xy[i+1]
                uz = math.hypot(bx-ax, by-ay)
                adim = max(1, int(uz / (HUCRE_M / 2)) + 1)
                for t in range(adim + 1):
                    px = ax + (bx-ax) * t / adim
                    py = ay + (by-ay) * t / adim
                    ci, cj = _hucre(px, py)
                    for di in (-1, 0, 1):
                        for dj in (-1, 0, 1):
                            _parca_izgara[(ci+di, cj+dj)].append((hat, yon, i))


def izgara():
    _kur()
    return _parca_izgara


def _parca_izdusum(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    uz2 = dx*dx + dy*dy
    if uz2 == 0:
        return 0.0, math.hypot(px-ax, py-ay)
    t = ((px-ax)*dx + (py-ay)*dy) / uz2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    ix, iy = ax + t*dx, ay + t*dy
    return t * math.sqrt(uz2), math.hypot(px-ix, py-iy)


def iz_izdusumleri(iz):
    """İzin her noktasını, YAKINDAKİ parçalara sahip her aday rotaya izdüşürür.

    Döner: {(hat,yon): [(mesafe_m, sapma_m) | None, ...]}  — iz sırasıyla
    """
    _kur()
    sonuc = defaultdict(lambda: [None] * len(iz))
    for k, (_, enlem, boylam) in enumerate(iz):
        px, py = _duzle(boylam, enlem)
        yakin = defaultdict(list)
        for hat, yon, i in _parca_izgara.get(_hucre(px, py), ()):
            yakin[(hat, yon)].append(i)
        for anahtar, parcalar in yakin.items():
            xy, kum = _rotalar_xy[anahtar]
            en_iyi = None
            for i in parcalar:
                (ax, ay), (bx, by) = xy[i], xy[i+1]
                ilerleme, sapma = _parca_izdusum(px, py, ax, ay, bx, by)
                if en_iyi is None or sapma < en_iyi[1]:
                    en_iyi = (kum[i] + ilerleme, sapma)
            sonuc[anahtar][k] = en_iyi
    return sonuc


# ─────────────────────────────────────────────────────────────────────────────
# PUANLAMA
# ─────────────────────────────────────────────────────────────────────────────

def _gercek_yol(iz):
    """Aracın ölçümler arasında GERÇEKTE katettiği yol (metre)."""
    toplam = 0.0
    for i in range(1, len(iz)):
        x0, y0 = _duzle(iz[i-1][2], iz[i-1][1])
        x1, y1 = _duzle(iz[i][2], iz[i][1])
        toplam += math.hypot(x1-x0, y1-y0)
    return toplam


def puanla(izdusum, gercek_yol, n):
    """(bedel, ilerleme) — bedel küçükse araç bu rotada demektir.

    Üç ölçü birlikte:
      ORTALAMA SAPMA  · araç çizginin üstünde mi
      EN BÜYÜK SAPMA  · yanlış rotada araç bir yerde ayrılır ve orada patlar
      YOL TUTARLILIĞI · rota üzerindeki ilerleme, GERÇEKTE katedilen yola yakın
                        olmalı. Ortak koridordan ayrılanı eleyen asıl ölçü bu;
                        eklenince isabet %67'den %94'e çıktı.
    """
    var = [v for v in izdusum if v]
    if len(var) < max(MIN_IZ, n // 2):
        return None                          # izin yarısında bile bu rotanın yanında değil
    sapmalar = [s for _, s in var]
    mesafeler = [m for m, _ in var]
    ort_sapma = sum(sapmalar) / len(sapmalar)
    if ort_sapma > MAX_SAPMA_M or max(sapmalar) > MAX_TEK_SAPMA_M:
        return None
    ilerleme = mesafeler[-1] - mesafeler[0]
    if ilerleme < MIN_ILERLEME_M:
        return None
    oran = ilerleme / gercek_yol if gercek_yol > 0 else 0
    tutarsizlik = abs(oran - 1.0)
    if tutarsizlik > 0.6:
        return None
    geri = sum(max(0.0, mesafeler[i-1] - mesafeler[i]) for i in range(1, len(mesafeler)))
    return ort_sapma + 0.45*max(sapmalar) + 260.0*tutarsizlik + geri/8.0, ilerleme


def tahmin_et(iz):
    """İzden (hat, yon, bedel) döndürür. Emin değilse None — uydurmuyoruz."""
    if len(iz) < MIN_IZ:
        return None
    gercek_yol = _gercek_yol(iz)
    if gercek_yol < MIN_IZ_YOL_M:
        return None
    puanlar = []
    for (hat, yon), izd in iz_izdusumleri(iz).items():
        p = puanla(izd, gercek_yol, len(iz))
        if p:
            puanlar.append((p[0], hat, yon))
    if not puanlar:
        return None
    puanlar.sort()
    en_iyi = puanlar[0]
    for bedel, hat, yon in puanlar[1:]:
        if hat != en_iyi[1]:
            if bedel < en_iyi[0] * USTUNLUK:
                return None                  # ortak koridor — karar verilemiyor
            break
    return en_iyi[1], en_iyi[2], en_iyi[0]


# ─────────────────────────────────────────────────────────────────────────────
# VERİ
# ─────────────────────────────────────────────────────────────────────────────

def arac_izi(kayit, kapino, an, dakika=IZ_DK):
    return kayit.execute(
        "SELECT zaman, enlem, boylam FROM filo_konum WHERE kapino=?"
        " AND zaman > ? AND zaman <= ? AND enlem IS NOT NULL ORDER BY zaman",
        (kapino, (an - timedelta(minutes=dakika)).strftime("%Y-%m-%d %H:%M:%S"),
         an.strftime("%Y-%m-%d %H:%M:%S"))).fetchall()


def sina(ornek=400):
    """Servisten gelen GERÇEK eşlemelerle isabet ölçer.

    `arac_hat` tablosu hat bazlı sorgudan geliyor, yani doğrunun kendisi.
    Aynı anlar için geometriden tahmin üretip karşılaştırıyoruz.
    """
    kayit = sqlite3.connect(str(VERI / "kayit.db"))
    gercek = kayit.execute(
        "SELECT zaman, kapino, hat, guzergahkodu FROM arac_hat"
        " WHERE zaman >= '2026-08-27 06:00' ORDER BY RANDOM() LIMIT ?", (ornek,)).fetchall()
    print("izgara kuruluyor...")
    izgara()
    print("%d gerçek eşleme üzerinde sınanıyor\n" % len(gercek))

    dogru = yanlis = suskun = izsiz = 0
    yon_dogru = yon_toplam = 0
    for zaman, kapino, hat, gkod in gercek:
        an = datetime.strptime(zaman, "%Y-%m-%d %H:%M:%S")
        iz = arac_izi(kayit, kapino, an)
        if len(iz) < MIN_IZ:
            izsiz += 1
            continue
        t = tahmin_et(iz)
        if t is None:
            suskun += 1
        elif t[0] == hat:
            dogru += 1
            if gkod and "_" in gkod:
                yon_toplam += 1
                if t[1] == gkod.split("_")[1]:
                    yon_dogru += 1
        else:
            yanlis += 1

    karar = dogru + yanlis
    print("=" * 60)
    print("  iz yetersiz (araç durmuş / yeni)  : %d" % izsiz)
    print("  karar verilemedi (ortak koridor)  : %d" % suskun)
    print("  KARAR VERİLEN                     : %d" % karar)
    if karar:
        print("    doğru hat  : %d  (%%%.1f)" % (dogru, 100.0 * dogru / karar))
        print("    yanlış hat : %d  (%%%.1f)" % (yanlis, 100.0 * yanlis / karar))
    if yon_toplam:
        print("    yön isabeti: %%%.1f (%d örnek)" % (100.0 * yon_dogru / yon_toplam, yon_toplam))
    kapsanan = izsiz + suskun + karar
    if kapsanan:
        print("\n  toplam örneğin %%%.0f'inde karar verildi" % (100.0 * karar / kapsanan))
    print("=" * 60)
    kayit.close()


if __name__ == "__main__":
    if "--sina" in sys.argv:
        sina(int(sys.argv[sys.argv.index("--sina") + 1])
             if len(sys.argv) > sys.argv.index("--sina") + 1 else 400)
    else:
        print("kullanım: python3 hat_tahmini.py --sina [örnek_sayısı]")

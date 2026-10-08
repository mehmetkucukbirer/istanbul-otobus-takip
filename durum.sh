#!/bin/zsh
# DURUM — kaydedici çalışıyor mu, ne topladı? Tek bakışta.
cd "/Users/mehmetkucukbirer/otobus-takip"
print -P "\n%F{cyan}═══ OTOBÜS TAKİP · DURUM ═══%f  $(date '+%d.%m.%Y %H:%M:%S')\n"

if pgrep -f "kaydedici.py" > /dev/null; then
  print -P "  %F{green}●%f  KAYDEDİCİ ÇALIŞIYOR"
else
  print -P "  %F{red}●%f  KAYDEDİCİ DURMUŞ  —  başlatmak için:"
  echo   "      cd \"/Users/mehmetkucukbirer/otobus-takip\" && nohup caffeinate -i python3 -u kaydedici.py >> veri/kaydedici.log 2>&1 &"
fi

pgrep -f "sabah_rutini.sh"   > /dev/null && print -P "  %F{green}●%f  sabah rutini bekliyor (09:00)"
pgrep -f "gecis_dongusu.sh"  > /dev/null && print -P "  %F{green}●%f  geçiş döngüsü (10 dk)" \
                                         || print -P "  %F{yellow}●%f  geçiş döngüsü DURMUŞ  —  ./gecis_dongusu.sh"
pgrep -f "duyuru_dongusu.sh" > /dev/null && print -P "  %F{green}●%f  duyuru döngüsü (10 dk · sefer iptalleri)" \
                                         || print -P "  %F{yellow}●%f  duyuru döngüsü DURMUŞ  —  ./duyuru_dongusu.sh"
pgrep -f "model_dongusu.sh"  > /dev/null && print -P "  %F{green}●%f  model döngüsü (saat başı · süre modeli)" \
                                         || print -P "  %F{yellow}●%f  model döngüsü DURMUŞ  —  ./model_dongusu.sh"
pgrep -f "gps_dongusu.sh"    > /dev/null && print -P "  %F{green}●%f  gps döngüsü (10 dk · karanlık sefer iddiaları)" \
                                         || print -P "  %F{yellow}●%f  gps döngüsü DURMUŞ  —  ./gps_dongusu.sh"
# ⚠️ ARAYÜZ SUNUCUSU — 4 Eylül'e kadar burada HİÇ görünmüyordu; sessizce ölünce
#    kimse fark etmiyordu (uygulama "sunucuya ulaşılamıyor" diyene kadar).
#    Süreç var mı DEĞİL, gerçekten CEVAP VERİYOR mu diye bakılıyor: süreç ayakta
#    kalıp cevap vermeyi bırakabilir.
if curl -s -m 2 -o /dev/null "http://localhost:8790/" 2>/dev/null; then
  print -P "  %F{green}●%f  arayüz sunucusu (8790 · cevap veriyor)"
elif pgrep -f "arayuz_sunucu.py" > /dev/null; then
  print -P "  %F{red}●%f  arayüz sunucusu AYAKTA AMA CEVAP VERMİYOR  —  öldürüp yeniden başlat"
else
  print -P "  %F{yellow}●%f  arayüz sunucusu DURMUŞ  —  nohup python3 -u arayuz_sunucu.py >> veri/arayuz_sunucu.log 2>&1 & disown"
fi
pgrep -f "caffeinate"      > /dev/null && print -P "  %F{green}●%f  uyku engelli (caffeinate)" \
                                       || print -P "  %F{yellow}●%f  uyku engeli YOK"

FIS=$(pmset -g batt | sed -n 2p | grep -q "discharging" && echo "PİLDE ⚠️" || echo "fişte")
PIL=$(pmset -g batt | sed -n 2p | grep -oE "[0-9]+%" | head -1)
print -P "  %F{blue}●%f  güç: $FIS · $PIL\n"

echo "  ── son 3 tur ─────────────────────────────────────"
grep -E "^[0-9]{2}:" veri/kaydedici.log | tail -3 | sed 's/^/     /'

python3 - <<'PY'
import sqlite3
from datetime import datetime
k = sqlite3.connect("veri/kayit.db", timeout=20)
son = k.execute("SELECT MAX(zaman) FROM yoklama").fetchone()[0]
gecen = (datetime.now() - datetime.strptime(son, "%Y-%m-%d %H:%M:%S")).total_seconds()
b = lambda n: "{:,}".format(n).replace(",", ".")
print("\n  ── veri ─────────────────────────────────────────")
print("     son kayıt      : %s  (%.0f saniye önce)" % (son[11:], gecen))
print("     %s" % ("✅ akış normal" if gecen < 180 else "⚠️  180 saniyeden uzun süredir kayıt yok"))
print("     toplam konum   : %s" % b(k.execute("SELECT COUNT(*) FROM filo_konum").fetchone()[0]))
bugun = datetime.now().strftime("%Y-%m-%d")
print("     bugün eklenen  : %s" % b(k.execute(
    "SELECT COUNT(*) FROM filo_konum WHERE zaman >= ?", (bugun,)).fetchone()[0]))
print("     hat eşlemesi   : %s" % b(k.execute("SELECT COUNT(*) FROM arac_hat").fetchone()[0]))
r = k.execute("SELECT COUNT(*), SUM(sonuc='ok') FROM yoklama WHERE zaman >= ?", (bugun,)).fetchone()
if r[0]:
    print("     bugünkü istek  : %d  (%d başarılı · %%%.0f)" % (r[0], r[1] or 0, 100.0*(r[1] or 0)/r[0]))
try:
    d = k.execute("SELECT COUNT(*), SUM(tip='Sefer'), MAX(son_gorulme) FROM duyuru"
                  " WHERE tarih = ?", (bugun,)).fetchone()
    print("     bugün duyuru   : %s  (%s sefer iptali · son %s)"
          % (b(d[0]), b(d[1] or 0), (d[2] or "—")[11:16]))
except Exception:
    pass
# ⭐ SÜRE MODELİ TAZELİĞİ — tahminin temeli. Bayatlarsa tahmin dünkü trafiği anlatır.
try:
    oku = lambda a: (k.execute("SELECT deger FROM durum WHERE anahtar=?", (a,)).fetchone()
                     or [None])[0]
    kurulum, veri_sonu = oku("sure_kurulum"), oku("sure_veri_sonu")
    if kurulum:
        yas = (datetime.now() - datetime.strptime(kurulum, "%Y-%m-%d %H:%M:%S")).total_seconds()/60
        im = "✅" if yas < 90 else "⚠️ "
        print("     süre modeli    : %s %s kuruldu (%.0f dk önce) · veri %s'e kadar"
              % (im, kurulum[11:16], yas, (veri_sonu or "—")[11:16]))
    else:
        print("     süre modeli    : ⚠️  hiç damgalanmamış (bir kez kur)")
except Exception:
    pass

# ⭐ ÇIKARIM VERİMİ — gecis / filo_konum (7 Eylül'de eklendi)
#
# ⚠️ NEDEN BURADA: bu oran 1 Eylül'de 0,80'den 0,50'ye düştü ve ALTI GÜN kimse
#    fark etmedi (Bölüm 63). Ham veri diskte duruyordu ama çıkarım göremiyordu;
#    hiçbir gösterge bunu söylemiyordu. Sessizce bozulan şey ölçülmeli.
#
#    0,80 civarı = sağlıklı · 0,60 altı = çıkarımda kayıp var, bak
try:
    from datetime import timedelta
    dun = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    fk = k.execute("SELECT COUNT(*) FROM filo_konum WHERE zaman LIKE ?", (dun+"%",)).fetchone()[0]
    gc = k.execute("SELECT COUNT(*) FROM gecis WHERE zaman LIKE ?", (dun+"%",)).fetchone()[0]
    if fk > 1000:
        v = gc / fk
        im = "✅" if v >= 0.70 else ("⚠️ " if v >= 0.55 else "⛔")
        print("     çıkarım verimi : %s %.2f  (dün · %s geçiş / %s konum · sağlıklı ≥0,70)"
              % (im, v, "{:,}".format(gc).replace(",", "."), "{:,}".format(fk).replace(",", ".")))
except Exception:
    pass
k.close()
PY
echo

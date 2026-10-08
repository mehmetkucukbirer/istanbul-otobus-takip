#!/bin/zsh
# İZLE — canlı takip ekranı. Her 20 saniyede kendini yeniler.
#   Çıkmak için Ctrl+C  (kaydediciyi DURDURMAZ, sadece izlemeyi bırakır)
cd "/Users/mehmetkucukbirer/otobus-takip"
trap 'print -P "\n%F{yellow}izleme bırakıldı — kaydedici çalışmaya devam ediyor%f\n"; exit 0' INT

while true; do
  clear
  print -P "%F{cyan}╔══════════════════════════════════════════════════════════════╗%f"
  print -P "%F{cyan}║%f  %BOTOBÜS TAKİP · CANLI İZLEME%b        $(date '+%d.%m.%Y %H:%M:%S')  %F{cyan}║%f"
  print -P "%F{cyan}╚══════════════════════════════════════════════════════════════╝%f"
  echo

  if pgrep -f "kaydedici.py" > /dev/null; then
    print -P "  %F{green}●%f KAYDEDİCİ ÇALIŞIYOR"
  else
    print -P "  %F{red}●%f KAYDEDİCİ DURMUŞ"
    print -P "    başlatmak için:  %F{yellow}nohup caffeinate -i python3 -u kaydedici.py >> veri/kaydedici.log 2>&1 &%f"
  fi
  # Arayüz sunucusu: süreç değil, CEVAP kontrol ediliyor (bkz. durum.sh)
  if curl -s -m 2 -o /dev/null "http://localhost:8790/" 2>/dev/null; then
    print -P "  %F{green}●%f arayüz sunucusu (8790)"
  else
    print -P "  %F{red}●%f arayüz sunucusu CEVAP VERMİYOR"
  fi
  pgrep -f "sabah_rutini.sh" >/dev/null && print -P "  %F{green}●%f sabah rutini bekliyor (09:00)"
  pgrep -f "gunluk.py"       >/dev/null && print -P "  %F{yellow}●%f günlük analiz şu an çalışıyor"
  pgrep -f "gecisler.py"     >/dev/null && print -P "  %F{yellow}●%f geçiş çıkarımı çalışıyor"

  if pmset -g batt | sed -n 2p | grep -q discharging; then
    print -P "  %F{yellow}●%f güç: PİLDE  $(pmset -g batt | grep -oE '[0-9]+%' | head -1)"
  else
    print -P "  %F{green}●%f güç: fişte  $(pmset -g batt | grep -oE '[0-9]+%' | head -1)"
  fi

  echo
  print -P "  %F{blue}── son turlar ─────────────────────────────────────────────%f"
  grep -E "^[0-9]{2}:" veri/kaydedici.log 2>/dev/null | tail -6 | sed 's/^/    /'

  echo
  print -P "  %F{blue}── veri ───────────────────────────────────────────────────%f"
  python3 - <<'PY' 2>/dev/null
import sqlite3
from datetime import datetime
k = sqlite3.connect("veri/kayit.db", timeout=8)
b = lambda n: "{:,}".format(n).replace(",", ".")
son = k.execute("SELECT MAX(zaman) FROM yoklama").fetchone()[0]
g = (datetime.now() - datetime.strptime(son, "%Y-%m-%d %H:%M:%S")).total_seconds()
bugun = datetime.now().strftime("%Y-%m-%d")
print("    son kayıt      : %s  (%.0f sn önce)  %s"
      % (son[11:], g, "✅" if g < 180 else "⚠️  AKIŞ DURMUŞ"))
print("    toplam konum   : %s" % b(k.execute("SELECT COUNT(*) FROM filo_konum").fetchone()[0]))
print("    bugün eklenen  : %s" % b(k.execute(
    "SELECT COUNT(*) FROM filo_konum WHERE zaman >= ?", (bugun,)).fetchone()[0]))
print("    durak geçişi   : %s" % b(k.execute("SELECT COUNT(*) FROM gecis").fetchone()[0]))
print("    süre modeli    : %s parça-saat" % b(
    k.execute("SELECT COUNT(*) FROM parca_sure").fetchone()[0]))
r = k.execute("SELECT COUNT(*), SUM(sonuc='ok') FROM yoklama WHERE zaman >= ?", (bugun,)).fetchone()
if r[0]:
    print("    bugünkü istek  : %d  (%d başarılı · %%%.0f)" % (r[0], r[1] or 0, 100.0*(r[1] or 0)/r[0]))
dk = k.execute("SELECT COUNT(DISTINCT substr(zaman,12,5)) FROM yoklama WHERE zaman >= ?",
               (bugun,)).fetchone()[0]
gecen = (datetime.now() - datetime.strptime(bugun, "%Y-%m-%d")).total_seconds()/60
print("    bugün kapsama  : %d / %d dakika  (%%%.0f)" % (dk, gecen, 100.0*dk/gecen))
k.close()
PY
  echo
  print -P "  %F{242}Ctrl+C ile çık · kaydedici etkilenmez · 20 sn'de bir yenilenir%f"
  sleep 20
done

#!/bin/zsh
# GEÇİŞ DÖNGÜSÜ — geçiş çıkarımını sürekli taze tutar.
#
# ⚠️ NEDEN VAR (1 Eylül): gecis tablosu yalnızca günlük rutin çalışınca (09:00)
#    güncelleniyordu. Gün boyunca "son geçiş" saatler öncesini gösteriyor, bu
#    yüzden uygulamada HER HAT "gecikti" diyordu. Gözlem katmanı ancak taze
#    veriyle anlamlı.
cd "/Users/mehmetkucukbirer/otobus-takip"
LOG="veri/gecis_dongusu.log"
echo "[$(date '+%d.%m %H:%M')] geçiş döngüsü başladı · her 10 dakikada bir" >> "$LOG"
while true; do
  BAS=$(date +%s)

  # ⚠️ ZAMAN AŞIMI KORUMASI (2 Eylül): dört döngü de 13:54 civarında SESSİZCE durdu.
  #    Süreçler ayaktaydı, sleep çocukları görünüyordu ama PID'leri değişmiyordu —
  #    yani döngü dönmüyordu. Kök sebep bulunamadı (sistem uyumamış, kayit.db WAL
  #    kipinde). Sebep bilinmese de çare belli: asılan adım öldürülüp döngü sürsün.
  #    macOS'ta `timeout` komutu yok, bekçi süreç deseni kullanılıyor.
    python3 -u gecisler.py >> "$LOG" 2>&1 &
  IS=$!
  ( sleep 1200; kill -9 $IS 2>/dev/null ) &
  BEKCI=$!
  wait $IS 2>/dev/null
  DURUM=$?
  kill $BEKCI 2>/dev/null; wait $BEKCI 2>/dev/null
  if [[ $DURUM -ne 0 ]]; then
    echo "[$(date '+%d.%m %H:%M')] ⚠️ tur başarısız/zaman aşımı (kod $DURUM)" >> "$LOG"
  fi

  SURE=$(( $(date +%s) - BAS ))
  echo "[$(date '+%d.%m %H:%M')] tur bitti · ${SURE} sn" >> "$LOG"
  # tur uzun sürdüyse hemen tekrar başlama; en az 10 dakika ara ver
  sleep $(( 600 > SURE ? 600 - SURE : 60 ))
done

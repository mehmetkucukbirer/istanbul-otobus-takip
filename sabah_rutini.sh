#!/bin/zsh
# SABAH RUTİNİ — HER GÜN belirlenen saatte günlük analizi çalıştırır.
# ⚠️ İlk sürüm tek seferlikti: bir kez koşup ölüyordu, ertesi gün elle yeniden
#    kurmak gerekiyordu ve iki kez unutuldu. Artık sonsuz döngü.
cd "/Users/mehmetkucukbirer/otobus-takip"
HEDEF=${1:-09:00}
LOG="veri/sabah_rutini.log"
echo "[$(date '+%d.%m %H:%M')] sabah rutini kuruldu (kalıcı) · her gün $HEDEF" >> "$LOG"
while true; do
  while [[ "$(date '+%H:%M')" != "$HEDEF" ]]; do sleep 40; done
  echo "[$(date '+%d.%m %H:%M')] başlıyor" >> "$LOG"
  python3 -u gunluk.py "$(date -v-1d '+%Y%m%d')" >> "$LOG" 2>&1
  echo "[$(date '+%d.%m %H:%M')] bitti" >> "$LOG"
  sleep 90        # aynı dakikada iki kez tetiklenmesin
done

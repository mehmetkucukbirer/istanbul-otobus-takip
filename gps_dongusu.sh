#!/bin/zsh
# GPS KARANLIĞI İDDİA DÖNGÜSÜ — 10 dakikada bir tarar ve iddiaları KAYDEDER.
#
# ⚠️ NEDEN VAR: `yoldaki_gorunmeyenler()` (Bölüm 51) "bu kalkış yolda ama konum
#    bildirmiyor" diyor, ama bu iddia istek geldiğinde hesaplanıp UÇUYOR.
#    Yarın arşiv indiğinde kıyaslanacak hiçbir kayıt kalmıyor.
#
#    `yoklama` tablosu dersinin aynısı (Bölüm 7): ölçmediğin şeyi sonradan
#    doğrulayamazsın. Tahmin, VERİLDİĞİ ANDA yazılmalı.
#
# MALİYET: tam tarama 12 saniye ölçüldü (775 hat). Kotadan istek harcamıyor.
# DOĞRULAMA: ertesi sabah gunluk.py 5/5 adımı arşivle kıyaslar.
cd "/Users/mehmetkucukbirer/otobus-takip"
LOG="veri/gps_dongusu.log"
echo "[$(date '+%d.%m %H:%M')] gps karanlığı döngüsü başladı · 10 dakikada bir" >> "$LOG"
while true; do
  BAS=$(date +%s)

  # ⚠️ ZAMAN AŞIMI KORUMASI (2 Eylül): dört döngü de 13:54 civarında SESSİZCE durdu.
  #    Süreçler ayaktaydı, sleep çocukları görünüyordu ama PID'leri değişmiyordu —
  #    yani döngü dönmüyordu. Kök sebep bulunamadı (sistem uyumamış, kayit.db WAL
  #    kipinde). Sebep bilinmese de çare belli: asılan adım öldürülüp döngü sürsün.
  #    macOS'ta `timeout` komutu yok, bekçi süreç deseni kullanılıyor.
    python3 -u gps_izleyici.py >> "$LOG" 2>&1 &
  IS=$!
  ( sleep 300; kill -9 $IS 2>/dev/null ) &
  BEKCI=$!
  wait $IS 2>/dev/null
  DURUM=$?
  kill $BEKCI 2>/dev/null; wait $BEKCI 2>/dev/null
  if [[ $DURUM -ne 0 ]]; then
    echo "[$(date '+%d.%m %H:%M')] ⚠️ tur başarısız/zaman aşımı (kod $DURUM)" >> "$LOG"
  fi

  SURE=$(( $(date +%s) - BAS ))
  sleep $(( 600 > SURE ? 600 - SURE : 60 ))
done

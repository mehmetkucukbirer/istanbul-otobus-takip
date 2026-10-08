#!/bin/zsh
# DUYURU DÖNGÜSÜ — İETT sefer iptali akışını sürekli yakalar.
#
# ⚠️ NEDEN VAR (1 Eylül): GetDuyurular_json arşiv tutmuyor, KAYAN PENCERE veriyor —
#    14:29'da bakıldığında yalnızca 14:00-16:12 arası iptaller vardı, sabahkiler
#    gitmişti. Yoklamazsak veri kalıcı olarak kayboluyor.
#
# ⚠️⚠️ ZAMAN AŞIMI KORUMASI (2 Eylül'de eklendi — 70 DAKİKALIK SESSİZ KAYIP):
#    Pil bitip makine uyandıktan sonra ağ oynarken `duyurular.py` bir yerde asılı
#    kaldı ve DÖNGÜYÜ KİLİTLEDİ. Belirti sinsiydi: süreç ayaktaydı, `sleep 600`
#    çocuğu görünüyordu, ama PID'i hiç değişmiyordu — yani döngü dönmüyordu.
#    13:53'ten 15:05'e kadar hiç yoklama yapılmadı ve günlüğe tek satır düşmedi.
#
#    Python'un kendi `urlopen(timeout=45)` koruması yetmedi; DNS/soket katmanında
#    daha derinde takıldı. Bu yüzden koruma KABUK düzeyinde: 120 saniyede
#    bitmezse süreç öldürülür ve döngü devam eder.
#    macOS'ta `timeout` komutu yok, o yüzden bekçi süreç deseni kullanılıyor.
#
# KOTA: 10 dakikada bir = saatte 6 istek. Her yoklama `yoklama` tablosuna yazılır;
#    kaydedici.py bütçesini o tablodan okuduğu için harcamayı görüp kendi hat
#    sorgularını kendiliğinden kısar.
cd "/Users/mehmetkucukbirer/otobus-takip"
LOG="veri/duyuru_dongusu.log"
ZAMAN_ASIMI=120

echo "[$(date '+%d.%m %H:%M')] duyuru döngüsü başladı · her 10 dakikada bir" >> "$LOG"
while true; do
  BAS=$(date +%s)

  python3 -u duyurular.py >> "$LOG" 2>&1 &
  IS=$!
  ( sleep $ZAMAN_ASIMI; kill -9 $IS 2>/dev/null ) &
  BEKCI=$!
  wait $IS 2>/dev/null
  DURUM=$?
  kill $BEKCI 2>/dev/null; wait $BEKCI 2>/dev/null

  if [[ $DURUM -ne 0 ]]; then
    echo "[$(date '+%d.%m %H:%M')] ⚠️ tur başarısız/zaman aşımı (kod $DURUM) — döngü sürüyor" >> "$LOG"
  fi

  SURE=$(( $(date +%s) - BAS ))
  sleep $(( 600 > SURE ? 600 - SURE : 60 ))
done

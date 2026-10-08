#!/bin/zsh
# MODEL DÖNGÜSÜ — süre modelini saat başı tazeler.
#
# ⚠️ NEDEN VAR (1 Eylül, Mehmet'in tespiti): süre modeli GÜNDE YALNIZCA BİR KEZ
#    kuruluyordu (sabah_rutini.sh, 09:00). Ham veri dakikada bir akıyor, geçişler
#    10 dakikada bir çıkarılıyor, ama tahminin temeli olan parça tablosu 24 saat
#    donuk kalıyordu. Ölçüldü: 1 Eylül 15:50'de model 31 Ağustos verisiyle
#    çalışıyordu — o gün çıkarılmış 1.346.218 geçişin hiçbiri tahmine girmiyordu.
#
#    "her geçen gün daha sağlam tahmin" ancak model veriyi GÖRÜRSE olur.
#
# MALİYET: tam kurulum 2 dk 11 sn ölçüldü (674 hat · 850 bin parça-saat).
#    Saatin %3'ü. Kotadan istek harcamıyor — tamamen yerel hesap.
#
# ⚠️ KİLİT: gecisler.py uzun yazma yaparken kaydediciyi öldürmüştü (Bölüm 31).
#    sure_modeli.kur() busy_timeout=120000 ile açıyor ve 50 hatta bir commit
#    ediyor; kilidi uzun tutmuyor.
#
# ⭐ HAVUZ BESLEMESİ EKLENDİ (4 Eylül · Bölüm 61 madde 3).
#    sure_modeli.kur() artık ham `gecis` yerine `parca_havuz`dan besleniyor
#    (Bölüm 60). Havuz elle doldurulduğu sürece model, en son elle çalıştırılan
#    ana kadarki veriyi görüyordu — yani "saat başı tazeleme" yalanı oluyordu.
#    Bu yüzden besleme, kurulumdan ÖNCE ve aynı turda çalışmak zorunda.
#
#    SIRA ÖNEMLİ:  parca_havuz doldur  →  sure_modeli kur
#    Ölçüldü (4 Eylül): besleme 83 sn (2 saatlik veri) · kurulum ~131 sn.
#    Saat başı çalışınca besleme ~45 sn olacak. Toplam ~3 dk, bekçi sınırı 15 dk.
#
#    ⚠️ İKİSİ AYRI BEKÇİYLE: besleme çökerse model yine de kurulsun — eski
#    havuzla kurulan model, hiç kurulmayan modelden iyidir.
cd "/Users/mehmetkucukbirer/otobus-takip"
LOG="veri/model_dongusu.log"

# Bir adımı bekçi süreçle çalıştırır: 900 sn içinde bitmezse öldürür, döngü sürer.
# ⚠️ macOS'ta `timeout` komutu yok — bekçi süreç deseni bunun yerini tutuyor.
bekcili() {
  local ETIKET=$1; shift
  "$@" >> "$LOG" 2>&1 &
  local IS=$!
  ( sleep 900; kill -9 $IS 2>/dev/null ) &
  local BEKCI=$!
  wait $IS 2>/dev/null
  local DURUM=$?
  kill $BEKCI 2>/dev/null; wait $BEKCI 2>/dev/null
  if [[ $DURUM -ne 0 ]]; then
    echo "[$(date '+%d.%m %H:%M')] ⚠️ $ETIKET başarısız/zaman aşımı (kod $DURUM)" >> "$LOG"
  fi
  return $DURUM
}
echo "[$(date '+%d.%m %H:%M')] model döngüsü başladı · saat başı" >> "$LOG"
while true; do
  # bir sonraki saat başına kadar bekle (rutinlerle çakışmasın diye 12. dakikada)
  SIMDI=$(date +%s)
  HEDEF=$(( (SIMDI / 3600 + 1) * 3600 + 720 ))
  sleep $(( HEDEF - SIMDI ))
  BAS=$(date +%s)
  echo "[$(date '+%d.%m %H:%M')] tazeleniyor…" >> "$LOG"

  # ⚠️ ZAMAN AŞIMI KORUMASI (2 Eylül): dört döngü de 13:54 civarında SESSİZCE durdu.
  #    Süreçler ayaktaydı, sleep çocukları görünüyordu ama PID'leri değişmiyordu —
  #    yani döngü dönmüyordu. Kök sebep bulunamadı (sistem uyumamış, kayit.db WAL
  #    kipinde). Sebep bilinmese de çare belli: asılan adım öldürülüp döngü sürsün.
  #    macOS'ta `timeout` komutu yok, bekçi süreç deseni kullanılıyor.
  bekcili "havuz beslemesi" python3 -u parca_havuz.py doldur --sessiz
  bekcili "süre modeli"     python3 -u sure_modeli.py kur

  echo "[$(date '+%d.%m %H:%M')] bitti · $(( $(date +%s) - BAS )) sn" >> "$LOG"
done

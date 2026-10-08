#!/bin/zsh
# ─────────────────────────────────────────────────────────────────────────────
# GÖZCÜ — kaydedici ve tünel ölürse ayağa kaldırır
#
# ⭐ NEDEN VAR (4 Ekim): aynı arıza İKİ KEZ yaşandı (11 Eylül gecesi ve 4 Ekim
#   öğleden sonra). Ağ kesiliyor, iki servis de kendi başına toparlanamıyor:
#
#   KAYDEDİCİ üstel geri çekilmeye giriyor (180→300→600→1800 sn) ve TAVANDA
#   KİLİTLENİYOR. Ağ beş dakikada dönse bile 30 dakika uyuyor; uyanıp yine hata
#   alırsa 30 dakika daha. 4 Ekim'de 18:46→21:30 arası ÜÇ SAAT böyle geçti.
#
#   TÜNEL koptuğunda cloudflared yeniden bağlanmayı deniyor ama Cloudflare
#   ücretsiz tünelin kaydını silmiş oluyor: "Unauthorized: Tunnel not found".
#   Süreç ÖLMEDİĞİ için launchd de yeniden başlatmıyor — sonsuza kadar boşa
#   deniyor. Tek çare dışarıdan yeniden başlatmak (yeni adres alır).
# ─────────────────────────────────────────────────────────────────────────────
cd "$(dirname "$0")" || exit 1
PERIYOT=300          # 5 dakika
VERI_ESIK_DK=10      # kaydedici bu kadar süre yazmadıysa ölmüş sayılır
LOG=veri/gozcu.log

yaz() { print -r -- "$(date '+%d.%m %H:%M:%S')  $1" >> $LOG }

yaz "gözcü başladı · periyot ${PERIYOT}sn · veri eşiği ${VERI_ESIK_DK}dk"

while true; do
  # ⚠️ ÖNCE İNTERNET: ağ gerçekten yoksa yeniden başlatmanın faydası yok,
  #    sadece günlüğü şişirir ve servisleri boşuna sarsar.
  if ! curl -s -m 10 -o /dev/null https://www.google.com 2>/dev/null; then
    yaz "internet yok — müdahale edilmiyor"
    sleep $PERIYOT; continue
  fi

  # ── 1) KAYDEDİCİ: son kayıt ne kadar eski?
  yas=$(/usr/bin/python3 - <<'PY' 2>/dev/null
import sqlite3
from datetime import datetime
try:
    k = sqlite3.connect("file:veri/kayit.db?mode=ro", uri=True)
    r = k.execute("SELECT MAX(zaman) FROM filo_konum").fetchone()
    if r and r[0]:
        print(int((datetime.now() - datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")).total_seconds() // 60))
    else:
        print(9999)
except Exception:
    print(-1)
PY
)
  if [[ "$yas" =~ '^[0-9]+$' ]] && (( yas > VERI_ESIK_DK )); then
    yaz "⚠️ kaydedici ${yas} dk'dır yazmıyor — yeniden başlatılıyor"
    launchctl kickstart -k "gui/$(id -u)/otobus.kaydedici" 2>>$LOG
  fi

  # ── 2) TÜNEL: dışarıdan cevap veriyor mu?
  # ⚠️ Kontrol YEREL sunucuya değil TÜNEL ADRESİNE yapılıyor: yerel sunucu
  #    gayet ayakta olup tünel kopuk olabilir — 4 Ekim'de tam bu oldu.
  url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' veri/tunel.log 2>/dev/null | tail -1)
  if [[ -n "$url" ]]; then
    kod=$(curl -s -m 20 -o /dev/null -w "%{http_code}" "$url/saglik" 2>/dev/null)
    if [[ "$kod" != "200" ]]; then
      yaz "⚠️ tünel cevap vermiyor (HTTP ${kod:-yok}) — yeniden başlatılıyor"
      launchctl kickstart -k "gui/$(id -u)/otobus.tunel" 2>>$LOG
      # Yeni adresin Cloudflare'de oturmasını bekle — sonra panoya hemen as,
      # yoksa dışarıdaki telefon bir sonraki tura (5 dk) kadar beklerdi.
      sleep 45
    fi
  fi

  # ── 3) ADRES PANOSU (8 Ekim · pano.py): adres değiştiyse ya da son ilan
  #    6 saatten eskiyse imzalı ilanı yeniden as. Sağlıksız adres asılmaz.
  sonuc=$(/usr/bin/python3 pano.py 2>&1 | tail -1)
  [[ "$sonuc" == asıldı* ]] && yaz "📌 pano: $sonuc"
  [[ "$sonuc" == *Error* || "$sonuc" == *Traceback* ]] && yaz "⚠️ pano: $sonuc"

  sleep $PERIYOT
done

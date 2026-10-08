#!/bin/zsh
# LAUNCHD KURULUMU — arka plan süreçlerini macOS'un kendi servis yöneticisine devreder.
#
# ⚠️⚠️ NEDEN (3 Eylül): ÜÇ GÜNDE ÜÇ AYRI SEBEPLE VERİ KAYBEDİLDİ.
#     1 Eyl gece  pil bitti                → 2 saat  6 dk kayıp
#     2 Eyl öğlen döngüler sessizce durdu  →     70 dk kayıp
#     3 Eyl gece  disk doldu, süreç öldü   → 7 saat     kayıp
#
#     Ortak sebep: süreçler `nohup ... &` ile ELLE başlatılıyordu. Öldüklerinde
#     kimse haberdar olmuyor, makine kapanınca geri gelmiyorlar.
#     launchd oturum açılınca kendisi başlatır, çökerlerse KeepAlive ile geri
#     getirir. Koddaki zaman aşımı kalkanları (Bölüm 55) duruyor; bu ikinci ağ.
#
# ⭐ SABAH RUTİNİ AYRICA KAZANIYOR: `while` döngüsü yerine StartCalendarInterval.
#    3 Eylül 09:00'da makine uykudaydı ve rutin HİÇ ÇALIŞMADI. launchd kaçırılan
#    takvim işini makine uyanınca çalıştırır — o kayıp bir daha yaşanmaz.
#
# ⚠️ KURULUMDA İKİ KEZ TÖKEZLENDİ, İKİSİ DE AYNI SEBEPTEN — proje klasörünün
#    adında BOŞLUK var ("mobil otobüsüm nerede"):
#      1) Tam yol yazıp ProgramArguments'ı boşluktan bölmek → yol üç parçaya
#         ayrıldı, hepsi "çıkış 127" verdi.
#      2) Göreli ada geçmek → `WorkingDirectory` spawn anında uygulanmadığı için
#         zsh dosyayı bulamadı: "can't open input file: gecis_dongusu.sh".
#    ÇÖZÜM: her servis `/bin/zsh -c "cd <proje> && exec ..."` biçiminde, TEK
#    parça komut dizesiyle çalışıyor. Bölünecek bir şey kalmıyor, `cd` da
#    launchd'ye değil kabuğa ait oluyor.
#
# KULLANIM:
#     ./launchd_kur.sh          kur ve başlat
#     ./launchd_kur.sh durum    ne çalışıyor
#     ./launchd_kur.sh durdur   hepsini durdur ve kaldır

PROJE="/Users/mehmetkucukbirer/otobus-takip"
AJAN="$HOME/Library/LaunchAgents"
PY="/usr/bin/python3"
ONEK="otobus"
mkdir -p "$AJAN" "$PROJE/veri"

# etiket · kabukta çalışacak komut · günlük dosyası
typeset -A KOMUT LOG
KOMUT[kaydedici]="exec /usr/bin/caffeinate -i $PY -u kaydedici.py"
KOMUT[gecis]="exec /bin/zsh gecis_dongusu.sh"
KOMUT[duyuru]="exec /bin/zsh duyuru_dongusu.sh"
KOMUT[model]="exec /bin/zsh model_dongusu.sh"
KOMUT[gps]="exec /bin/zsh gps_dongusu.sh"
KOMUT[arayuz]="exec $PY -u arayuz_sunucu.py"
LOG[kaydedici]="veri/kaydedici.log"
LOG[gecis]="veri/launchd_gecis.log"
LOG[duyuru]="veri/launchd_duyuru.log"
LOG[model]="veri/launchd_model.log"
LOG[gps]="veri/launchd_gps.log"
LOG[arayuz]="veri/arayuz.log"
SIRA=(kaydedici gecis duyuru model gps arayuz)

plist_yaz() {   # $1 etiket · $2 kabuk-komutu · $3 günlük · $4 ek-xml
  cat > "$AJAN/$ONEK.$1.plist" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$ONEK.$1</string>
    <key>ProgramArguments</key><array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>cd '$PROJE' &amp;&amp; $2</string>
    </array>
    <key>StandardOutPath</key><string>$PROJE/$3</string>
    <key>StandardErrorPath</key><string>$PROJE/$3</string>
    <key>ThrottleInterval</key><integer>30</integer>
    <!-- ⚠️⚠️ ProcessType (3 Eylül): launchd, tür belirtilmezse süreci ARKA PLAN
         işi sayar ve DİSK ERİŞİMİNİ KISITLAR (I/O throttling). 7 GB'lık
         veritabanından okuyan sunucu bu yüzden launchd altında asılıyor,
         istekler 60 sn'de zaman aşımına uğruyordu — elle çalıştırıldığında
         aynı istek 0,07 sn. Fark tamamen bu ayardan.
         "Interactive" = kullanıcı bekliyor, kısıtlama. -->
    <key>ProcessType</key><string>Interactive</string>
    <!-- ⚠️⚠️ DOSYA SINIRI (3 Eylül): launchd servislere VARSAYILAN 256 dosya
         sınırı koyuyor; giriş kabuğunda bu sınır 1.048.576. Fark ölçüldü.
         Arayüz sunucusu her istekte veritabanı bağlantısı + rota dosyası +
         ağ soketi açıyor, 256'ya dayanınca çöküyordu:
             OSError: [Errno 24] Too many open files
         Elle `nohup` ile başlatılırken hiç yaşanmadı — sorun launchd'ye
         geçince ortaya çıktı, çünkü sınır oradan geliyor. -->
    <key>SoftResourceLimits</key><dict>
        <key>NumberOfFiles</key><integer>8192</integer>
    </dict>
    <key>EnvironmentVariables</key><dict>
        <key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
$4
</dict>
</plist>
XML
  echo "   yazıldı  $ONEK.$1.plist"
}

yukle() {
  launchctl bootout "gui/$UID/$ONEK.$1" 2>/dev/null
  launchctl bootstrap "gui/$UID" "$AJAN/$ONEK.$1.plist" 2>&1 | grep -v "^$" || true
}

case "${1:-kur}" in
durdur)
  for e in $SIRA sabah; do
    launchctl bootout "gui/$UID/$ONEK.$e" 2>/dev/null
    rm -f "$AJAN/$ONEK.$e.plist"; echo "   kaldırıldı $ONEK.$e"
  done ;;

durum)
  printf "   %-20s %8s %10s\n" "servis" "PID" "son-çıkış"
  for e in $SIRA sabah; do
    s=$(launchctl list | awk -v L="$ONEK.$e" '$3==L {printf "%s %s",$1,$2}')
    [[ -z "$s" ]] && s="- yüklü-değil"
    printf "   %-20s %8s %10s\n" "$ONEK.$e" ${=s}
  done ;;

*)
  echo "── elle başlatılmış eski süreçler durduruluyor ──"
  pkill -f "kaydedici.py" 2>/dev/null
  pkill -f "_dongusu.sh" 2>/dev/null
  pkill -f "sabah_rutini.sh" 2>/dev/null
  pkill -f "arayuz_sunucu.py" 2>/dev/null
  sleep 3

  echo "── plist yazılıyor ──"
  for e in $SIRA; do
    plist_yaz "$e" "${KOMUT[$e]}" "${LOG[$e]}" \
"    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>"
  done
  # Takvim işi: RunAtLoad YOK, kurulur kurulmaz koşmasın.
  plist_yaz "sabah" "exec $PY -u gunluk.py" "veri/sabah_rutini.log" \
"    <key>StartCalendarInterval</key><dict>
        <key>Hour</key><integer>9</integer>
        <key>Minute</key><integer>0</integer>
    </dict>"

  echo "── yükleniyor ──"
  for e in $SIRA sabah; do yukle "$e"; echo "   yüklendi $ONEK.$e"; done ;;
esac

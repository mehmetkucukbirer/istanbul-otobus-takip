import SwiftUI

/// Sunucu adresi. Veri Mehmet'in bilgisayarındaki Python sunucusundan geliyor;
/// telefon ile bilgisayar aynı Wi-Fi'de olmalı.
struct AyarlarGorunumu: View {
    @Environment(\.dismiss) private var kapat
    @State private var adres = Servis.shared.sunucu
    @State private var anahtar = Servis.shared.anahtar
    @State private var tercihler = Tercihler.shared

    var body: some View {
        NavigationStack {
            ZStack {
                Tema.zemin.ignoresSafeArea()
                VStack(alignment: .leading, spacing: 14) {
                    Text("SUNUCU ADRESİ").font(Tema.kucukEtiket()).tracking(1.4)
                        .foregroundStyle(Tema.soluk)
                    TextField("http://10.0.0.5:8790", text: $adres)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .foregroundStyle(Tema.ink)
                        .padding(12)
                        .background(Tema.kart, in: .rect(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Tema.cizgi))

                    Text("ERİŞİM ANAHTARI").font(Tema.kucukEtiket()).tracking(1.4)
                        .foregroundStyle(Tema.soluk)
                        .padding(.top, 6)
                    // ⚠️ SecureField: anahtar omuz üstünden okunmasın. Kopyala-yapıştır
                    //    çalışıyor, elle yazmak gerekmiyor.
                    SecureField("bilgisayardaki veri/anahtar.txt", text: $anahtar)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .foregroundStyle(Tema.ink)
                        .padding(12)
                        .background(Tema.kart, in: .rect(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Tema.cizgi))

                    Text("""
                    Veri, bilgisayarındaki sunucudan geliyor. Anahtar o bilgisayarda \
                    veri/anahtar.txt dosyasında duruyor; terminalde şununla görürsün:

                    cat ~/otobus-takip/veri/anahtar.txt

                    Adres varsayılan olarak bilgisayarın ağ adıdır (.local) — IP \
                    değişse bile çalışır. Sorun olursa IP'yi öğrenmek için: \
                    ipconfig getifaddr en0
                    """)
                    .font(.system(size: 13)).foregroundStyle(Tema.soluk)

                    Divider().overlay(Tema.cizgi).padding(.vertical, 4)

                    // ⚠️ Araç kodu / anlık hız / durak sırası yolcuya bir şey
                    //    söylemiyor ama GELİŞTİRİRKEN gerekiyor: tahminleri ham
                    //    veriyle karşılaştırmak için (Bölüm 62-63 doğrulamaları).
                    //    Silmek yerine buraya bağlandı, varsayılan kapalı.
                    Text("GÖSTERİM").font(Tema.kucukEtiket()).tracking(1.4)
                        .foregroundStyle(Tema.soluk)
                    Toggle(isOn: $tercihler.ayrintili) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Ayrıntılı gösterim")
                                .font(.system(size: 15)).foregroundStyle(Tema.ink)
                            Text("araç kodu, anlık hız ve durak sırası")
                                .font(.system(size: 12)).foregroundStyle(Tema.soluk)
                        }
                    }
                    .tint(Tema.mavi)
                    .padding(12)
                    .background(Tema.kart, in: .rect(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(Tema.cizgi))

                    Spacer()
                }
                .padding(16)
            }
            .navigationTitle("Ayarlar")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Kaydet") {
                        Servis.shared.sunucu = adres.trimmingCharacters(in: .whitespaces)
                        Servis.shared.anahtar = anahtar.trimmingCharacters(in: .whitespacesAndNewlines)
                        kapat()
                    }.tint(Tema.mavi)
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Vazgeç") { kapat() }.tint(Tema.soluk)
                }
            }
        }
    }
}

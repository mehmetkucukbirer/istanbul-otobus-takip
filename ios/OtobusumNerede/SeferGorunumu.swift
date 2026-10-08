import SwiftUI

/// SEFER TABLOSU — günün tüm seferleri, durumlarına göre renkli.
///
/// ⭐ NEDEN VAR (10 Eylül, Mehmet'in isteği):
///   *"tüm sefer saatleri gözükecek, tablo şeklinde. Hangileri çıktıysa bittiyse
///     başka bir renk, yoldakiler başka renk, GPS kapalı olanlar başka renk."*
///
/// ⚠️⚠️ TABLO YALNIZCA TARİFEYE DAYANAMAZ. Ölçüldü (10 Eylül): 98/D tarifesinde
/// bu durak için gün boyu 6 kalkış var ama 16 araç geçti (Bölüm 21). Sadece
/// tarifeye baksaydık günün üçte ikisi ekranda hiç görünmezdi. Tablo iki kaynağı
/// birleştiriyor: tarife satırları + tarifede karşılığı olmayan gerçek geçişler.
struct SeferGorunumu: View {
    let hat: String
    let yon: String
    let durakKodu: String

    @State private var tablo: HatSeferleri?
    @State private var hata: String?
    @State private var yukleniyor = true
    /// Seçili gün. nil = bugün. Geriye GECMIS_GUN kadar bakılabiliyor.
    @State private var secilenGun: Date = Date()
    @Environment(\.dismiss) private var kapat

    var body: some View {
        ZStack(alignment: .top) {
            Tema.zemin.ignoresSafeArea()
            VStack(spacing: 0) {
                baslik
                tarihSeridi
                if yukleniyor {
                    Spacer(); ProgressView().tint(Tema.mavi); Spacer()
                } else if let t = tablo {
                    ScrollView {
                        VStack(spacing: 12) {
                            if t.tarife_eksik == true { tarifeUyarisi(t) }
                            sayimSeridi(t)
                            tabloKarti(t)
                        }
                        .padding(14)
                    }
                    .scrollIndicators(.hidden)
                } else {
                    Spacer()
                    Text(hata ?? "Bu hattın sefer bilgisi alınamadı.")
                        .font(.callout).foregroundStyle(Tema.soluk)
                        .multilineTextAlignment(.center).padding(.horizontal, 40)
                    Spacer()
                }
            }
        }
        .ignoresSafeArea(edges: .top)
        .navigationBarBackButtonHidden()
        .task { await getir() }
    }

    /// ⚠️ GERİYE 14 GÜN: ham `gecis` verisi o kadar saklanıyor
    /// (kaydedici.GECIS_SAKLAMA_GUN = 14, Bölüm 63.5). Daha geriye gitmek boş
    /// tablo gösterirdi — olmayan veriyi sunmak yerine sınır konuldu.
    private static let gecmisGun = 14

    private var gunler: [Date] {
        let t = Calendar.current.startOfDay(for: Date())
        return (0..<Self.gecmisGun).compactMap {
            Calendar.current.date(byAdding: .day, value: -$0, to: t)
        }
    }

    private var tarihSeridi: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 7) {
                ForEach(gunler, id: \.self) { g in
                    let secili = Calendar.current.isDate(g, inSameDayAs: secilenGun)
                    Button {
                        secilenGun = g
                        Task { await getir() }
                    } label: {
                        VStack(spacing: 2) {
                            Text(gunAdi(g))
                                .font(.system(size: 10, weight: .medium))
                                .foregroundStyle(secili ? .white : Tema.soluk)
                            Text(gunSayisi(g))
                                .font(Tema.rakam(15))
                                .foregroundStyle(secili ? .white : Tema.ink)
                        }
                        .frame(width: 46)
                        .padding(.vertical, 8)
                        .background(secili ? Tema.mavi : Tema.kart, in: .rect(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10)
                            .stroke(secili ? .clear : Tema.cizgi))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 14).padding(.vertical, 10)
        }
        .background(Tema.zemin)
    }

    private func gunAdi(_ g: Date) -> String {
        if Calendar.current.isDateInToday(g) { return "bugün" }
        if Calendar.current.isDateInYesterday(g) { return "dün" }
        let b = DateFormatter()
        b.locale = Locale(identifier: "tr_TR"); b.dateFormat = "EEE"
        return b.string(from: g).lowercased()
    }

    private func uzunTarih(_ g: Date) -> String {
        let b = DateFormatter()
        b.locale = Locale(identifier: "tr_TR"); b.dateFormat = "d MMMM"
        return b.string(from: g)
    }

    private func gunSayisi(_ g: Date) -> String {
        let b = DateFormatter(); b.dateFormat = "d"
        return b.string(from: g)
    }

    private var baslik: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 9) {
                Button { kapat() } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 17, weight: .semibold)).foregroundStyle(.white)
                }
                Text(hat)
                    .font(.system(size: 15, weight: .heavy)).foregroundStyle(.white)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .background(.white.opacity(0.22), in: .rect(cornerRadius: 5))
                Spacer()
            }
            Text(Calendar.current.isDateInToday(secilenGun) ? "Bugünkü seferler"
                                                             : "\(uzunTarih(secilenGun)) seferleri")
                .font(.system(size: 25, weight: .bold)).foregroundStyle(.white)
                .padding(.top, 6).lineLimit(1).minimumScaleFactor(0.75)
            if let t = tablo {
                Text("\(t.durak_adi) · → \(t.hedef)")
                    .font(.system(size: 12)).foregroundStyle(.white.opacity(0.75)).lineLimit(1)
            }
        }
        .padding(.horizontal, 18).padding(.top, 58).padding(.bottom, 18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Tema.mavi)
        .clipShape(.rect(bottomLeadingRadius: 26, bottomTrailingRadius: 26))
    }

    /// ⚠️ Tarifenin eksikliği YOLCUYA SÖYLENİYOR: "tarifede 6 sefer var" bilgisi
    /// tek başına yanıltıcı olurdu.
    private func tarifeUyarisi(_ t: HatSeferleri) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 13)).foregroundStyle(Tema.turuncu)
            VStack(alignment: .leading, spacing: 3) {
                Text("Tarife bu hat için eksik")
                    .font(.system(size: 13, weight: .semibold)).foregroundStyle(Tema.ink)
                Text("Tarifede \(t.tarife_sayisi) kalkış var ama o gün \(t.gozlem_sayisi) "
                     + "araç geçti. Tabloda ikisi birlikte gösteriliyor.")
                    .font(.system(size: 12)).foregroundStyle(Tema.ink2)
            }
        }
        .padding(12).frame(maxWidth: .infinity, alignment: .leading)
        .background(Tema.turuncu.opacity(0.10), in: .rect(cornerRadius: 12))
    }

    /// Renk anahtarı + sayım — tablo okunmadan önce ne olduğunu özetliyor.
    private func sayimSeridi(_ t: HatSeferleri) -> some View {
        let sira: [(String, String)] = [("gecti", "geçti"), ("yolda", "yolda"),
                                        ("gps_yok", "GPS yok"), ("bekleniyor", "bekleniyor"),
                                        ("veri_yok", "veri yok")]
        return HStack(spacing: 8) {
            ForEach(sira, id: \.0) { anahtar, etiket in
                if let n = t.sayim[anahtar], n > 0 {
                    HStack(spacing: 5) {
                        Circle().fill(Self.renk(anahtar)).frame(width: 7, height: 7)
                        Text("\(n)").font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Tema.ink)
                        Text(etiket).font(.system(size: 11)).foregroundStyle(Tema.soluk)
                    }
                    .padding(.horizontal, 9).padding(.vertical, 7)
                    .background(Tema.kart, in: .rect(cornerRadius: 9))
                }
            }
            Spacer(minLength: 0)
        }
    }

    private func tabloKarti(_ t: HatSeferleri) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(t.satirlar.enumerated()), id: \.offset) { i, s in
                if i > 0 { Divider().overlay(Tema.cizgi).padding(.leading, 58) }
                satir(s)
            }
        }
        .background(Tema.kart, in: .rect(cornerRadius: 14))
    }

    private func satir(_ s: SeferSatiri) -> some View {
        let renk = Self.renk(s.durum)
        return HStack(spacing: 12) {
            // Sol: saat + durum rengi şeridi
            HStack(spacing: 8) {
                RoundedRectangle(cornerRadius: 2).fill(renk).frame(width: 3, height: 26)
                Text(s.kalkis)
                    .font(Tema.rakam(15))
                    .foregroundStyle(s.durum == "veri_yok" ? Tema.soluk : Tema.ink)
            }
            .frame(width: 62, alignment: .leading)

            Image(systemName: Self.simge(s.durum))
                .font(.system(size: 12)).foregroundStyle(renk).frame(width: 16)

            VStack(alignment: .leading, spacing: 1) {
                Text(Self.etiket(s.durum))
                    .font(.system(size: 13, weight: .medium)).foregroundStyle(renk)
                if let a = altYazi(s) {
                    Text(a).font(.system(size: 11)).foregroundStyle(Tema.soluk).lineLimit(1)
                }
            }
            Spacer(minLength: 0)
            if let dk = s.dakika {
                Text("\(dk) dk").font(Tema.rakam(15)).foregroundStyle(renk)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10)
    }

    private func altYazi(_ s: SeferSatiri) -> String? {
        switch s.durum {
        case "gecti":
            // Tarifede olmayan geçiş, tarifenin eksikliğinin kanıtı — belirtiliyor.
            return s.tarifede ? "tarifeye uydu" : "tarifede yok"
        case "gps_yok":
            return "tarifede var, otobüs görünmedi"
        case "veri_yok":
            // ⚠️ "GPS yok" DEĞİL: o saatte kaydedici çalışmıyordu, sefer yapılmış
            //    olabilir. Yanlış alarm vermemek için ayrı durum (PROMPT Bölüm 8).
            return "o saatte kayıt yapılamadı"
        case "yolda":
            return s.km.map { String(format: "%.1f km uzakta", $0) }
        default:
            return nil
        }
    }

    // ── Durum → renk / simge / etiket ────────────────────────────────────────
    // Renkler tema ile aynı dilde: yeşil olan oldu, mavi yolda, turuncu dikkat.

    static func renk(_ durum: String) -> Color {
        switch durum {
        case "gecti":      return Tema.yesil
        case "yolda":      return Tema.mavi
        case "gps_yok":    return Tema.turuncu
        case "bekleniyor": return Tema.soluk
        default:           return Tema.cizgi          // veri_yok — en sönük
        }
    }

    static func simge(_ durum: String) -> String {
        switch durum {
        case "gecti":      return "checkmark.circle.fill"
        case "yolda":      return "bus.fill"
        case "gps_yok":    return "exclamationmark.triangle.fill"
        case "bekleniyor": return "clock"
        default:           return "minus.circle"
        }
    }

    static func etiket(_ durum: String) -> String {
        switch durum {
        case "gecti":      return "geçti"
        case "yolda":      return "yolda"
        case "gps_yok":    return "GPS kapalı"
        case "bekleniyor": return "bekleniyor"
        default:           return "veri yok"
        }
    }

    private func getir() async {
        yukleniyor = true
        let b = DateFormatter(); b.dateFormat = "yyyy-MM-dd"
        let g = Calendar.current.isDateInToday(secilenGun) ? nil : b.string(from: secilenGun)
        do { tablo = try await Servis.shared.hatSeferleri(hat: hat, yon: yon,
                                                          durak: durakKodu, gun: g) }
        catch { hata = error.localizedDescription }
        yukleniyor = false
    }
}

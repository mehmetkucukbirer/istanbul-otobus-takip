import SwiftUI

/// Durak detayı — SAHADAKİ akıllı durak ekranının mobil karşılığı.
///
/// Ekranın düzeni birebir izleniyor:
///   mavi başlık        → yön + durak adı
///   bilgi çipleri      → tarih · saat · durak kodu
///   yeşil sütun başlığı→ HAT · HEDEF · VARIŞ
///   beyaz satırlar     → koyu lacivert rozet + hedef + dakika
///   turuncu şerit      → gecikme/uyarı
struct DurakGorunumu: View {
    let durak: Durak
    @State private var cevap: DurakCevabi?
    @State private var hata: String?
    @State private var yukleniyor = true
    private let saat = Timer.publish(every: 30, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            Tema.zemin.ignoresSafeArea()
            if yukleniyor && cevap == nil {
                ProgressView().tint(Tema.mavi)
            } else if let h = hata, cevap == nil {
                VStack(spacing: 10) {
                    Image(systemName: "wifi.exclamationmark").font(.system(size: 30))
                    Text(h).multilineTextAlignment(.center).font(.callout)
                }.foregroundStyle(Tema.soluk).padding(30)
            } else if let c = cevap {
                ScrollView {
                    VStack(spacing: 0) {
                        BaslikSeridi(cevap: c, durak: durak)
                        HatSeridi(hatlar: c.hatlar, durak: durak)
                        VStack(spacing: 10) {
                            ForEach(c.hatlar) { HatKarti(bilgi: $0, durak: durak) }
                            Text("30 saniyede bir yenilenir · İETT canlı verisi")
                                .font(Tema.kucukEtiket()).foregroundStyle(Tema.soluk)
                                .padding(.top, 4).padding(.bottom, 26)
                        }
                        .padding(.horizontal, 14).padding(.top, 14)
                    }
                }
                .refreshable { await yukle() }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(Tema.mavi, for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
        .task { await yukle() }
        .onReceive(saat) { _ in Task { await yukle(sessiz: true) } }
    }

    private func yukle(sessiz: Bool = false) async {
        if !sessiz { yukleniyor = true }
        do { cevap = try await Servis.shared.durak(durak.kod); hata = nil }
        catch { if !sessiz { hata = error.localizedDescription } }
        yukleniyor = false
    }
}

/// Ekranın tepesindeki mavi şerit: durak adı ve bilgi çipleri.
struct BaslikSeridi: View {
    let cevap: DurakCevabi
    let durak: Durak

    var body: some View {
        VStack(spacing: 12) {
            // İBB solda, İETT sağda — sahadaki ekranla aynı yerleşim
            HStack(alignment: .center) {
                IBBAmblemi(boyut: 40)
                Spacer()
                Text((cevap.ilce ?? "").uppercased())
                    .font(.system(size: 11, weight: .semibold)).tracking(1.6)
                    .foregroundStyle(.white.opacity(0.8))
                Spacer()
                IETTAmblemi(boyut: 44)
            }
            Text(cevap.ad)
                .font(.system(size: 27, weight: .bold))
                .foregroundStyle(.white)
                .multilineTextAlignment(.center)
                .lineLimit(2).minimumScaleFactor(0.7)
                .padding(.top, -2)

            HStack(spacing: 8) {
                Cip(ikon: "calendar", metin: Date.now.formatted(.dateTime.day().month().year()))
                Cip(ikon: "clock", metin: cevap.an)
                if let h = cevap.hava {
                    Cip(ikon: h.simge, metin: "\(h.sicaklik)°C")
                }
                // ⚠️ Şehir geneli trafik (10 Eylül). Tahmine GİRMİYOR — tahmin
                //    zaten otobüslerin kendi ölçülmüş hızından geliyor, o daha
                //    doğrudan bir sinyal. Bu çip yalnızca bağlam: "20 dakika
                //    normalden uzun mu?" sorusunun cevabı.
                if let t = cevap.trafik {
                    Cip(ikon: "car.fill", metin: t.durum)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 6).padding(.bottom, 18).padding(.horizontal, 16)
        .background(
            LinearGradient(colors: [Tema.mavi, Tema.mavi2],
                           startPoint: .top, endPoint: .bottom)
        )
        .shadow(color: .black.opacity(0.18), radius: 8, y: 3)
    }

    struct Cip: View {
        let ikon: String, metin: String
        var body: some View {
            HStack(spacing: 5) {
                // simgeler koyu turuncu, yazı beyaz — sahadaki ekranın vurgu rengi
                Image(systemName: ikon).font(.system(size: 11))
                    .foregroundStyle(Tema.turuncuKoyu)
                Text(metin).font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 10).padding(.vertical, 6)
            .background(.white.opacity(0.18), in: .rect(cornerRadius: 7))
        }
    }
}



/// Sahadaki ekranın tepesindeki yatay şeridin karşılığı:
/// tüm hatlar yan yana, sadece numara + hedef + kaç dakika kaldığı.
/// Yolcu ekrana bakınca ilk bunu görsün — hangi hat kaç dakika.
struct HatSeridi: View {
    let hatlar: [HatBilgisi]
    /// Araç detayına giderken "senin durağın" işaretlemesi için (10 Eylül).
    let durak: Durak

    private var cipler: [(HatBilgisi, Varis)] {
        hatlar.compactMap { h in seritVarisi(h).map { (h, $0) } }
    }

    var body: some View {
        // Gösterilecek gerçek varış yoksa şerit hiç çizilmiyor —
        // boş beyaz bant bozuk görünüyordu.
        if !cipler.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 9) {
                    ForEach(Array(cipler.enumerated()), id: \.offset) { _, p in
                        // ⚠️ Üstteki özet çipi de araç detayına götürüyor
                        //    (10 Eylül, Mehmet: "hat numaralarına tıklayınca da
                        //    nerede olduğu konumunu göstersin"). Aynı kural:
                        //    YALNIZCA canlı araç varsa — tahmin çipinde
                        //    gösterilecek konum yok.
                        if p.1.canliMi, let kap = p.1.arac {
                            NavigationLink(value: Rota.arac(kapino: kap, hat: p.0.hat,
                                                            yon: p.0.yon, durakKodu: durak.kod,
                                                            durakAdi: durak.ad)) {
                                Cip(bilgi: p.0, varis: p.1, tiklanabilir: true)
                            }
                            .buttonStyle(.plain)
                        } else if p.1.gpsKapaliMi, let k = p.1.kalkis {
                            // ⭐ 11 Eylül (Mehmet): "tahmini yapılan aracın da
                            //    konumu gösterilsin". Konum burada ÖLÇÜLMÜYOR,
                            //    hesaplanıyor — ayrı ekran, ayrı dil (bant + pay).
                            NavigationLink(value: Rota.seferKonum(hat: p.0.hat, yon: p.0.yon,
                                                                  kalkis: k, durakKodu: durak.kod)) {
                                Cip(bilgi: p.0, varis: p.1, tiklanabilir: true)
                            }
                            .buttonStyle(.plain)
                        } else {
                            Cip(bilgi: p.0, varis: p.1)
                        }
                    }
                }
                .padding(.horizontal, 14).padding(.vertical, 12)
            }
            .background(Tema.kart)
            .overlay(alignment: .bottom) { Rectangle().fill(Tema.cizgi).frame(height: 1) }
        }
    }

    /// ⭐ Şeridin işi TEK: "yakındaki seferler kaç dakikaya gelecek".
    /// İptal ve gecikme buraya YAZILMAZ — onlar aşağıdaki kartın işi.
    /// Bu yüzden şerit, gelmeyecek/gecikmiş satırları atlayıp ilk GERÇEK varışı seçer.
    private func seritVarisi(_ h: HatBilgisi) -> Varis? {
        h.varislar.first { !$0.iptalMi && !($0.gecikmis ?? false) }
    }

    struct Cip: View {
        let bilgi: HatBilgisi
        let varis: Varis
        /// Küçük bir konum simgesi — çipin dokunulabilir olduğunu belli eder.
        var tiklanabilir: Bool = false

        /// Şerit yalnızca süre gösterir: canlı görünen araç yeşil, tahmin mavi.
        private var renk: Color { varis.canliMi ? Tema.yesil : Tema.maviAcik }
        private var sayiMetni: String {
            varis.dakika <= 0 ? "şimdi" : "\(varis.dakika) dk"
        }

        var body: some View {
            VStack(spacing: 5) {
                Text(bilgi.hat)
                    .font(.system(size: 16, weight: .heavy))
                    .foregroundStyle(.white)
                    .frame(minWidth: 52)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .background(Tema.rozet, in: .rect(cornerRadius: 5))

                Text("→ " + bilgi.hedef)
                    .font(.system(size: 10))
                    .foregroundStyle(Tema.soluk)
                    .lineLimit(2).multilineTextAlignment(.center)
                    .frame(width: 74, height: 26, alignment: .top)

                // ⚠️ SEFER SAATİ ÇİPTE YAZMIYOR (11 Eylül, Mehmet'in kararı):
                //    kısa bir denemede çipe eklenmişti ama şeridi kalabalık
                //    yaptı — çipin işi TEK: "kaç dakikaya gelecek". Kalkış
                //    saati çipe dokununca açılan ekranın BAŞLIĞINDA duruyor
                //    ("10:35 seferi nerede?"), ayrıca aşağıdaki kartın kendi
                //    satırında. Aynı bilgiyi üç yerde tekrar etmiyoruz.

                // 📡 GPS kapalı: dakika gösterilir ama otobüsü GÖRMEDİĞİMİZ
                // belli edilir — yolcuya kesinlik iddiası satmıyoruz.
                HStack(spacing: 3) {
                    if varis.gpsKapaliMi {
                        Image(systemName: "dot.radiowaves.left.and.right")
                            .font(.system(size: 9, weight: .semibold))
                    }
                    Text(sayiMetni)
                        .font(.system(size: 14, weight: .bold))
                    if tiklanabilir {
                        Image(systemName: "location.fill")
                            .font(.system(size: 8, weight: .semibold))
                            .foregroundStyle(Tema.soluk)
                    }
                }
                .foregroundStyle(renk)
            }
            .frame(width: 82)
            .padding(.vertical, 9)
            .background(Tema.kart2, in: .rect(cornerRadius: 9))
            .overlay(RoundedRectangle(cornerRadius: 9).stroke(Tema.cizgi))
            .shadow(color: .black.opacity(0.05), radius: 2, y: 1)
        }
    }
}

struct HatKarti: View {
    @State private var tercihler = Tercihler.shared
    let bilgi: HatBilgisi
    /// Araç detayına giderken "senin durağın" işaretlemesi için gerekli.
    let durak: Durak

    private var gecikmisMi: Bool { bilgi.varislar.first?.gecikmis ?? false }

    /// ⛔ İptal edilen kalkışlar — kartın tepesinde kırmızı şeritte, saatleriyle.
    /// Sahadaki ekranın turuncu duyuru şeridinin karşılığı; iptal kırmızı.
    private var iptalSaatleri: [String] {
        bilgi.varislar.filter { $0.iptalMi }.compactMap { $0.kalkis }
    }

    var body: some View {
        VStack(spacing: 0) {
            // İptal şeridi — hangi saatteki sefer(ler) yapılmayacak
            if !iptalSaatleri.isEmpty {
                HStack(spacing: 6) {
                    Image(systemName: "xmark.octagon.fill").font(.system(size: 10))
                    // ⚠️ "İPTAL EDİLDİ" değil "İPTAL DUYURULDU" — ölçüldü, duyurulan
                    //    iptallerin %66'sı gerçekleşiyor, %34'ü telafi ediliyor.
                    //    Kesin olan DUYURU; seferin akıbeti değil. Edilgen çatı
                    //    bunu tek kelimeyle söylüyor, güven jargonu gerekmiyor.
                    Text(iptalSaatleri.count == 1
                         ? "İETT \(iptalSaatleri[0]) SEFERİNİ İPTAL DUYURDU"
                         : "İETT \(iptalSaatleri.joined(separator: " · ")) SEFERLERİNİ İPTAL DUYURDU")
                        .font(.system(size: 10, weight: .semibold)).tracking(0.6)
                    Spacer(minLength: 0)
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 13).padding(.vertical, 6)
                .background(Tema.kirmizi)
            }

            // Gecikme uyarısı — ekrandaki turuncu duyuru şeridinin karşılığı
            if gecikmisMi {
                HStack(spacing: 6) {
                    Image(systemName: "exclamationmark.triangle.fill").font(.system(size: 10))
                    Text("BEKLENENDEN UZUN SÜREDİR GEÇMEDİ")
                        .font(.system(size: 10, weight: .semibold)).tracking(0.6)
                    Spacer(minLength: 0)
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 13).padding(.vertical, 6)
                .background(Tema.turuncu)
            }

            // ── hat kimliği ── (dokununca bugünkü sefer tablosu açılır)
            NavigationLink(value: Rota.seferler(hat: bilgi.hat, yon: bilgi.yon,
                                                durakKodu: durak.kod)) {
            HStack(spacing: 11) {
                Text(bilgi.hat)
                    .font(.system(size: 17, weight: .heavy))
                    .foregroundStyle(.white)
                    .frame(minWidth: 54)
                    .padding(.horizontal, 8).padding(.vertical, 5)
                    .background(Tema.rozet, in: .rect(cornerRadius: 5))
                VStack(alignment: .leading, spacing: 2) {
                    // ⚠️ "GÜMRÜK" tek başına yön olduğunu belli etmiyordu (9 Eylül,
                    //    Mehmet: "hangi yöne gittiği gözükmüyor"). Ok ve "YÖNÜ" eki
                    //    kelimeyi bir hedefe çeviriyor.
                    HStack(spacing: 5) {
                        Image(systemName: "arrow.right")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(Tema.mavi)
                        Text(bilgi.hedef.uppercased() + " YÖNÜ")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundStyle(Tema.ink).lineLimit(2)
                    }
                    // Durak sırası yolcuya bir şey söylemiyor; ayrıntılı kipte kalıyor.
                    if tercihler.ayrintili {
                        Text("\(bilgi.sira)/\(bilgi.toplam_durak). durak · rotanın %\(bilgi.oran)'i")
                            .font(Tema.kucukEtiket()).foregroundStyle(Tema.soluk)
                    }
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Tema.soluk)
            }
            .padding(.horizontal, 13).padding(.vertical, 11)
            .contentShape(.rect)
            }
            .buttonStyle(.plain)

            // ⚠️ Canlı araç varken "beklersin" DEMEK YANLIŞ (9 Eylül): ekranda
            //    "ortalama 28 dk beklersin" yazarken altta 3 dk'da gelen otobüs
            //    duruyordu. İkisi çelişmiyor — biri hattın istatistiği, diğeri şu
            //    an görünen araç — ama yan yana okununca yolcu hangisine
            //    inanacağını bilemiyor. Araç görünüyorsa cümle bilgi kipine geçiyor.
            if let g = bilgi.gozlem {
                GozlemSatiri(gozlem: g, canliVar: bilgi.varislar.contains { $0.canliMi })
            }

            // İptaller yukarıdaki kırmızı şeritte anlatıldı; burada tekrar edilmiyor.
            // Böylece üç satırın üçü de GERÇEKTEN gelecek otobüslere kalıyor.
            ForEach(Array(bilgi.varislar.filter { !$0.iptalMi }
                                        .prefix(3).enumerated()), id: \.offset) { i, v in
                Rectangle().fill(Tema.cizgi).frame(height: 1)
                // ⚠️ YALNIZCA CANLI satır tıklanabilir (10 Eylül): detay ekranı
                //    aracın gerçek konumunu gösteriyor. Tahmin satırında
                //    gösterilecek bir araç yok — tıklanabilir yapmak boş bir
                //    söz vermek olurdu.
                if v.canliMi, let kap = v.arac {
                    NavigationLink(value: Rota.arac(kapino: kap, hat: bilgi.hat,
                                                    yon: bilgi.yon, durakKodu: durak.kod,
                                                    durakAdi: durak.ad)) {
                        VarisSatiri(varis: v, tiklanabilir: true)
                            .background(i % 2 == 1 ? Tema.kart2 : Tema.kart)
                    }
                    .buttonStyle(.plain)
                } else if v.gpsKapaliMi, let k = v.kalkis {
                    // ⭐ 11 Eylül: GPS'i kapalı seferin TAHMİNİ konumu artık
                    //    hesaplanabiliyor. Ama ölçülen konum değil — o yüzden
                    //    ayrı ekran: bant gösteriyor, payı da söylüyor.
                    NavigationLink(value: Rota.seferKonum(hat: bilgi.hat, yon: bilgi.yon,
                                                          kalkis: k, durakKodu: durak.kod)) {
                        VarisSatiri(varis: v, tiklanabilir: true)
                            .background(i % 2 == 1 ? Tema.kart2 : Tema.kart)
                    }
                    .buttonStyle(.plain)
                } else {
                    // ⚠️ Tarife satırında ne araç var ne hesaplanacak konum
                    //    (sefer henüz kalkmamış olabilir). Ama "bu sayı nereden
                    //    geliyor?" sorusunun cevabı var: hattın sefer tablosu.
                    NavigationLink(value: Rota.seferler(hat: bilgi.hat, yon: bilgi.yon,
                                                        durakKodu: durak.kod)) {
                        VarisSatiri(varis: v, tiklanabilir: true)
                            .background(i % 2 == 1 ? Tema.kart2 : Tema.kart)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .background(Tema.kart)
        .clipShape(.rect(cornerRadius: 11))
        .overlay(RoundedRectangle(cornerRadius: 11).stroke(Tema.cizgi.opacity(0.8)))
        // katmanlı gölge: yakın ve keskin + uzak ve yumuşak
        .shadow(color: Tema.mavi.opacity(0.10), radius: 2, y: 1)
        .shadow(color: Tema.mavi.opacity(0.07), radius: 10, y: 5)
    }
}

struct GozlemSatiri: View {
    let gozlem: Gozlem
    var canliVar: Bool = false
    var body: some View {
        HStack(spacing: 7) {
            Image(systemName: "chart.bar.fill").font(.system(size: 11)).foregroundStyle(Tema.yesil)
            Group {
                // ⚠️ "X dk'da bir geçiyor" YERİNE "ortalama X dk beklersin" (7 Eylül).
                //    Yolcunun sorduğu soru "hat ne sıklıkta?" değil, "ben ne kadar
                //    bekleyeceğim?" — ve konvoy halinde gelen hatlarda bu ikisi
                //    çok farklı çıkıyor (76: sıklık 1 dk, gerçek bekleme 2,6 dk).
                //    Eski sunucu bu alanı göndermiyorsa sıklığa geri dönülüyor.
                (gozlem.bekleme_dk.map { dk in
                    canliVar
                        ? Text("bu hat ortalama ") + Text("\(dk) dk").bold() + Text(" arayla geçer")
                        : Text("ortalama ") + Text("\(dk) dk").bold() + Text(" beklersin")
                } ?? (Text("bu saatte ortalama ") + Text("\(gozlem.aralik_dk) dk").bold()
                      + Text("'da bir geçiyor")))
                + Text(gozlem.son_gecis_dk.map { $0 < 180 ? " · son geçiş \($0) dk önce" : "" } ?? "")
            }
            .font(.system(size: 12)).foregroundStyle(Tema.ink2)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 13).padding(.vertical, 8)
        .background(Tema.kart2)
    }
}

struct VarisSatiri: View {
    let varis: Varis
    /// Sağda ok gösterilir — satırın dokunulabilir olduğunu belli eder.
    var tiklanabilir: Bool = false

    var body: some View {
        HStack(spacing: 11) {
            Image(systemName: ikon).font(.system(size: 14))
                .foregroundStyle(renk).frame(width: 20)

            VStack(alignment: .leading, spacing: 2) {
                Text(anaSatir).font(.system(size: 13.5)).foregroundStyle(Tema.ink)
                Text(altSatir).font(.system(size: 11)).foregroundStyle(Tema.soluk).lineLimit(1)
            }
            Spacer(minLength: 0)

            VStack(alignment: .trailing, spacing: 1) {
                Text(sayiMetni)
                    .font(Tema.rakam((varis.gecikmis ?? false) || varis.iptalMi ? 14 : 23))
                    .foregroundStyle(renk)
                // ⛔ İptalde "dk" yazılmaz: gelmeyecek otobüsün dakikası olmaz.
                if varis.dakika > 0 && !(varis.gecikmis ?? false) && !varis.iptalMi {
                    Text("dk").font(.system(size: 11, weight: .medium))
                        .foregroundStyle(Tema.soluk)
                }
            }

            // Dokunulabilir satırın işareti — yoksa kimse tıklamayı denemez.
            if tiklanabilir {
                Image(systemName: "chevron.right")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Tema.soluk)
            }
        }
        .padding(.horizontal, 13).padding(.vertical, 10)
        // İptal satırı: kırmızı sol şerit + hafif kırmızı zemin.
        // Kart zemini üst görünümden geliyor, o yüzden vurgu satırın İÇİNDE.
        .background(varis.iptalMi ? Tema.kirmiziZemin : Color.clear)
        .overlay(alignment: .leading) {
            if varis.iptalMi { Rectangle().fill(Tema.kirmizi).frame(width: 3) }
        }
    }

    private var ikon: String {
        if varis.iptalMi { return "xmark.octagon.fill" }
        if varis.gpsKapaliMi { return "dot.radiowaves.left.and.right" }
        return varis.canliMi ? "bus.fill" : (varis.gozlemMi ? "chart.bar.fill" : "clock")
    }
    private var renk: Color {
        if varis.iptalMi { return Tema.kirmizi }
        if varis.gecikmis ?? false { return Tema.turuncu }
        // GPS kapalı: yeşil DEĞİL — otobüsü görmüyoruz, tahmin ediyoruz.
        // Ama tarifeden güçlü, çünkü sefer gerçekten yola çıkmış.
        if varis.gpsKapaliMi { return Tema.mavi }
        return varis.canliMi ? Tema.yesil : (varis.gozlemMi ? Tema.mavi : Tema.ink2)
    }
    /// Gecikmiş sefere "şimdi" demek fazla iddialı olur — ayrı gösteriliyor.
    private var sayiMetni: String {
        if varis.iptalMi { return "İPTAL" }
        if varis.gecikmis ?? false { return "gecikti" }
        if varis.dakika <= 0 { return "şimdi" }
        return varis.gozlemMi ? "~\(varis.dakika)" : "\(varis.dakika)"
    }
    private var anaSatir: String {
        if varis.iptalMi { return "İETT \(varis.kalkis ?? "?") seferini iptal duyurdu" }
        if varis.gpsKapaliMi {
            return "\(varis.kalkis ?? "?") kalkışı · konum bildirmiyor"
        }
        if varis.gozlemMi {
            let a = varis.aralik_dk ?? 0, s = varis.son_gecis_dk ?? 0
            if varis.gecikmis ?? false { return "normalde \(a) dk'da bir geçer · son geçiş \(s) dk önce" }
            return "ölçüme göre sıradaki · \(a) dk'da bir"
        }
        if varis.canliMi {
            // ⚠️ Anlık hız yolcunun kararını değiştirmiyor (dakika zaten hesaba
            //    katıyor) ve "24 km/sa" ile "3 dk" yan yana çelişkili duruyordu.
            //    Ayrıntılı kipte kalıyor. Mesafe kalıyor: "ne kadar uzakta"
            //    sorusunun karşılığı ve güveni destekliyor.
            // ⚠️ "0.0 km uzakta" saçmaydı (9 Eylül): araç durağa varmış ama ekran
            //    sıfır gösteriyordu. Yakın mesafe METRE ile anlaşılır; 150 m'nin
            //    altı ise mesafe değil, DURUM bildiriyor.
            let km: String = {
                guard let m = varis.km else { return "yolda" }
                if m < 0.15 { return "durakta" }
                if m < 1.0  { return "\(Int((m * 1000).rounded(toNearestOrAwayFromZero: 50))) m uzakta" }
                return String(format: "%.1f km uzakta", m)
            }()
            // ⭐ HANGİ SEFER (11 Eylül): "5 dk" tek başına, tarifedeki hangi
            //    seferin otobüsü olduğunu söylemiyordu. Artık söylüyor.
            //    ⚠️ Kalkış çıkarılamadığında alan boş geliyor ve satır eskisi
            //    gibi görünüyor — yanlış saat yazmaktansa hiç yazmamak yeğ.
            // ⚠️ ÜÇ KADEME, ÜÇ FARKLI DİL — yolcu hangisine baktığını anlamalı:
            //    tarife → "09:30 seferi"    (ölçülen kalkış tarifeye oturdu)
            //    olcum  → "09:34 kalkışlı"  (tarife bozuk, ölçtüğümüz saat)
            //    hesap  → "≈09:30 seferi"   (kalkış görülmedi, varıştan geri hesap)
            //    "≈" boşuna değil: bu kademede ±5 dk pay var, kesinmiş gibi
            //    göstermek yolcuyu yanlış sefere güvendirirdi.
            let sefer: String? = varis.kalkis.map {
                switch varis.kalkis_kaynak {
                case "olcum": return "\($0) kalkışlı"
                case "hesap": return "≈\($0) seferi"
                default:      return "\($0) seferi"
                }
            }
            let govde = [sefer, km].compactMap { $0 }.joined(separator: " · ")
            guard Tercihler.shared.ayrintili else { return govde }
            return varis.hiz_kmh.map { "\(govde) · \($0) km/sa" } ?? govde
        }
        let k = varis.kalkis ?? "?"
        if let a = varis.alt, let u = varis.ust { return "\(k) kalkışı → \(a)–\(u)" }
        return "\(k) kalkışı"
    }
    private var altSatir: String {
        if varis.gpsKapaliMi {
            return "yolda · \(varis.varis ?? "?") civarı · ölçülmüş sürelerden"
        }
        if varis.iptalMi {
            // Kaynağı söylemek şart: bu satır tahmin değil, İETT'nin bildirimi.
            guard let yer = varis.kalkis_yeri, !yer.isEmpty else { return "İETT duyurusu" }
            return "İETT duyurusu · \(yer) kalkışlı"
        }
        // ⚠️ Araç kodu (A-1100) yolcuyu ilgilendirmiyor; "otobüs görünüyor" bilgisi
        //    ise ÖNEMLİ — tahmin değil, gerçekten görülen bir araç olduğunu söylüyor.
        if varis.canliMi {
            // ⚠️ Kalkış saati TARİFEDEN mi ÖLÇÜMDEN mi geldi — yolcu bilmeli.
            //    98 gibi tarifesi bozuk hatlarda ölçüme düşüyoruz (Bölüm 21);
            //    o saati tarifedeymiş gibi sunmak sessiz bir yalan olurdu.
            let kaynak: String = {
                switch varis.kalkis_kaynak {
                case "olcum": return " · tarifede yok"
                case "hesap": return " · sefer saati tahmini"
                default:      return ""
                }
            }()
            if Tercihler.shared.ayrintili {
                let olculen = varis.kalkis_kaynak == "tarife"
                    ? (varis.kalkis_olculen.map { " · kalkış ölçümü \($0)" } ?? "")
                    : ""
                return "otobüs görünüyor · araç \(varis.arac ?? "?")\(kaynak)\(olculen)"
            }
            return "otobüs görünüyor" + kaynak
        }
        return varis.not
    }
}


private extension Double {
    /// 50 metreye yuvarlar. "847 m uzakta" demek, GPS'in veremeyeceği bir
    /// kesinlik iddiası olurdu; "850 m" dürüst.
    func rounded(toNearestOrAwayFromZero adim: Double) -> Double {
        (self / adim).rounded() * adim
    }
}

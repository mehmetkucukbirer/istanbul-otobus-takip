import SwiftUI

/// AÇILIŞ EKRANI — düzeni İETT'nin kendi uygulamasından, rengi bizim temamızdan.
///
/// ⚠️ NEDEN BU DÜZEN (4 Eylül, Mehmet'in kararı): İstanbullu o uygulamanın
/// yerleşimini zaten biliyor — üstte karşılama, ortada arama, altında kısayollar.
/// Tanıdık bir yerleşim, öğrenilecek yeni bir şey olmaktan çıkarır. Tema.swift'teki
/// gerekçenin aynısı: tanıdıklık, özgünlükten daha değerli.
///
/// ⚠️ SAHTE BUTON YOK. Örnekte dört kısayol var (Değerlendir · Kare Kod ·
/// İstanbulkart · Canlı İzle) — bizde bunların hiçbiri yok. Çalışmayan buton
/// koymak yerine gerçekten çalışan üç şey kondu. Bir düğme varsa bir işi vardır.
struct GirisGorunumu: View {
    @State private var ayarlar = false
    @State private var konumcu = Konumcu()
    @State private var yakinDuraklar: [Durak] = []
    @State private var yukleniyor = false
    @State private var hata: String?
    @State private var favoriler = Favoriler.shared

    // ⚠️ ARAMA AYRI SAYFADA — ve öyle kalıyor (4 Eylül). Gün içinde iki kez
    //    döndü: önce sayfa vardı, sonra "sayfa açılmasın klavye çıksın" diye
    //    buraya taşındı, sonra "yeni sayfa açılsın ama estetik olsun" denildi.
    //    İtiraz sayfaya değil, ANİ YANA KAYMAYA'ydı — çözüm zoom geçişi:
    //    aşağıdaki arama çubuğu büyüyerek arama sayfasına dönüşüyor.
    /// Gezinme yığını — tek kaynak. Bayrak tabanlı gezinme KULLANILMIYOR;
    /// gerekçesi Rota.swift'te.
    @State private var yol: [Rota] = []
    @Namespace private var gecisAlani

    var body: some View {
        NavigationStack(path: $yol) {
            ScrollView {
                VStack(spacing: 0) {
                    kahraman
                    liste
                        // Sonuçlar/favoriler yer değiştirirken sıçramasın:
                        // hafifçe yukarıdan sönümlenerek geliyorlar.
                        .transition(.opacity.combined(with: .move(edge: .top)))
                        .animation(.easeInOut(duration: 0.28), value: yakinDuraklar.count)
                        .animation(.easeInOut(duration: 0.28), value: favoriler.duraklar.count)
                }
            }
            .background(Tema.zemin)
            .scrollIndicators(.hidden)
            .ignoresSafeArea(edges: .top)
            .sheet(isPresented: $ayarlar) { AyarlarGorunumu() }
            // ⚠️ TEK HEDEF, TEK BİÇİM — uygulamadaki bütün sayfalar burada.
            //    İkinci bir `navigationDestination` eklemek (hangi biçimde olursa
            //    olsun) 4 Eylül'deki "yanlış sayfa açılıyor" hatasını geri getirir.
            .navigationDestination(for: Rota.self) { r in
                switch r {
                case .arama:
                    AramaGorunumu(gecisAlani: gecisAlani)
                        .zoomIleAcil("arama", gecisAlani)
                case .durak(let d):
                    // Zoom geçişi: durak ekranı, dokunulan satırdan büyüyerek
                    // açılıyor — standart itme ekranı birden yana kaydırıyordu.
                    DurakGorunumu(durak: d).zoomIleAcil(d.kod, gecisAlani)
                case .arac(let kapino, let hat, let yon, let durakKodu, let durakAdi):
                    AracGorunumu(arac: kapino, hat: hat, yon: yon,
                                 durakKodu: durakKodu, durakAdi: durakAdi)
                case .seferler(let hat, let yon, let durakKodu):
                    SeferGorunumu(hat: hat, yon: yon, durakKodu: durakKodu)
                case .seferKonum(let hat, let yon, let kalkis, let durakKodu):
                    SeferKonumGorunumu(hat: hat, yon: yon, kalkis: kalkis,
                                       durakKodu: durakKodu)
                }
            }
        }
        .tint(Tema.mavi)
    }

    // ─────────────────────────────────────────────────────────────────────
    // ÜST BLOK — başlık + karşılama + arama
    // ─────────────────────────────────────────────────────────────────────

    private var kahraman: some View {
        // ⚠️ Fotoğraf ZStack'in İÇİNDE değil, ARKASINDA (4 Eylül).
        //    İlk denemede ZStack'e konmuştu: scaledToFill fotoğrafı 500×750
        //    oranıyla 603pt yüksekliğe çıkardı, ZStack o boyutu aldı, sonra
        //    .frame(height: 292) ORTADAN kırptı — başlık ve "Merhaba" pencerenin
        //    dışında kaldı. Arka plan olarak verilince boyutu içerik belirliyor,
        //    fotoğraf taşan kısmıyla birlikte kırpılıyor.
        // ⚠️ Blok, örnektekiyle aynı oranda UZUN (4 Eylül, Mehmet'in tespiti):
        //    ilk sürümde 292pt idi; arama çubuğu başlığa yapışık duruyor, altta
        //    kalan geniş beyaz alan ekranı boş gösteriyordu. Örnekte fotoğraf
        //    ekranın yarısından fazlasını kaplıyor ve kısayollar da onun ÜSTÜNDE
        //    duruyor — beyaz alan böylece hiç doğmuyor.
        VStack(alignment: .leading, spacing: 0) {
            baslikSatiri
            Text("Merhaba")
                .font(.system(size: 30, weight: .bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 18).padding(.top, 2)

            Spacer(minLength: 30)
            aramaCubugu.padding(.horizontal, 18)
            Spacer(minLength: 30)
            kisayollar
            Spacer(minLength: 26)
        }
        .padding(.top, 58)                     // durum çubuğu payı
        .frame(height: 476)
        .background {
            // ⭐ Gece Boğaziçi Köprüsü (Mehmet'in getirdiği görsel).
            //
            // ⚠️ Fotoğraf OLDUĞU GİBİ kullanılmıyor — üç katman var:
            //    1. saturation(0.5)  köprünün kırmızısı temayla çakışıyordu;
            //       doygunluk yarıya inince fotoğraf zemine geri çekiliyor
            //    2. mavi degrade    üstte koyu (başlık okunsun), ortada açık
            //       (fotoğraf görünsün), altta yine koyu (arama çubuğu okunsun)
            //    3. ince siyah kat  metnin altında kalan bölge için güvence
            //
            //    Amaç fotoğrafı göstermek değil, ekranın karakterini vermek:
            //    okunabilirlik her zaman görselin önünde.
            Image("BogazArka")
                .resizable()
                .scaledToFill()
                .saturation(0.5)
                .overlay {
                    LinearGradient(
                        stops: [
                            .init(color: Tema.mavi.opacity(0.94), location: 0.00),
                            .init(color: Tema.mavi.opacity(0.55), location: 0.34),
                            .init(color: Tema.mavi2.opacity(0.62), location: 0.68),
                            .init(color: Tema.mavi.opacity(0.90), location: 1.00),
                        ],
                        startPoint: .top, endPoint: .bottom)
                }
                .overlay { Color.black.opacity(0.10) }
        }
        .clipShape(.rect(bottomLeadingRadius: 30, bottomTrailingRadius: 30))
    }

    private var baslikSatiri: some View {
        HStack(spacing: 9) {
            Image(systemName: "bus.fill")
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(Tema.turuncu)
            (Text("Otobüsüm").fontWeight(.bold) + Text("Nerede?").fontWeight(.regular))
                .font(.system(size: 20))
                .foregroundStyle(.white)
            Spacer()
            Button { ayarlar = true } label: {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 19, weight: .semibold))
                    .foregroundStyle(.white)
            }
        }
        .padding(.horizontal, 18)
    }

    /// Arama alanı — dokununca arama sayfası BU ÇUBUKTAN büyüyerek açılıyor.
    /// `matchedTransitionSource`, geçişin nereden başlayacağını söyleyen işaret.
    private var aramaCubugu: some View {
        Button { yol.append(.arama) } label: {
            HStack(spacing: 12) {
                ZStack {
                    Circle().fill(Tema.turuncu).frame(width: 50, height: 50)
                    Image(systemName: "bus.fill")
                        .font(.system(size: 21, weight: .semibold))
                        .foregroundStyle(.white)
                }
                HStack {
                    Text("Durak ara")
                        .foregroundStyle(Tema.soluk)
                        .font(.system(size: 16))
                    Spacer()
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(Tema.mavi)
                }
                .padding(.horizontal, 18)
                .frame(height: 54)
                .background(Tema.kart, in: .capsule)
            }
        }
        .buttonStyle(.plain)
        .gecisKaynagi("arama", gecisAlani)
        .shadow(color: .black.opacity(0.18), radius: 10, y: 4)
    }

    // ─────────────────────────────────────────────────────────────────────
    // KISAYOLLAR — üçü de gerçekten çalışıyor
    // ─────────────────────────────────────────────────────────────────────

    private var kisayollar: some View {
        HStack(spacing: 10) {
            Kisayol(simge: "location.fill", baslik: "Yakınımdaki\nDuraklar") { yakiniBul() }
            Kisayol(simge: "heart.fill", baslik: "Favori\nDuraklar") {
                // Alt listeyi favorilere çevir. Favori yoksa aramaya yönlendir —
                // boş bir "favoriler" başlığı göstermenin kimseye faydası yok.
                if favoriler.duraklar.isEmpty { yol.append(.arama) } else { yakinDuraklar = [] }
            }
            Kisayol(simge: "magnifyingglass", baslik: "Durak\nAra") { yol.append(.arama) }
        }
        .padding(.horizontal, 10)
    }

    // ─────────────────────────────────────────────────────────────────────
    // ALT LİSTE — yakındakiler ya da favoriler
    // ─────────────────────────────────────────────────────────────────────

    @ViewBuilder private var liste: some View {
        VStack(spacing: 0) {
            if yukleniyor {
                ProgressView().tint(Tema.mavi).padding(.vertical, 40)
            } else if let h = hata {
                VStack(spacing: 8) {
                    Image(systemName: "wifi.exclamationmark").font(.system(size: 26))
                    Text(h).multilineTextAlignment(.center).font(.footnote)
                    Button("Sunucu adresini değiştir") { ayarlar = true }.font(.footnote)
                }
                .foregroundStyle(Tema.soluk).padding(.horizontal, 34).padding(.vertical, 30)
            } else if !yakinDuraklar.isEmpty {
                bolum("YAKINIMDAKİ DURAKLAR", yakinDuraklar)
            } else if !favoriler.duraklar.isEmpty {
                bolum("FAVORİ DURAKLARIM", favoriler.duraklar)
            } else {
                VStack(spacing: 6) {
                    Text("Durak ara ya da yakınındakileri bul.")
                        .font(.system(size: 14)).foregroundStyle(Tema.soluk)
                    Text("Sık kullandığın durağı ♥ ile buraya sabitleyebilirsin.")
                        .font(.system(size: 12)).foregroundStyle(Tema.soluk.opacity(0.8))
                }
                .multilineTextAlignment(.center).padding(.horizontal, 34).padding(.vertical, 34)
            }
        }
    }

    private func bolum(_ baslik: String, _ liste: [Durak]) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(baslik)
                .font(Tema.sutunBasligi()).kerning(0.8)
                .foregroundStyle(Tema.soluk)
                .padding(.horizontal, 20).padding(.top, 22).padding(.bottom, 8)

            VStack(spacing: 0) {
                ForEach(liste) { d in
                    DurakSatiri(durak: d, gecisAlani: gecisAlani)
                    if d.id != liste.last?.id {
                        Divider().overlay(Tema.cizgi).padding(.leading, 16)
                    }
                }
            }
            .background(Tema.kart, in: .rect(cornerRadius: 14))
            .padding(.horizontal, 14)
            .padding(.bottom, 26)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func yakiniBul() {
        Task {
            hata = nil; yukleniyor = true
            guard let k = await konumcu.konumAl() else {
                yukleniyor = false
                hata = "Konum alınamadı. Ayarlar'dan izin verebilir ya da durak adıyla arayabilirsin."
                return
            }
            do { yakinDuraklar = try await Servis.shared.yakin(enlem: k.latitude, boylam: k.longitude) }
            catch { hata = error.localizedDescription }
            yukleniyor = false
        }
    }
}

private struct Kisayol: View {
    let simge: String
    let baslik: String
    let eylem: () -> Void

    var body: some View {
        Button(action: eylem) {
            // ⚠️ Fotoğrafın ÜSTÜNDE duruyor: beyaz kart zemini görseli keserdi.
            //    Örnekteki gibi ince çemberli, beyaz simge. `renk` yalnızca
            //    çemberin içini hafifçe boyuyor — kimlik korunuyor, görsel açık kalıyor.
            VStack(spacing: 9) {
                // ⚠️ Renkli dolgu KALDIRILDI (4 Eylül): turuncu %35 saydamlık,
                //    altındaki koyu mavi fotoğrafla karışıp kahverengi bir leke
                //    veriyordu. Örnekteki gibi sade beyaz çember hem temiz duruyor
                //    hem de fotoğrafın hangi bölgesine denk gelirse gelsin okunuyor.
                ZStack {
                    Circle().fill(.black.opacity(0.18))
                    Circle().stroke(.white.opacity(0.75), lineWidth: 1.5)
                    Image(systemName: simge)
                        .font(.system(size: 19, weight: .semibold))
                        .foregroundStyle(.white)
                }
                .frame(width: 52, height: 52)
                .shadow(color: .black.opacity(0.25), radius: 5, y: 2)

                Text(baslik)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .shadow(color: .black.opacity(0.4), radius: 3, y: 1)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }
}

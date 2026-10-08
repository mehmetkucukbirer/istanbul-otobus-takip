import SwiftUI

/// ARAMA SAYFASI — giriş ekranındaki arama çubuğundan açılır.
///
/// ⚠️ TASARIM GEÇMİŞİ (4 Eylül, aynı gün iki kez döndü):
///   1. Önce ayrı sayfaydı, dokununca yana kayarak açılıyordu.
///   2. "Sayfa açılmasın, klavye çıksın" denildi — arama giriş ekranına taşındı.
///   3. "Yeni sayfa açılsın ama estetik olsun" denildi — sayfa geri geldi,
///      bu sefer ZOOM geçişiyle: arama çubuğu büyüyerek bu sayfaya dönüşüyor.
///
///   Kalan ders: itiraz sayfanın kendisine değil, ANİ YANA KAYMAYA'ydı.
///   Geçiş, dokunulan yerden büyüyünce göz bağlamı kaybetmiyor.
struct AramaGorunumu: View {
    /// ⚠️ Geçiş alanı DIŞARIDAN geliyor (4 Eylül hata düzeltmesi).
    ///    Kendi `@Namespace`'ini kullansaydı, durak ekranını da kendisi
    ///    tanımlamak zorunda kalırdı — sorunun kaynağı buydu.
    let gecisAlani: Namespace.ID

    @State private var metin = ""
    @State private var duraklar: [Durak] = []
    @State private var yukleniyor = false
    @State private var hata: String?
    @State private var ayarlar = false
    @State private var aramaGorevi: Task<Void, Never>?
    /// Sayfa açılırken BİR KEZ alınır, her harfte değil (GPS 1-3 sn sürer).
    @State private var konum: (enlem: Double, boylam: Double)?
    @State private var konumcu = Konumcu()
    @FocusState private var odak: Bool
    @Environment(\.dismiss) private var kapat

    var body: some View {
        ZStack(alignment: .top) {
            Tema.zemin.ignoresSafeArea()
            VStack(spacing: 0) {
                baslik
                aramaCubugu
                icerik
            }
        }
        .ignoresSafeArea(edges: .top)
        .navigationBarBackButtonHidden()
        .sheet(isPresented: $ayarlar) { AyarlarGorunumu() }
        // ⚠️⚠️ BURADA `navigationDestination(for: Durak.self)` YOK — VE OLMAMALI.
        //    4 Eylül'de vardı ve şu hataya yol açıyordu: durağa dokununca önce
        //    BOŞ bir arama ekranı açılıyor, geri basınca asıl durak ekranı
        //    ortaya çıkıyordu. Sebep, aynı NavigationStack içinde aynı tip için
        //    İKİ hedef tanımlanmasıydı (biri burada, biri GirisGorunumu'nda);
        //    SwiftUI hangisini kullanacağını bilemeyince yığın karışıyordu.
        //    Kural: bir tip için bir NavigationStack'te TEK hedef — o da kökte,
        //    GirisGorunumu'nda tanımlı ve bu ekrandaki bağlantıları da kapsıyor.
        // Sayfa açılır açılmaz klavye gelsin — buraya aramak için gelindi.
        .task {
            try? await Task.sleep(for: .milliseconds(420))   // geçiş bitsin
            odak = true
        }
        .task {
            // İzin yoksa sessizce atlar — aramada izin penceresi açılmıyor.
            if let k = await konumcu.izinliyseKonum() {
                konum = (k.latitude, k.longitude)
                if !metin.isEmpty { gecikmeliAra(metin) }   // sonuçlar uzaklıkla tazelensin
            }
        }
    }

    /// Mavi karşılama şeridi — girişteki başlığın aynısı, alt köşeleri yuvarlak.
    private var baslik: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 9) {
                Button { kapat() } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(.white)
                }
                Image(systemName: "bus.fill")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Tema.turuncu)
                (Text("Otobüsüm").fontWeight(.bold) + Text("Nerede?").fontWeight(.regular))
                    .font(.system(size: 20)).foregroundStyle(.white)
                Spacer()
                Button { ayarlar = true } label: {
                    Image(systemName: "line.3.horizontal")
                        .font(.system(size: 19, weight: .semibold))
                        .foregroundStyle(.white)
                }
            }
            Text("Durak Ara")
                .font(.system(size: 27, weight: .bold))
                .foregroundStyle(.white)
                .padding(.top, 6)
        }
        .padding(.horizontal, 18)
        .padding(.top, 58)
        .padding(.bottom, 18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Tema.mavi)
        .clipShape(.rect(bottomLeadingRadius: 26, bottomTrailingRadius: 26))
    }

    /// Örnekteki düzen: renkli kutu, içinde etiket ve beyaz yazma alanı.
    /// Örnekte kutu sarı; burada temanın duyuru turuncusu kullanılıyor.
    private var aramaCubugu: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text("Hat veya Durak Ara")
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(.white)
            HStack(spacing: 8) {
                TextField("durak adı…", text: $metin)
                    .foregroundStyle(Tema.ink)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .submitLabel(.search)
                    .focused($odak)
                    .onChange(of: metin) { _, yeni in gecikmeliAra(yeni) }
                if !metin.isEmpty {
                    Button { metin = ""; duraklar = []; hata = nil } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(Tema.soluk)
                    }
                    .buttonStyle(.plain)
                }
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Tema.mavi)
            }
            .padding(.horizontal, 16)
            .frame(height: 50)
            .background(Tema.kart, in: .rect(cornerRadius: 12))
        }
        .padding(14)
        .background(Tema.turuncu, in: .rect(cornerRadius: 16))
        .padding(.horizontal, 14).padding(.top, 16).padding(.bottom, 12)
    }

    @ViewBuilder private var icerik: some View {
        if yukleniyor {
            bosluk { ProgressView().tint(Tema.mavi) }
        } else if let h = hata {
            bosluk {
                VStack(spacing: 10) {
                    Image(systemName: "wifi.exclamationmark").font(.system(size: 30))
                    Text(h).multilineTextAlignment(.center).font(.callout)
                    Button("Sunucu adresini değiştir") { ayarlar = true }
                        .font(.footnote).tint(Tema.mavi)
                }.foregroundStyle(Tema.soluk).padding(.horizontal, 30)
            }
        } else if duraklar.isEmpty {
            bosluk {
                Text(metin.trimmingCharacters(in: .whitespaces).count >= 2
                     ? "“\(metin)” için durak bulunamadı."
                     : "Durak adının ilk harflerini yazman yeterli.")
                    .foregroundStyle(Tema.soluk).font(.callout)
                    .multilineTextAlignment(.center).padding(.horizontal, 40)
            }
        } else {
            // ⚠️ List yerine ScrollView: List, NavigationLink'e kendi ">" okunu
            //    ekliyor ve favori kalbiyle yan yana kalabalık duruyordu.
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(duraklar) { d in
                        DurakSatiri(durak: d, gecisAlani: gecisAlani)
                        Divider().overlay(Tema.cizgi).padding(.leading, 70)
                    }
                }
                .background(Tema.kart)
            }
            .scrollIndicators(.hidden)
            .scrollDismissesKeyboard(.immediately)
            .transition(.opacity)
        }
    }

    private func bosluk<İ: View>(@ViewBuilder _ ic: () -> İ) -> some View {
        VStack { Spacer(); ic(); Spacer() }.frame(maxWidth: .infinity)
    }

    /// Her tuşta istek atmamak için 300 ms bekletiyoruz.
    private func gecikmeliAra(_ q: String) {
        aramaGorevi?.cancel()
        guard q.trimmingCharacters(in: .whitespaces).count >= 2 else { duraklar = []; return }
        aramaGorevi = Task {
            try? await Task.sleep(for: .milliseconds(300))
            if Task.isCancelled { return }
            yukleniyor = true; hata = nil
            do {
                let bulunan = try await Servis.shared.ara(q, konum: konum)
                if Task.isCancelled { return }
                withAnimation(.easeInOut(duration: 0.22)) { duraklar = bulunan }
            } catch {
                hata = error.localizedDescription; duraklar = []
            }
            yukleniyor = false
        }
    }
}

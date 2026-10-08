import SwiftUI

/// GPS'i KAPALI seferin tahmini konumu.
///
/// ⭐ NEDEN VAR (11 Eylül, Mehmet'in isteği):
///   *"tahmini yapılan aracın da konumu gösterilsin"*
///
/// Canlı araçta konum ÖLÇÜLÜYOR (`AracGorunumu`). Burada otobüs görünmüyor;
/// elimizde yalnızca kalkış saati ve ölçülmüş parça süreleri var. Kalkıştan bu
/// yana geçen süreyi durak sırasına çeviriyoruz.
///
/// ⚠️⚠️ BU EKRAN NEDEN TEK DURAK GÖSTERMİYOR: ölçüldü (11 Eylül, 10 Eylül
/// verisi) — tahmin edilen sıra ile aracın gerçekten görüldüğü sıra arasında
/// ortanca 4 durak sapma var (89A'da ±1–2, 522'de sürekli +9). "Otobüs şu an
/// ŞURADA" demek yolcuyu ortalama dört durak yanıltmak olurdu. Onun yerine
/// BANT gösteriliyor ve payın kendisi ekranda yazıyor.
///
/// ⚠️ Hatların yalnız %34'ünde ölçülmüş parça verisi var. Kalanında ekran
/// "konum hesaplanamıyor" diyor — uydurulmuş bir konum göstermiyor.
struct SeferKonumGorunumu: View {
    let hat: String
    let yon: String
    let kalkis: String
    let durakKodu: String

    @State private var konum: SeferKonumu?
    @State private var hata: String?
    @State private var yukleniyor = true
    @Environment(\.dismiss) private var kapat

    var body: some View {
        ZStack(alignment: .top) {
            Tema.zemin.ignoresSafeArea()
            VStack(spacing: 0) {
                baslik
                if yukleniyor {
                    Spacer(); ProgressView().tint(Tema.mavi); Spacer()
                } else if let s = konum {
                    ScrollView {
                        VStack(spacing: 12) {
                            if s.konum_var { bantKarti(s); yolKarti(s) } else { konumYokKarti(s) }
                        }
                        .padding(14)
                    }
                    .scrollIndicators(.hidden)
                } else {
                    Spacer()
                    Text(hata ?? "Bu seferin bilgisi alınamadı.")
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
            Text("\(kalkis) seferi nerede?")
                .font(.system(size: 25, weight: .bold)).foregroundStyle(.white)
                .padding(.top, 6).lineLimit(1).minimumScaleFactor(0.8)
            // ⚠️ Başlıkta bile kesinlik iddiası yok: otobüs konum bildirmiyor.
            HStack(spacing: 5) {
                Image(systemName: "dot.radiowaves.left.and.right").font(.system(size: 10))
                Text("bu otobüs konum bildirmiyor")
            }
            .font(.system(size: 12)).foregroundStyle(.white.opacity(0.75))
        }
        .padding(.horizontal, 18).padding(.top, 58).padding(.bottom, 18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Tema.mavi)
        .clipShape(.rect(bottomLeadingRadius: 26, bottomTrailingRadius: 26))
    }

    // ── Bant: "şu an şurası ile şurası arasında" ─────────────────────────────

    private func bantKarti(_ s: SeferKonumu) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 9) {
                Image(systemName: "location.viewfinder")
                    .font(.system(size: 14)).foregroundStyle(Tema.turuncu)
                Text("Şu an tahminen bu aralıkta")
                    .font(.system(size: 14, weight: .semibold)).foregroundStyle(Tema.ink)
                Spacer(minLength: 0)
            }

            Text("\(s.bant_bas_ad ?? "?")  ↔  \(s.bant_son_ad ?? "?")")
                .font(.system(size: 15, weight: .medium)).foregroundStyle(Tema.mavi)
                .fixedSize(horizontal: false, vertical: true)

            Divider().overlay(Tema.cizgi)

            // ⚠️⚠️ PAY EKRANDA YAZIYOR. Ölçülmüş sapmayı saklamak, yolcuya
            //    olmayan bir kesinlik satmak olurdu (PROMPT Bölüm 8).
            satir(simge: "clock", metin: "\(kalkis) kalkışından bu yana \(s.gecen_dk) dk geçti")
            satir(simge: "exclamationmark.triangle",
                  metin: "±\(s.pay_durak) durak pay var — otobüs görünmediği için "
                       + "konum ölçülmüyor, ölçülmüş sürelerden hesaplanıyor",
                  renk: Tema.turuncu)

            if s.hedef_gecilmis_olabilir == true {
                satir(simge: "arrow.uturn.left",
                      metin: "bu otobüs \(s.durak_adi) durağını geçmiş olabilir — sıradakini bekle",
                      renk: Tema.kirmizi)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Tema.kart, in: .rect(cornerRadius: 14))
    }

    /// Veri yoksa uydurmuyoruz — neden bilmediğimizi söylüyoruz.
    private func konumYokKarti(_ s: SeferKonumu) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 9) {
                Image(systemName: "questionmark.circle")
                    .font(.system(size: 14)).foregroundStyle(Tema.soluk)
                Text("Konum hesaplanamıyor")
                    .font(.system(size: 14, weight: .semibold)).foregroundStyle(Tema.ink)
                Spacer(minLength: 0)
            }
            Text(s.not ?? "Bu sefer için yeterli ölçüm yok.")
                .font(.system(size: 13)).foregroundStyle(Tema.ink2)
            Text("Otobüs konum bildirmiyor ve bu hat için yeterli geçmiş ölçüm "
                 + "birikmemiş. Uydurma bir yer göstermektense boş bırakıyoruz.")
                .font(.system(size: 12)).foregroundStyle(Tema.soluk)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Tema.kart, in: .rect(cornerRadius: 14))
    }

    private func satir(simge: String, metin: String, renk: Color = Tema.ink2) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: simge).font(.system(size: 12)).foregroundStyle(renk)
                .frame(width: 16)
            Text(metin).font(.system(size: 12)).foregroundStyle(renk)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
    }

    // ── Rota: bandın içi vurgulu ─────────────────────────────────────────────

    private func yolKarti(_ s: SeferKonumu) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("BU ARALIKTAKİ DURAKLAR")
                .font(Tema.sutunBasligi()).kerning(0.8).foregroundStyle(Tema.soluk)
                .padding(.bottom, 10)

            ForEach(s.duraklar, id: \.sira) { g in
                HStack(spacing: 12) {
                    ZStack {
                        Rectangle().fill(Tema.cizgi).frame(width: 2)
                        Circle()
                            .fill(g.hedef_mi ? Tema.mavi : (g.bantta ? Tema.turuncu.opacity(0.35) : Tema.kart))
                            .frame(width: g.hedef_mi ? 12 : 9, height: g.hedef_mi ? 12 : 9)
                            .overlay(Circle().stroke(g.hedef_mi ? Tema.mavi : Tema.cizgi, lineWidth: 2))
                    }
                    .frame(width: 26)

                    VStack(alignment: .leading, spacing: 1) {
                        Text(g.ad)
                            .font(.system(size: 14, weight: g.hedef_mi ? .semibold : .regular))
                            .foregroundStyle(g.hedef_mi ? Tema.mavi : Tema.ink).lineLimit(1)
                        if g.hedef_mi {
                            Text("senin durağın").font(.system(size: 11)).foregroundStyle(Tema.soluk)
                        }
                    }
                    Spacer(minLength: 6)
                    if g.sira == s.tahmini_sira {
                        Text("en olası").font(Tema.kucukEtiket()).foregroundStyle(Tema.turuncu)
                    }
                }
                .padding(.vertical, 5)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Tema.kart, in: .rect(cornerRadius: 14))
    }

    private func getir() async {
        yukleniyor = true
        do { konum = try await Servis.shared.seferKonumu(hat: hat, yon: yon,
                                                         kalkis: kalkis, durak: durakKodu) }
        catch { hata = error.localizedDescription }
        yukleniyor = false
    }
}

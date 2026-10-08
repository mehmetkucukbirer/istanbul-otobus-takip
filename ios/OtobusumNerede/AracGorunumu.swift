import SwiftUI

/// ARAÇ DETAYI — "bu otobüs şu an nerede, nereye gidiyor?"
///
/// ⭐ NEDEN VAR (10 Eylül, Mehmet'in isteği):
///   *"sefaköy ht20 otobüsü 10 dk'ya gelicek, üstüne tıklayınca anlık olarak
///     hangi duraktan nereye hareket ediyor onu göster"*
///
/// Durak ekranındaki "5 dk" tek başına bir iddia. Bu ekran o iddiayı DAYANAĞIYLA
/// gösteriyor: otobüs en son hangi duraktan kaçta geçti, şimdi nerede, yolcunun
/// durağına kaç durak var. Yolcu tahmine kendi güvenini kurabiliyor —
/// PROMPT Bölüm 2'deki "neden" cümlesinin ekrandaki karşılığı.
struct AracGorunumu: View {
    let arac: String
    let hat: String
    let yon: String
    let durakKodu: String
    let durakAdi: String

    @State private var detay: AracDetay?
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
                } else if let d = detay {
                    ScrollView {
                        VStack(spacing: 12) {
                            durumKarti(d)
                            yolKarti(d)
                        }
                        .padding(14)
                    }
                    .scrollIndicators(.hidden)
                } else {
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "bus.doubledecker").font(.system(size: 30))
                        Text(hata ?? "Bu otobüsün konumu şu an alınamıyor.")
                            .font(.callout).multilineTextAlignment(.center)
                    }
                    .foregroundStyle(Tema.soluk).padding(.horizontal, 40)
                    Spacer()
                }
            }
        }
        .ignoresSafeArea(edges: .top)
        .navigationBarBackButtonHidden()
        .task { await getir() }
    }

    private var seferMetni: String {
        guard let k = detay?.kalkis else { return "otobüs \(arac)" }
        let s = detay?.kalkis_kaynak == "hesap" ? "≈\(k)" : k
        return "\(s) seferi · otobüs \(arac)"
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
            Text("Bu otobüs nerede?")
                .font(.system(size: 25, weight: .bold)).foregroundStyle(.white)
                .padding(.top, 6)
            // ⭐ Sefer saati başlıkta: çipten kaldırılan bilgi buraya taşındı.
            //    "≈" geri hesap kademesinin payını belirtiyor (gerekçe
            //    sunucudaki sefer_kimligi'nde).
            Text(seferMetni)
                .font(.system(size: 12)).foregroundStyle(.white.opacity(0.7))
        }
        .padding(.horizontal, 18).padding(.top, 58).padding(.bottom, 18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Tema.mavi)
        .clipShape(.rect(bottomLeadingRadius: 26, bottomTrailingRadius: 26))
    }

    // ── ŞU ANKİ DURUM ────────────────────────────────────────────────────────

    private func durumKarti(_ d: AracDetay) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Image(systemName: "location.fill")
                    .font(.system(size: 13)).foregroundStyle(Tema.yesil)
                // ⚠️ Konumun YAŞI gösteriliyor: 1 dakikalık konumla 6 dakikalık
                //    konum aynı şey değil, yolcu bunu bilmeli.
                Text(d.konum_yasi_dk <= 1 ? "konumu az önce alındı"
                                          : "konumu \(d.konum_yasi_dk) dk önce alındı")
                    .font(.system(size: 13)).foregroundStyle(Tema.ink2)
                Spacer(minLength: 0)
            }
            if let h = d.hiz_kmh {
                satir(simge: "speedometer",
                      metin: h < 5 ? "şu an duruyor ya da çok yavaş" : "şu an \(h) km/sa ile gidiyor")
            }
            // ⚠️ Otobüs durağı geçmişse bunu SÖYLE. Sessizce "senin durağın"
            //    işaretini gizlemek, yolcuyu bekletmeye devam ettirir.
            if d.hedef_gecildi == true {
                HStack(spacing: 10) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 13)).foregroundStyle(Tema.turuncu)
                    Text("bu otobüs durağını geçmiş — sıradakini bekle")
                        .font(.system(size: 13, weight: .medium)).foregroundStyle(Tema.turuncu)
                    Spacer(minLength: 0)
                }
            }
            if let t = d.trafik {
                // ⚠️ ŞEHİR GENELİ indeks — yol bazlı değil (yol bazlı açık veride
                //    yok). Tahmine girmiyor, yalnızca bağlam veriyor.
                satir(simge: "car.fill",
                      metin: "İstanbul trafiği: \(t.durum) (\(t.deger)/100)",
                      renk: t.deger < 40 ? Tema.yesil : (t.deger < 65 ? Tema.turuncu : Tema.kirmizi))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Tema.kart, in: .rect(cornerRadius: 14))
    }

    private func satir(simge: String, metin: String, renk: Color = Tema.ink2) -> some View {
        HStack(spacing: 10) {
            Image(systemName: simge).font(.system(size: 13)).foregroundStyle(renk)
            Text(metin).font(.system(size: 13)).foregroundStyle(Tema.ink2)
            Spacer(minLength: 0)
        }
    }

    // ── YOL: geçtiği ve gideceği duraklar ────────────────────────────────────

    private func yolKarti(_ d: AracDetay) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("YOLU")
                .font(Tema.sutunBasligi()).kerning(0.8).foregroundStyle(Tema.soluk)
                .padding(.bottom, 10)

            ForEach(d.gecti, id: \.sira) { g in
                durakSatiri(ad: g.ad, sag: "\(g.saat)", altYazi: "\(g.dk_once) dk önce geçti",
                            renk: Tema.soluk, dolu: true)
            }

            // Otobüsün şu anki yeri — geçtikleriyle gidecekleri arasında
            HStack(spacing: 12) {
                ZStack {
                    Circle().fill(Tema.yesil).frame(width: 26, height: 26)
                    Image(systemName: "bus.fill")
                        .font(.system(size: 12, weight: .bold)).foregroundStyle(.white)
                }
                Text("otobüs şu an burada")
                    .font(.system(size: 14, weight: .semibold)).foregroundStyle(Tema.yesil)
                Spacer(minLength: 0)
            }
            .padding(.vertical, 6)

            ForEach(d.gidecek, id: \.sira) { g in
                durakSatiri(ad: g.ad, sag: "\(g.km) km",
                            altYazi: g.hedef_mi ? "senin durağın" : nil,
                            renk: g.hedef_mi ? Tema.mavi : Tema.ink,
                            dolu: false, vurgu: g.hedef_mi)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Tema.kart, in: .rect(cornerRadius: 14))
    }

    private func durakSatiri(ad: String, sag: String, altYazi: String? = nil,
                             renk: Color, dolu: Bool, vurgu: Bool = false) -> some View {
        HStack(spacing: 12) {
            // Sol kenardaki çizgi + nokta: geçilen duraklar dolu, gelecekler boş
            ZStack {
                Rectangle().fill(Tema.cizgi).frame(width: 2)
                Circle()
                    .fill(dolu ? Tema.soluk : (vurgu ? Tema.mavi : Tema.kart))
                    .frame(width: vurgu ? 12 : 9, height: vurgu ? 12 : 9)
                    .overlay(Circle().stroke(vurgu ? Tema.mavi : Tema.cizgi, lineWidth: 2))
            }
            .frame(width: 26)

            VStack(alignment: .leading, spacing: 1) {
                Text(ad)
                    .font(.system(size: 14, weight: vurgu ? .semibold : .regular))
                    .foregroundStyle(renk).lineLimit(1)
                if let a = altYazi {
                    Text(a).font(.system(size: 11)).foregroundStyle(Tema.soluk)
                }
            }
            Spacer(minLength: 6)
            Text(sag).font(Tema.kucukEtiket()).foregroundStyle(Tema.soluk)
        }
        .padding(.vertical, 5)
    }

    private func getir() async {
        yukleniyor = true
        do { detay = try await Servis.shared.aracDetay(arac: arac, hat: hat, yon: yon, durak: durakKodu) }
        catch { hata = error.localizedDescription }
        yukleniyor = false
    }
}

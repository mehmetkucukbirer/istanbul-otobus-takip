import CoreLocation
import SwiftUI

// ⚠️ Bu dosyada eskiden `AramaGorunumu` vardı: ayrı bir arama SAYFASI.
//    4 Eylül'de kaldırıldı — arama giriş ekranına taşındı (GirisGorunumu),
//    çünkü sayfa geçişi tek işi durak aramak olan bir uygulamada fazladan
//    bir adımdı. Geriye iki parça kaldı ve ikisi de hâlâ kullanılıyor:
//    aşağıdaki durak satırı ile en alttaki konum yardımcısı.

/// Arama sonucundaki tek satır — örnekteki düzen: rozet · ad · YÖN · kalp.
///
/// ⚠️ "YÖN" satırı ürünün kendi bulgusu değil, örnekte de var: İETT'nin kendi
/// uygulaması da aynı duraktan iki yönü bu şekilde ayırıyor. Aynı ada sahip
/// duraklar yolun iki yakasıdır ve TERS yöne gider; ad ile ilçe onları ayırmaz.
struct DurakSatiri: View {
    let durak: Durak
    /// Geçiş kaynağı — durak ekranı bu satırdan BÜYÜYEREK açılıyor.
    /// Satırın kendisi animasyonun başlangıç karesi oluyor.
    var gecisAlani: Namespace.ID? = nil
    @State private var favoriler = Favoriler.shared

    var body: some View {
        // ⚠️ Kalp, NavigationLink'in DIŞINDA olmak zorunda: bağlantının içine
        //    konan düğme dokunuşu yutulur, favori eklenmez — sadece durak açılır.
        HStack(spacing: 12) {
            NavigationLink(value: Rota.durak(durak)) { govde.contentShape(.rect) }
                .buttonStyle(.plain)
                .gecisKaynagi(durak.kod, gecisAlani)

            Button { favoriler.degistir(durak) } label: {
                Image(systemName: favoriler.favoriMi(durak.kod) ? "heart.fill" : "heart")
                    .font(.system(size: 17))
                    .foregroundStyle(favoriler.favoriMi(durak.kod) ? Tema.turuncu : Tema.soluk)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
    }

    private var altBilgi: String {
        var parca: [String] = []
        if let i = durak.ilce, !i.isEmpty { parca.append(i) }
        if let h = durak.hatlar, !h.isEmpty {
            let fazla = durak.hat_sayisi - h.count
            parca.append(h.prefix(5).joined(separator: " ") + (fazla > 0 ? " +\(fazla)" : ""))
        } else if durak.hat_sayisi > 0 {
            parca.append("\(durak.hat_sayisi) hat")
        }
        return parca.joined(separator: " · ")
    }

    /// 850 m · 3,9 km · 12 km — kilometre üstünde metre hassasiyeti gürültü.
    static func uzaklikMetni(_ m: Int) -> String {
        if m < 40 { return "yanında" }            // "0 m" anlamsız görünüyordu
        if m < 1000 { return "\((m + 25) / 50 * 50) m" }
        if m < 10_000 { return String(format: "%.1f km", Double(m) / 1000).replacingOccurrences(of: ".", with: ",") }
        return "\(m / 1000) km"
    }

    private var govde: some View {
        HStack(spacing: 12) {
            // Rozet — örnekteki "D" kutusu. Durak simgesi taşıyor.
            ZStack {
                RoundedRectangle(cornerRadius: 8).stroke(Tema.mavi, lineWidth: 2)
                Image(systemName: "bus.fill")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Tema.mavi)
            }
            .frame(width: 42, height: 42)

            VStack(alignment: .leading, spacing: 2) {
                Text(durak.ad)
                    .foregroundStyle(Tema.ink)
                    .font(.system(size: 16, weight: .semibold))
                    .lineLimit(1)

                // Durağın gittiği yön — aynı adlı durakları ayıran tek şey.
                // ⚠️ Örnekteki gibi TEK hedef. Sunucu üçünü de gönderiyor ama
                //    telefonda üçü satıra sığmıyor ve "YÖNÜ" eki kırpılıyordu —
                //    ayırt eden zaten ilk (en çok hattın gittiği) hedef.
                // ⚠️⚠️ 7 Ekim: sunucu artık İLK yönü değil AYIRT EDİCİ yönü başa
                //    koyuyor — aynı adlı diğer duraklarda bulunmayan yönü. Ölçüm:
                //    ilk yönle %5,6 durak karışıyordu, ayırt edici yönle %1,7.
                if let y = durak.yonler, let ilk = y.first {
                    Text(ilk + " YÖNÜ")
                        .foregroundStyle(Tema.mavi)
                        .font(.system(size: 11.5, weight: .semibold))
                        .kerning(0.3)
                        .lineLimit(1)
                }
                // ⭐ "Nerede" sorusunun cevabı: ilçe ve oradan geçen hatlar.
                //    Kalan %1,7'yi ayıran bunlar ve sağdaki uzaklık. Hat numarası
                //    yolcunun en iyi tanıdığı bilgi — "89A'nın geçtiği Sefaköy".
                Text(altBilgi)
                    .foregroundStyle(Tema.soluk)
                    .font(.system(size: 11.5))
                    .lineLimit(1)
            }

            Spacer(minLength: 6)

            if let m = durak.uzaklik_m {
                Text(Self.uzaklikMetni(m))
                    .font(Tema.kucukEtiket())
                    .foregroundStyle(m < 1000 ? Tema.yesil : Tema.soluk)
                    .monospacedDigit()
            }
        }
    }
}

/// Konum izni ve tek seferlik konum alma.
@Observable
final class Konumcu: NSObject, CLLocationManagerDelegate {
    private let yonetici = CLLocationManager()
    private var devam: CheckedContinuation<CLLocationCoordinate2D?, Never>?

    override init() { super.init(); yonetici.delegate = self }

    /// İzin ZATEN verilmişse konum alır; verilmemişse sessizce nil döner.
    ///
    /// ⚠️ Aramada kullanılıyor (7 Ekim) ve aramanın izin penceresi AÇMAMASI
    ///   gerekiyor: yolcu durak adı yazarken önüne "konumuna erişebilir miyiz?"
    ///   çıkması işi böler. İzni "Yakınımdaki Duraklar" istiyor; o verildiyse
    ///   arama da faydalanıyor. Önce son bilinen konum (anında), yoksa tek istek.
    func izinliyseKonum() async -> CLLocationCoordinate2D? {
        let d = yonetici.authorizationStatus
        guard d == .authorizedWhenInUse || d == .authorizedAlways else { return nil }
        if let son = yonetici.location,
           Date().timeIntervalSince(son.timestamp) < 600 { return son.coordinate }
        return await konumAl()
    }

    func konumAl() async -> CLLocationCoordinate2D? {
        if yonetici.authorizationStatus == .notDetermined {
            yonetici.requestWhenInUseAuthorization()
        }
        return await withCheckedContinuation { c in
            devam = c
            yonetici.requestLocation()
        }
    }

    func locationManager(_ m: CLLocationManager, didUpdateLocations l: [CLLocation]) {
        devam?.resume(returning: l.first?.coordinate); devam = nil
    }
    func locationManager(_ m: CLLocationManager, didFailWithError e: Error) {
        devam?.resume(returning: nil); devam = nil
    }
}

import Foundation
import SwiftUI

/// Görüntüleme tercihleri — telefonda saklanır.
///
/// ⚠️ NEDEN VAR (9 Eylül, Mehmet'in tespiti): durak ekranı geliştirici için
/// yazılmıştı, yolcu için değil. Ekranda şunlar duruyordu:
///
///     "32/33. durak · rotanın %96'i"     ← yolcuya hiçbir şey söylemiyor
///     "1.22 km uzakta · 24 km/sa"        ← anlık hız kararı değiştirmiyor
///     "araç A-1100 görünüyor"            ← araç kodu yolcuyu ilgilendirmiyor
///
/// Ama bu alanlar GELİŞTİRME sırasında işe yarıyordu: 4-8 Eylül'deki doğrulama
/// oturumlarında araç kodu ve mesafe ile tahminler ham veriyle karşılaştırıldı
/// (Bölüm 62-63). Silmek yerine anahtara bağlandı.
///
/// Varsayılan KAPALI: uygulamayı ilk açan yolcu sade ekranı görür.
@Observable
final class Tercihler {
    static let shared = Tercihler()

    private let anahtar = "ayrintili_gosterim"

    /// Açıkken araç kodu, anlık hız ve durak sırası da gösterilir.
    var ayrintili: Bool {
        didSet { UserDefaults.standard.set(ayrintili, forKey: anahtar) }
    }

    private init() {
        ayrintili = UserDefaults.standard.bool(forKey: anahtar)   // varsayılan false
    }
}

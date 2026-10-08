import SwiftUI

/// EKRAN GEÇİŞLERİ — "birden yana kayma" yerine büyüyerek açılma.
///
/// ⚠️ NEDEN KOŞULLU (4 Eylül): `navigationTransition(.zoom)` ve
/// `matchedTransitionSource` iOS 18 ile geldi; projenin dağıtım hedefi ise 17.0.
/// Hedefi 18'e çıkarmak, iOS 17'de kalmış telefonları uygulamanın dışında
/// bırakırdı — bir geçiş animasyonu için ödenecek bedel değil. Bu yüzden geçiş
/// `#available` ile sarmalandı:
///
///     iOS 18+  → ekran, dokunulan öğeden büyüyerek açılır
///     iOS 17   → sistemin standart geçişi (uygulama aynı şekilde çalışır)
///
/// Görsel bir iyileştirmenin, çalışan bir özelliği kimseden geri almaması gerekir.

/// Geçişin BAŞLADIĞI öğeyi işaretler (satır, düğme).
struct GecisKaynagi: ViewModifier {
    let kod: String
    let alan: Namespace.ID?

    func body(content: Content) -> some View {
        if #available(iOS 18.0, *), let alan {
            content.matchedTransitionSource(id: kod, in: alan)
        } else {
            content
        }
    }
}

/// Geçişin VARDIĞI ekrana uygulanır; kaynakla aynı `kod`u taşımalı.
struct ZoomGecisi: ViewModifier {
    let kod: String
    let alan: Namespace.ID

    func body(content: Content) -> some View {
        if #available(iOS 18.0, *) {
            content.navigationTransition(.zoom(sourceID: kod, in: alan))
        } else {
            content
        }
    }
}

extension View {
    /// Bu görünüm, bir geçişin başlangıç karesi olsun.
    func gecisKaynagi(_ kod: String, _ alan: Namespace.ID?) -> some View {
        modifier(GecisKaynagi(kod: kod, alan: alan))
    }

    /// Bu ekran, `kod` ile işaretlenmiş öğeden büyüyerek açılsın.
    func zoomIleAcil(_ kod: String, _ alan: Namespace.ID) -> some View {
        modifier(ZoomGecisi(kod: kod, alan: alan))
    }
}

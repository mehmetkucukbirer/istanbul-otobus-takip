import SwiftUI

@main
struct OtobusumNeredeApp: App {
    var body: some Scene {
        WindowGroup {
            // Kök artık giriş ekranı; arama oradan açılıyor (4 Eylül).
            GirisGorunumu()
                .preferredColorScheme(.light)
        }
    }
}

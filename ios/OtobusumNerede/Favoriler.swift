import Foundation
import SwiftUI

/// Favori duraklar — telefonda saklanır, sunucuya gitmez.
///
/// ⚠️ NEDEN VAR (4 Eylül): giriş ekranı tasarımı favori kalbini içeriyor.
/// Çalışmayan bir kalp koymaktansa gerçekten çalıştırmak hem dürüst hem faydalı:
/// yolcu her sabah aynı durağa bakıyor, onu her seferinde aratmak gereksiz.
///
/// Sunucuda kullanıcı hesabı yok ve olmasına da gerek yok — favori tamamen
/// kişisel bir tercih. `UserDefaults` yeterli: uygulama silinmedikçe kalır.
@Observable
final class Favoriler {
    static let shared = Favoriler()

    private let anahtar = "favori_duraklar"
    private(set) var duraklar: [Durak] = []

    private init() { yukle() }

    func favoriMi(_ kod: String) -> Bool {
        duraklar.contains { $0.kod == kod }
    }

    func degistir(_ d: Durak) {
        if let i = duraklar.firstIndex(where: { $0.kod == d.kod }) {
            duraklar.remove(at: i)
        } else {
            duraklar.insert(d, at: 0)
        }
        kaydet()
    }

    private func yukle() {
        guard let veri = UserDefaults.standard.data(forKey: anahtar),
              let liste = try? JSONDecoder().decode([Durak].self, from: veri) else { return }
        duraklar = liste
    }

    private func kaydet() {
        // ⚠️ Yazma başarısız olursa sessizce geçiyoruz: favori kaydedilememesi
        //    uygulamayı çökertmeye değmez, bir sonraki dokunuşta yine denenir.
        guard let veri = try? JSONEncoder().encode(duraklar) else { return }
        UserDefaults.standard.set(veri, forKey: anahtar)
    }
}

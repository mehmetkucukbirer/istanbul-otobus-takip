import SwiftUI

/// UYGULAMADAKİ SAYFALAR — gezinmenin tek kaynağı.
///
/// ⚠️⚠️ NEDEN VAR — 4 Eylül'deki gezinme hatası (Mehmet'in bulduğu):
///   *"durak adı yazıyorum tıklıyorum benden bir daha durak adı yazmamı istiyor,
///     geri tuşuna basınca bu sefer yazdığım durağın bilgilerine gidiyor"*
///
///   Sebep: aynı NavigationStack'te İKİ FARKLI gezinme biçimi karışıyordu.
///       .navigationDestination(isPresented: $aramaAcik) { ... }   ← bayrak tabanlı
///       .navigationDestination(for: Durak.self)         { ... }   ← değer tabanlı
///   Durağa dokunulup yığına bir değer itildiğinde, bayrak tabanlı hedef yeniden
///   değerlendiriliyor ve arama ekranı SIFIRDAN kuruluyordu — yazılan metin gitmiş,
///   üstelik asıl durak ekranı onun ALTINA giriyordu. Geri basınca ortaya çıkması
///   bundandı: sayfa zaten açılmıştı, üstüne boş bir arama ekranı binmişti.
///
///   Çözüm: tek biçim. Bütün sayfalar bu enum'un birer durumu, yığın tek bir
///   `[Rota]` dizisi. Bayrak yok, çakışacak ikinci hedef yok.
enum Rota: Hashable {
    case arama
    case durak(Durak)
    /// Araç detayı — durak ekranındaki canlı otobüs satırına dokununca (10 Eylül).
    case arac(kapino: String, hat: String, yon: String, durakKodu: String, durakAdi: String)
    /// Hattın bugünkü sefer tablosu — hat başlığına dokununca (10 Eylül).
    case seferler(hat: String, yon: String, durakKodu: String)
    /// GPS'i kapalı seferin TAHMİNİ konumu (11 Eylül). Canlı araçtan ayrı bir
    /// rota: orada konum ölçülüyor, burada hesaplanıyor — ekran da farklı
    /// konuşuyor (bant + pay uyarısı).
    case seferKonum(hat: String, yon: String, kalkis: String, durakKodu: String)
}

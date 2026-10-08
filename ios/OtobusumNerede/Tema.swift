import SwiftUI

/// Görsel dil — İETT'nin SAHADAKİ akıllı durak ekranından alındı.
///
/// ⚠️ İlk sürüm koyu lacivert/kehribar bir tema kullanıyordu; o benim tahminimdi.
/// Mehmet gerçek ekranın fotoğrafını getirince görüldü ki durak ekranı AÇIK temalı:
/// mavi başlık şeridi, yeşil tablo başlığı, beyaz gövde, koyu lacivert yazı,
/// turuncu duyuru şeridi. Uygulama artık onu birebir izliyor.
///
/// Amaç: İstanbullu o ekranı zaten tanıyor. Aynı dili kullanmak uygulamayı
/// öğrenilecek yeni bir şey olmaktan çıkarıp tanıdık bir şeyin cebe girmiş hâli yapar.
enum Tema {
    // zeminler
    static let zemin   = Color(red: 0.933, green: 0.949, blue: 0.965)   // #EEF2F7 sayfa
    static let kart    = Color.white                                     // beyaz kart
    static let kart2   = Color(red: 0.965, green: 0.976, blue: 0.988)   // #F6F9FC şerit

    // başlık mavisi — Mehmet'in isteğiyle koyulaştırıldı (1 Eylül)
    static let mavi    = Color(red: 0.098, green: 0.220, blue: 0.427)   // #19386D
    static let mavi2   = Color(red: 0.165, green: 0.318, blue: 0.549)   // #2A518C
    static let maviAcik = Color(red: 0.310, green: 0.478, blue: 0.706)  // #4F7AB4 vurgu

    // İETT yeşili — tablo başlığı
    static let yesil   = Color(red: 0.243, green: 0.608, blue: 0.416)   // #3E9B6A

    // duyuru turuncusu
    static let turuncu = Color(red: 0.894, green: 0.506, blue: 0.235)   // #E4813C
    /// Başlık çiplerindeki simgeler — mavi zeminde okunur koyu turuncu
    static let turuncuKoyu = Color(red: 0.847, green: 0.400, blue: 0.078) // #D86614

    /// ⛔ İPTAL — turuncudan AYRI olmak zorunda: turuncu "gecikti" demek,
    /// kırmızı "hiç gelmeyecek" demek. İkisi karışırsa yolcu bekler durur.
    static let kirmizi = Color(red: 0.753, green: 0.231, blue: 0.212)     // #C03B36
    static let kirmiziZemin = Color(red: 0.988, green: 0.937, blue: 0.933) // #FCEFEE

    // yazı
    static let ink     = Color(red: 0.118, green: 0.165, blue: 0.247)   // #1E2A3F
    static let ink2    = Color(red: 0.322, green: 0.384, blue: 0.478)   // #52627A
    static let soluk   = Color(red: 0.541, green: 0.596, blue: 0.675)   // #8A98AC
    static let cizgi   = Color(red: 0.878, green: 0.902, blue: 0.929)   // #E0E6ED

    // hat rozeti — ekrandaki koyu lacivert
    static let rozet   = Color(red: 0.137, green: 0.196, blue: 0.302)   // #23324D

    /// Rakamlar sütun hâlinde hizalansın diye sabit genişlikli.
    static func rakam(_ boyut: CGFloat, _ agirlik: Font.Weight = .bold) -> Font {
        .system(size: boyut, weight: agirlik).monospacedDigit()
    }
    static func kucukEtiket() -> Font { .system(size: 11, weight: .medium) }
    /// Tablo başlıklarındaki gibi seyrek harfli büyük yazı
    static func sutunBasligi() -> Font { .system(size: 10, weight: .semibold) }
}

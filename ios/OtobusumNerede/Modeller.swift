import Foundation

// Sunucudan gelen JSON'un birebir karşılığı (arayuz_sunucu.py).

struct Durak: Codable, Identifiable, Hashable {
    let kod: String
    let ad: String
    let ilce: String?
    let hat_sayisi: Int
    let uzaklik_m: Int?

    /// ⚠️ Durağın NEREYE gittiği — aramadaki asıl ayırt edici (4 Eylül).
    /// "sefaköy" dört özdeş satır döndürüyordu; ad ve ilçe aynı olduğu için
    /// yolcu hangisini seçeceğini bilemiyordu. Yolun iki yakası ayrı duraktır
    /// ve ters yöne gider — bu alan onu görünür kılıyor.
    /// Sunucu eski sürümdeyse gelmez, o yüzden isteğe bağlı.
    let yonler: [String]?
    /// Duraktan geçen hatlar, doğal sırayla (89, 89A, 98…) — en fazla 6. (7 Ekim)
    let hatlar: [String]?

    var id: String { kod }
}

struct Varis: Codable, Hashable {
    let kaynak: String          // "canli" | "tarife" | "gozlem" | "iptal"
    let guven: String           // "yuksek" | "orta" | "dusuk" | "kesin"
    let dakika: Int
    let not: String
    // ⛔ iptal — İETT'nin kendi duyurusu (Bölüm 47). Tahmin değil.
    //    `varis` bu satırda boş: gelmeyecek otobüsün varış saati olmaz.
    let kalkis_yeri: String?

    // canlı
    let km: Double?
    let arac: String?
    let hiz_kmh: Int?
    // tarife — ve 11 Eylül'den beri CANLI satırda da dolu:
    // ⭐ "tahmini yapılan seferin hangi saat dakikadaki otobüs olduğunu öğreneyim"
    //    Canlı araç en güvendiğimiz satırdı ama hangi sefer olduğunu söylemiyordu.
    let kalkis: String?
    /// "tarife" → kalkış tarifedeki bir sefere oturdu (±10 dk).
    /// "olcum"  → tarife tutmadı (98 gibi bozuk tarifeler), ölçülen saat gösteriliyor.
    /// ⚠️ Ayrımı saklamıyoruz: yolcu hangisine baktığını bilmeli.
    let kalkis_kaynak: String?
    /// Aracın kalkış durağından geçtiği gerçek saat — ayrıntılı kipte gösterilir.
    let kalkis_olculen: String?
    let varis: String?
    let alt: String?
    let ust: String?
    let sure_dk: Int?
    // gözlem
    let aralik_dk: Int?
    let son_gecis_dk: Int?
    let gecikmis: Bool?

    var canliMi: Bool { kaynak == "canli" }
    var gozlemMi: Bool { kaynak == "gozlem" }
    var iptalMi: Bool { kaynak == "iptal" }
    /// 📡 Yolda ama konum bildirmiyor — ürünün asıl vaadi (PROMPT Bölüm 2).
    /// Rakip uygulamanın sustuğu yer tam burası.
    var gpsKapaliMi: Bool { kaynak == "gps_kapali" }
}

struct Gozlem: Codable, Hashable {
    let aralik_dk: Int
    let en_az: Int
    let en_cok: Int
    let olcum: Int

    /// ⭐ Yolcunun GERÇEKTE bekleyeceği süre (7 Eylül) — `aralik_dk` değil.
    /// Otobüsler konvoy halinde geldiği için ardışık aralıkların ortancası
    /// yolcunun deneyimini yansıtmıyor; bu alan her aralığı kendi uzunluğuyla
    /// ağırlıklayarak beklenen bekleme süresini veriyor. Gerekçe ve ölçümler:
    /// durakta_ne_var.gozlenen_gecisler(). Eski sunucuda yok, o yüzden isteğe bağlı.
    let bekleme_dk: Int?

    let son_gecis_dk: Int?
}

struct HatBilgisi: Codable, Identifiable, Hashable {
    let hat: String
    let yon: String
    let hedef: String
    let sira: Int
    let toplam_durak: Int
    let oran: Int
    let varislar: [Varis]
    let gozlem: Gozlem?
    var id: String { hat + yon }
}

struct Hava: Codable {
    let sicaklik: Int
    let kod: Int?

    /// WMO hava kodunu SF Symbol'a çevirir. Güneşliyken güneş, yağmurluyken
    /// bulut çıksın — sahadaki ekran da hava durumunu gösteriyor.
    var simge: String {
        switch kod ?? 0 {
        case 0:            return "sun.max.fill"
        case 1, 2:         return "cloud.sun.fill"
        case 3:            return "cloud.fill"
        case 45, 48:       return "cloud.fog.fill"
        case 51...67:      return "cloud.rain.fill"
        case 71...77:      return "cloud.snow.fill"
        case 80...82:      return "cloud.heavyrain.fill"
        case 95...99:      return "cloud.bolt.rain.fill"
        default:           return "sun.max.fill"
        }
    }
}

struct DurakCevabi: Codable {
    let kod: String
    let ad: String
    let ilce: String?
    let an: String
    let hatlar: [HatBilgisi]
    let hava: Hava?
    /// Şehir geneli trafik — başlıkta bağlam olarak (10 Eylül). Eski sunucuda yok.
    let trafik: TrafikDurumu?
}


// ─────────────────────────────────────────────────────────────────────────────
// ARAÇ DETAYI — "bu otobüs şu an nerede?" (10 Eylül)
// ─────────────────────────────────────────────────────────────────────────────

struct TrafikDurumu: Codable, Hashable {
    let deger: Int
    let durum: String        // "akıcı" | "yoğun" | "çok yoğun"
}

struct GecilenDurak: Codable, Hashable {
    let ad: String
    let sira: Int
    let saat: String
    let dk_once: Int
}

struct GelecekDurak: Codable, Hashable {
    let ad: String
    let sira: Int
    let kod: String?
    let km: Double
    /// Yolcunun beklediği durak — listede vurgulanıyor.
    let hedef_mi: Bool
}

struct AracDetay: Codable {
    /// ⭐ Bu otobüs hangi kalkışın otobüsü (11 Eylül). Sefer saati üstteki
    ///   çipten kaldırıldı; "tıklayınca görünsün" dendiği için buraya geldi.
    ///   Çıkarılamadığında nil — başlıkta hiç yazılmıyor.
    let kalkis: String?
    let kalkis_kaynak: String?

    let arac: String
    let hat: String
    let yon: String
    let hiz_kmh: Int?
    /// ⚠️ Konumun yaşı: 1 dakikalık konumla 6 dakikalık konum aynı şey değil.
    let konum_yasi_dk: Int
    let rota_oran: Int?
    let sapma_m: Int?
    let gecti: [GecilenDurak]
    let gidecek: [GelecekDurak]
    /// Otobüs yolcunun durağını geçtiyse true — ekranda uyarı gösteriliyor.
    let hedef_gecildi: Bool?
    /// Şehir geneli trafik (0-100) — yol bazlı değil, yalnızca bağlam.
    let trafik: TrafikDurumu?
}


// ─────────────────────────────────────────────────────────────────────────────
// SEFER TABLOSU — "bu hat bugün ne yaptı?" (10 Eylül)
// ─────────────────────────────────────────────────────────────────────────────

/// Tablodaki tek satır — bir sefer ve durumu.
struct SeferSatiri: Codable, Hashable {
    let kalkis: String
    /// "gecti" | "yolda" | "gps_yok" | "bekleniyor" | "veri_yok"
    let durum: String
    let gecis_saati: String?
    let arac: String?
    let dakika: Int?
    let km: Double?
    /// Tarifede karşılığı var mı — yoksa tarifenin eksikliğinin kanıtı.
    let tarifede: Bool
}

struct HatSeferleri: Codable {
    let hat: String
    let yon: String
    let durak_adi: String
    let hedef: String
    let gun: String
    /// Geçmiş günde "yolda"/"bekleniyor" olmaz — gün bitmiştir.
    let bugun_mu: Bool?
    let satirlar: [SeferSatiri]
    let sayim: [String: Int]
    let tarife_sayisi: Int
    let gozlem_sayisi: Int
    /// ⚠️ Tarife gözlemden belirgin azsa true — ekranda uyarı gösteriliyor.
    let tarife_eksik: Bool?
}

/// GPS'i kapalı bir seferin TAHMİNİ konumu — tek durak değil, BANT.
///
/// ⚠️⚠️ Neden bant: ölçüldü (11 Eylül), tahmin edilen durak ile aracın gerçekten
/// görüldüğü durak arasında ortanca 4 durak sapma var. Tek durak göstermek
/// yolcuyu ortalama dört durak yanıltmak olurdu. Kapsama da sınırlı: hat-yön
/// çiftlerinin yalnız %34'ünde ölçülmüş parça süresi var; kalanında
/// `konum_var == false` gelir ve ekran bunu açıkça söyler.
struct SeferKonumu: Codable, Hashable {
    let hat: String
    let yon: String
    let kalkis: String
    let durak_adi: String
    let gecen_dk: Int
    let pay_durak: Int
    let toplam_durak: Int
    let konum_var: Bool
    let duraklar: [SeferDuragi]
    let not: String?

    // konum_var == true ise dolu
    let tahmini_sira: Int?
    let bant_bas: Int?
    let bant_son: Int?
    let bant_bas_ad: String?
    let bant_son_ad: String?
    let hedef_sira: Int?
    let hedef_gecilmis_olabilir: Bool?
}

struct SeferDuragi: Codable, Hashable {
    let sira: Int
    let ad: String
    let kod: String?
    let bantta: Bool
    let hedef_mi: Bool
}

/// `/api/tunel` cevabı — ayrı ağdan erişim için güncel tünel adresi.
struct TunelCevabi: Codable {
    let adres: String?
    /// Adres panosunun (ntfy.sh) gizli adı — 8 Ekim.
    let pano: String?
}

import CryptoKit
import Foundation

/// Sunucuyla konuşan katman.
///
/// ⚠️ Veri şu an Mehmet'in bilgisayarındaki Python sunucusundan geliyor
/// (`arayuz_sunucu.py`, port 8790). Yani telefon ile bilgisayar **aynı Wi-Fi'de**
/// olmalı. Adres Ayarlar ekranından değiştirilebiliyor.
///
/// ⚠️⚠️ ADRES NEDEN IP DEĞİL, `.local` (4 Eylül — Mehmet'in yaşadığı arıza):
///   Varsayılan sabit bir IP'ydi (10.100.35.107). Bilgisayar fişten çıkıp başka
///   bir ağa bağlanınca IP 192.168.1.119 oldu ve uygulama "sunucu çalışmıyor"
///   demeye başladı — oysa sunucu gayet çalışıyordu, sadece adres eskimişti.
///
///   `Mehmet-MacBook-Air-2.local` macOS'un Bonjour/mDNS adı: ağ değişse de,
///   IP değişse de aynı kalır. Aynı Wi-Fi'de olduğu sürece hep bulur.
///   Ölçüldü (4 Eylül): hem `.local` hem yeni IP üzerinden HTTP 200.
///
///   Info.plist'te gereken izinler zaten var:
///     NSAllowsLocalNetworking · NSLocalNetworkUsageDescription
@Observable
final class Servis {
    static let shared = Servis()

    // ⚠️⚠️ NEDEN `didSet` DEĞİL (4 Ekim'de bulunan hata): bu sınıf `@Observable`.
    //   Makro saklanan özellikleri sarmalıyor ve `didSet` gözlemcisi güvenilir
    //   tetiklenmiyordu — ölçüldü: uygulama çalışıp adresi kullanmasına rağmen
    //   UserDefaults'ta `sunucu` ve `tunelAdres` BOŞ kaldı. Telefonda anahtar
    //   girilseydi o da kaydedilmeyecekti. Yazma artık açıkça set içinde.
    private var _sunucu: String
    var sunucu: String {
        get { _sunucu }
        set { _sunucu = newValue; UserDefaults.standard.set(newValue, forKey: "sunucu") }
    }

    /// ⭐ ERİŞİM ANAHTARI (4 Ekim) — sunucu internete açıldığındaki tek koruma.
    /// ⚠️ Koda GÖMÜLMÜYOR: kaynak kodda duran sır, kodu gören herkesin sırrıdır.
    ///   Mac'te `veri/anahtar.txt` dosyasında duruyor, buraya Ayarlar'dan giriliyor.
    private var _anahtar: String
    var anahtar: String {
        get { _anahtar }
        set { _anahtar = newValue; UserDefaults.standard.set(newValue, forKey: "anahtar") }
    }

    /// ⭐ TÜNEL ADRESİ (4 Ekim) — Mac ile telefon AYRI AĞLARDAYKEN kullanılır.
    /// ⚠️⚠️ Ücretsiz Cloudflare tünelinin adresi her başlangıçta DEĞİŞİYOR.
    ///   Bu yüzden elle girilmiyor: telefon ev ağındayken sunucudan öğrenip
    ///   saklıyor (`/api/tunel`), dışarıdayken onu deniyor. Yani eve her
    ///   gelişte adres kendiliğinden tazeleniyor.
    private var _tunelAdres: String
    var tunelAdres: String {
        get { _tunelAdres }
        set { _tunelAdres = newValue; UserDefaults.standard.set(newValue, forKey: "tunelAdres") }
    }

    /// Bu oturumda ÇALIŞTIĞI görülen adres. Kalıcı değil — uygulama her
    /// açılışta kullanıcının kendi ayarından başlar, oradan yedeklere düşer.
    private var aktifAdres: String?
    private var sonTunelTazeleme: Date?

    /// ⭐ ADRES PANOSU (8 Ekim) — dışarıdayken tünel adresi değiştiyse telefonun
    /// yeni adresi Mac'e sormadan öğrendiği yer. Panonun adı evdeyken sunucudan
    /// öğreniliyor (`/api/tunel`). Ayrıntı: pano.py ve PROJE DURUMU Bölüm 82.
    private var panoKonu: String {
        get { UserDefaults.standard.string(forKey: "panoKonu") ?? "" }
        set { UserDefaults.standard.set(newValue, forKey: "panoKonu") }
    }
    /// Kabul edilmiş en yeni ilanın zamanı — daha eski bir ilan (tekrar saldırısı
    /// ya da panodaki bayat kayıt) yeni adresin üstüne yazılamasın.
    private var sonPanoZamani: Int {
        get { UserDefaults.standard.integer(forKey: "sonPanoZamani") }
        set { UserDefaults.standard.set(newValue, forKey: "sonPanoZamani") }
    }

    private init() {
        // ⚠️ SIRA ÖNEMLİ: Swift'te bütün saklanan özellikler atanmadan `self`'e
        //    dokunulamaz. `sunucu`nun didSet'i UserDefaults'a yazarken self'i
        //    kullandığı için `anahtar` ondan ÖNCE atanmalı.
        _anahtar = UserDefaults.standard.string(forKey: "anahtar") ?? ""
        _tunelAdres = UserDefaults.standard.string(forKey: "tunelAdres") ?? ""

        let kayitli = UserDefaults.standard.string(forKey: "sunucu")
        // ⚠️ Eski sürümlerin kaydettiği sabit IP'yi bir kez temizliyoruz: kullanıcı
        //    kendi adresini yazmadıysa o eski IP kalıcı olarak yanlış cevap verirdi.
        if let k = kayitli, k.contains("10.100.35.107") {
            _sunucu = Servis.varsayilanAdres
            UserDefaults.standard.set(_sunucu, forKey: "sunucu")
        } else {
            _sunucu = kayitli ?? Servis.varsayilanAdres
        }
    }

    /// Bonjour adı — IP değişse de sabit kalır (gerekçe yukarıda).
    static let varsayilanAdres = "http://Mehmet-MacBook-Air-2.local:8790"


    enum Hata: LocalizedError {
        case adres, ag(String), anahtarYok
        var errorDescription: String? {
            switch self {
            case .adres: return "Sunucu adresi geçersiz."
            case .ag(let m): return m
            // ⚠️ Hata mesajı NE YAPILACAĞINI söylüyor. "401 Unauthorized"
            //    kullanıcıya hiçbir şey anlatmaz.
            case .anahtarYok:
                return "Erişim anahtarı eksik ya da yanlış. Ayarlar'dan gir — "
                     + "anahtar bilgisayarındaki veri/anahtar.txt dosyasında."
            }
        }
    }

    /// Denenecek adresler, en olasıdan en son çareye.
    ///
    /// ⚠️ SIRA KASITLI: önce kullanıcının kendi ayarı, sonra `.local` (ev ağında
    ///   IP değişse de sabit kalır), en son tünel (internet üzerinden dolaşır,
    ///   yani yavaş ve yalnız ayrı ağdayken gerekli).
    private var adaylar: [String] {
        var a: [String] = []
        if let k = aktifAdres { a.append(k) }          // bu oturumda çalışan
        if !a.contains(sunucu) { a.append(sunucu) }
        if !a.contains(Servis.varsayilanAdres) { a.append(Servis.varsayilanAdres) }
        if !tunelAdres.isEmpty, !a.contains(tunelAdres) { a.append(tunelAdres) }
        return a
    }

    private func getir<T: Decodable>(_ yol: String, _ tip: T.Type) async throws -> T {
        var sonHata: Error?
        for aday in adaylar {
            do {
                let v = try await istek(aday + yol, tip)
                aktifAdres = aday
                await tunelTazele()
                return v
            } catch let e as DecodingError {
                throw Hata.ag("Sunucu beklenmedik cevap verdi. (\(e))")
            } catch Hata.anahtarYok {
                // ⚠️ Yetki hatasında YEDEK ADRES DENEME: adres doğru, sorun
                //    anahtarda. Yedeğe düşmek gerçek sebebi gizlerdi.
                throw Hata.anahtarYok
            } catch {
                sonHata = error
                continue
            }
        }
        _ = sonHata
        // ⭐ Son çare — ADRES PANOSU: tünel yeniden başladıysa adresi değişmiştir;
        //    yenisini Mac'e sormadan panodan öğren ve BİR KEZ daha dene.
        if let yeni = await panodanAdres(), yeni != tunelAdres {
            tunelAdres = yeni
            if let v = try? await istek(yeni + yol, tip) {
                aktifAdres = yeni
                return v
            }
        }
        throw Hata.ag("Sunucuya ulaşılamadı. Bilgisayar açık mı? "
                    + "Tünel yeniden başlıyorsa birkaç dakika içinde düzelir.")
    }

    /// Panodaki EN YENİ GEÇERLİ ilanın adresi — yoksa nil.
    ///
    /// ⚠️⚠️ İMZA DOĞRULANMADAN HİÇBİR ADRESE GİDİLMİYOR. ntfy konuları herkese
    ///   açık yazılabilir; sahte bir adres kabul edilse telefon X-Anahtar'ını
    ///   oraya gönderirdi. İmza = HMAC-SHA256(anahtar, "adres|zaman"); anahtarı
    ///   bilmeyen geçerli imza üretemez. Python tarafıyla birebir uyumu ayrı bir
    ///   Swift betiğiyle gerçek ilan üzerinde sınandı (8 Ekim).
    private func panodanAdres() async -> String? {
        guard !panoKonu.isEmpty, !anahtar.isEmpty,
              let url = URL(string: "https://ntfy.sh/\(panoKonu)/json?poll=1&since=12h") else { return nil }
        var r = URLRequest(url: url); r.timeoutInterval = 10
        guard let (veri, _) = try? await URLSession.shared.data(for: r) else { return nil }
        let kilit = SymmetricKey(data: Data(anahtar.utf8))
        var enIyi: (adres: String, zaman: Int)?
        for satir in String(decoding: veri, as: UTF8.self).split(separator: "\n") {
            guard let olay = try? JSONSerialization.jsonObject(with: Data(satir.utf8)) as? [String: Any],
                  olay["event"] as? String == "message",
                  let mesaj = olay["message"] as? String,
                  let ilan = try? JSONSerialization.jsonObject(with: Data(mesaj.utf8)) as? [String: Any],
                  let adres = ilan["adres"] as? String, let zaman = ilan["zaman"] as? Int,
                  let gelen = ilan["imza"] as? String else { continue }
            let beklenen = HMAC<SHA256>.authenticationCode(for: Data("\(adres)|\(zaman)".utf8), using: kilit)
                .map { String(format: "%02x", $0) }.joined()
            guard beklenen == gelen, zaman >= sonPanoZamani,
                  adres.hasPrefix("https://") else { continue }
            if enIyi == nil || zaman > enIyi!.zaman { enIyi = (adres, zaman) }
        }
        guard let s = enIyi else { return nil }
        sonPanoZamani = s.zaman
        return s.adres
    }

    /// Ev ağındayken güncel tünel adresini öğrenip saklar.
    ///
    /// ⚠️ YALNIZ YEREL BAĞLANTIDA çalışır: tünel üzerinden bağlıyken kendi
    ///   adresini sormanın anlamı yok. Ve 10 dakikada birden sık sorulmuyor —
    ///   adres yalnız tünel yeniden başlayınca değişir, her istekte sormak
    ///   bedava trafik olurdu.
    private func tunelTazele() async {
        guard let k = aktifAdres, k.contains(".local") || k.contains("://192.168.")
                                   || k.contains("://10.") || k.contains("://172.") else { return }
        if let s = sonTunelTazeleme, Date().timeIntervalSince(s) < 600 { return }
        sonTunelTazeleme = Date()
        if let c = try? await istek(k + "/api/tunel", TunelCevabi.self) {
            if let a = c.adres, !a.isEmpty, a != tunelAdres { tunelAdres = a }
            if let p = c.pano, !p.isEmpty, p != panoKonu { panoKonu = p }
        }
    }

    private func istek<T: Decodable>(_ tam: String, _ tip: T.Type) async throws -> T {
        guard let url = URL(string: tam) else { throw Hata.adres }
        var r = URLRequest(url: url)
        r.timeoutInterval = 12
        r.cachePolicy = .reloadIgnoringLocalCacheData
        // ⚠️ Anahtar BAŞLIKTA gidiyor, adreste değil: URL'ler günlüklere,
        //    tarayıcı geçmişine ve ara sunucu kayıtlarına düşer.
        if !anahtar.isEmpty { r.setValue(anahtar, forHTTPHeaderField: "X-Anahtar") }
        let (veri, cevap) = try await URLSession.shared.data(for: r)
        if let h = cevap as? HTTPURLResponse {
            if h.statusCode == 401 { throw Hata.anahtarYok }
            // ⚠️⚠️ JSON DEĞİLSE BU BİZİM SUNUCU DEĞİL (8 Ekim'de bulundu).
            //   Sunucumuz her cevabı JSON döndürüyor (200, 404, 401 doğrulandı).
            //   Ölü bir tünel adresi ise Cloudflare'in HTML hata sayfasını
            //   döndürüyor (HTTP 530); kafe Wi-Fi'larının giriş sayfası da 200 +
            //   HTML. Eskiden bu JSON diye çözülmeye çalışılıyor, DecodingError
            //   atılıyor ve `getir` HEMEN vazgeçiyordu — sıradaki adrese ve
            //   ADRES PANOSUNA hiç geçmeden. Yani pano tam ihtiyaç anında devreye
            //   girmeyecekti. Artık "bu adres çalışmıyor" sayılıp sıradakine geçiliyor.
            let tur = h.value(forHTTPHeaderField: "Content-Type") ?? ""
            if !tur.contains("json") { throw URLError(.cannotConnectToHost) }
        }
        return try JSONDecoder().decode(tip, from: veri)
    }

    /// Konum verilirse sonuçlar uzaklıkla gelir ve aynı adlılar en yakından
    /// uzağa sıralanır ("ATATÜRK CADDESİ" 33 ayrı durak). (7 Ekim)
    func ara(_ metin: String, konum: (enlem: Double, boylam: Double)? = nil) async throws -> [Durak] {
        let q = metin.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        var yol = "/api/ara?q=" + q
        if let k = konum { yol += "&e=\(k.enlem)&b=\(k.boylam)" }
        return try await getir(yol, [Durak].self)
    }

    func yakin(enlem: Double, boylam: Double) async throws -> [Durak] {
        try await getir("/api/yakin?e=\(enlem)&b=\(boylam)", [Durak].self)
    }

    func aracDetay(arac: String, hat: String, yon: String, durak: String) async throws -> AracDetay {
        // ⚠️ `.urlQueryAllowed` mevcut `ara()` ile aynı küme — araç kodları
        //    (A-1738) ve hat kodları (98AB) zaten güvenli karakterler.
        let k = { (x: String) in x.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? x }
        return try await getir("/api/arac?kapino=\(k(arac))&hat=\(k(hat))&yon=\(k(yon))&durak=\(k(durak))",
                               AracDetay.self)
    }

    /// GPS'i kapalı seferin tahmini konumu (bant). Gerekçesi SeferKonumu'nda.
    func seferKonumu(hat: String, yon: String, kalkis: String,
                     durak: String) async throws -> SeferKonumu {
        let k = { (x: String) in x.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? x }
        return try await getir("/api/sefer?hat=\(k(hat))&yon=\(k(yon))&kalkis=\(k(kalkis))&durak=\(k(durak))",
                               SeferKonumu.self)
    }

    func hatSeferleri(hat: String, yon: String, durak: String,
                      gun: String? = nil) async throws -> HatSeferleri {
        let k = { (x: String) in x.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? x }
        var yol = "/api/hat?hat=\(k(hat))&yon=\(k(yon))&durak=\(k(durak))"
        if let g = gun { yol += "&gun=\(k(g))" }
        return try await getir(yol, HatSeferleri.self)
    }

    func durak(_ kod: String) async throws -> DurakCevabi {
        try await getir("/api/durak?kod=" + kod, DurakCevabi.self)
    }
}

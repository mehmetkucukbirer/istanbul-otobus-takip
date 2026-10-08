import SwiftUI

/// İETT ve İBB amblemlerinin sadeleştirilmiş beyaz çizimleri.
///
/// ⚠️ Gerçek amblemler sahadaki ekran fotoğrafından çıkarılmaya çalışıldı ama
/// çözünürlük çok düşük ve cam yansımasıyla kaplıydı — varlık olarak kullanılamadı.
/// Bunlar SwiftUI'da çizilmiş sade karşılıkları. Resmi logo dosyaları (şeffaf PNG)
/// bulunursa `Assets.xcassets`'e konup burası değiştirilebilir.
///
/// ⚠️ ŞEKİLLERE DOKUNULMAYACAK (Mehmet'in isteği, 1 Eylül). Yalnızca `boyut` ve
/// `renk` ayarlanır. Renk saf beyaz değil, çok hafif kırık beyaz — mavi zeminde
/// saf beyaz fazla sert duruyordu.
private let amblemRengi = Color(red: 0.914, green: 0.937, blue: 0.965)   // #E9EFF6

struct IETTAmblemi: View {
    var boyut: CGFloat = 44

    var body: some View {
        // ⚠️ ŞEKLE HİÇ DOKUNULMUYOR. Resmi amblem dosyası şeffaf ŞABLON görsele
        //    çevrildi (alfa korundu, şekil olduğu gibi). Rengi uygulama veriyor —
        //    İBB amblemiyle birebir aynı renk.
        Image("IETTAmblem")
            .renderingMode(.template)
            .resizable()
            .scaledToFit()
            .foregroundStyle(amblemRengi)
            .frame(height: boyut)
            .accessibilityLabel("İETT")
    }
}

struct IBBAmblemi: View {
    var boyut: CGFloat = 42

    var body: some View {
        // ⚠️ ŞEKLE HİÇ DOKUNULMUYOR (Mehmet'in isteği). Resmi amblem dosyası
        //    şeffaf ŞABLON görsele çevrildi: beyaz zemin alfa'ya dönüştürüldü,
        //    şeklin kendisi olduğu gibi korundu. Şablon olduğu için rengi
        //    uygulama belirliyor — burada beyaz.
        Image("IBBAmblem")
            .renderingMode(.template)
            .resizable()
            .scaledToFit()
            .foregroundStyle(amblemRengi)
            .frame(height: boyut)
            .accessibilityLabel("İstanbul Büyükşehir Belediyesi")
    }
}


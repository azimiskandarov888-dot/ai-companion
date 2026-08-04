// Three faces, three jobs — the distinction that carries most of the app's soul.
//
//   Soft (rounded)   — the app's VOICE: the warm lines, titles, buttons. Round
//                      terminals, no corners, real weight. See below.
//   SF Pro (sans)    — the app LABELLING: settings rows, prices, fine print.
//                      Neutral, quiet, gets out of the way.
//   New York (serif) — everything a PERSON wrote: the scroll, the diary, the
//                      quote. Ink on paper is allowed a sharp edge.
//
// All three carry Cyrillic and Dynamic Type.

import SwiftUI
import UIKit

enum AppType {

    // MARK: - The soft face
    //
    // Nunito if it has been added to the project, SF Rounded otherwise.
    //
    // Both are round-terminal faces with full Cyrillic — no pointed serifs, no
    // hard corners anywhere. Nunito is warmer and a little more human, and is
    // free under the SIL Open Font License; SF Rounded ships with the system,
    // so the app is never waiting on a download to look right. See BUILD.md for
    // the three steps to add Nunito.
    //
    // WEIGHT MATTERS AS MUCH AS SHAPE. Light was the mistake: thin strokes on a
    // bright photograph read as wiry and hard however round the letterforms
    // are. Medium gives the letters body, and body is what reads as soft.

    private static let hasNunito = !UIFont.fontNames(forFamilyName: "Nunito").isEmpty

    static func soft(_ size: CGFloat, _ weight: Font.Weight = .medium) -> Font {
        guard hasNunito else {
            return .system(size: size, weight: weight, design: .rounded)
        }
        let face: String
        switch weight {
        case .light:    face = "Nunito-Light"
        case .regular:  face = "Nunito-Regular"
        case .semibold: face = "Nunito-SemiBold"
        case .bold:     face = "Nunito-Bold"
        default:        face = "Nunito-Medium"
        }
        return .custom(face, size: size)
    }

    // MARK: - The voice — the few lines that carry the app's feeling

    /// 33 / 1.24 soft, Medium. Sign-in's warm line, "Take care of him".
    static let hero = soft(33, .medium)
    /// 27 soft, SemiBold. Screen titles.
    static let title = soft(27, .semibold)
    /// 19 / 1.5 soft, Regular. The sentence under a hero line.
    static let lede = soft(19, .regular)

    /// 17 / Regular. Body, list labels.
    static let body = Font.system(size: 17)
    /// 17 soft, SemiBold. Button labels.
    static let button = soft(17, .semibold)
    /// 15 / Regular. Sub-lines, list values, plan details.
    static let secondary = Font.system(size: 15)
    /// 13. Fine print, the status word, prices above the button.
    static let caption = Font.system(size: 13)
    /// 11. Legal, version numbers.
    static let micro = Font.system(size: 11)

    // MARK: - Serif — what a person wrote

    /// 22 / Medium serif. The heading on the scroll, the diary's title page.
    static let writtenHeading = Font.system(size: 22, weight: .medium, design: .serif)
    /// 18 / 1.66 serif. The user's own writing on the scroll.
    static let writtenBody = Font.system(size: 18, design: .serif)
    /// 15 / 1.72 serif italic. His diary — his handwriting.
    static let diaryBody = Font.system(size: 15, design: .serif).italic()
    /// 20 / 1.55 serif. The friendship quote — the one thing on screen 4 you
    /// are meant to stop and read, so it is sized to be read. Not italic:
    /// italic Cyrillic in a serif turns into near-cursive letterforms that are
    /// markedly harder to read than the upright ones.
    static let quote = Font.system(size: 20, design: .serif)
    /// 11 serif. Page numbers — the only faint text in the app.
    static let pageNumber = Font.system(size: 11, design: .serif)

    // MARK: - Line spacing
    //
    // SwiftUI's `lineSpacing` is the gap BETWEEN lines, not the line height, so
    // these are (lineHeight − fontSize) rather than the ratios themselves.

    static let heroLeading: CGFloat      = 33 * 1.24 - 33   // ≈ 7.9
    static let ledeLeading: CGFloat      = 19 * 1.50 - 19   // ≈ 9.5
    static let writtenLeading: CGFloat   = 18 * 1.66 - 18   // ≈ 11.9
    static let diaryLeading: CGFloat     = 15 * 1.72 - 15   // ≈ 10.8
    static let quoteLeading: CGFloat     = 20 * 1.55 - 20   // ≈ 11.0
    static let bodyLeading: CGFloat      = 17 * 1.50 - 17   // ≈ 8.5

    /// The status word under the orb carries a little tracking so it reads as a
    /// breath rather than a label.
    static let statusTracking: CGFloat = 0.07 * 13
}

extension View {
    /// Sans text that scales with Dynamic AppType.
    func appFont(_ font: Font, leading: CGFloat? = nil) -> some View {
        self.font(font).lineSpacing(leading ?? 0)
    }
}

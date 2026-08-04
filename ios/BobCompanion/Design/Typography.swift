// Two typefaces, two jobs — the distinction that carries most of the app's soul.
//
//   SF Pro (sans)    — everything the APP says: buttons, labels, settings.
//                      Neutral, quiet, gets out of the way.
//   New York (serif) — everything a PERSON wrote: the scroll, the diary, the
//                      quote. Warm, and unmistakably hand-set.
//
// Both are system faces, so they carry Dynamic Type for free and cost nothing to
// ship. Every size below scales with the user's text size (`relativeTo:`), which
// is why no view in this app may be a fixed-height box.

import SwiftUI

enum AppType {

    // MARK: - The voice — the few lines that carry the app's feeling
    //
    // These are the only sentences in the app trying to make you feel
    // something, and a system sans says them like a settings label — correct,
    // and completely flat. They get their own face.

    /// 32 / 1.22 ROUNDED, Light. Sign-in's warm line, "Take care of him".
    ///
    /// Rounded, not serif. A serif — even at Light — has pointed terminals and
    /// sharp bracketed joints; every letter ends in a fine hard tip, and no
    /// amount of softening the shadow behind it changes that. The letterforms
    /// themselves were the sharpness. SF Rounded has no corners anywhere: every
    /// stroke ends in a circle. It is the softest face on the system, and next
    /// to a photograph of leaves and light it reads as warm rather than cut.
    ///
    /// Serif is still used, deliberately, for the things a PERSON wrote — the
    /// scroll, the diary, the quote. Ink on paper should have a sharp edge.
    /// That contrast is now doing real work instead of being decoration.
    static let hero = Font.system(size: 32, weight: .light, design: .rounded)
    /// 27 / Regular rounded. Screen titles.
    static let title = Font.system(size: 27, weight: .regular, design: .rounded)
    /// 19 / 1.5 rounded, Light. The sentence under a hero line.
    static let lede = Font.system(size: 19, weight: .light, design: .rounded)
    /// 17 / Regular. Body, list labels.
    static let body = Font.system(size: 17)
    /// 17 / Semibold. Button labels.
    static let button = Font.system(size: 17, weight: .semibold)
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
    /// 14 / 1.6 serif italic. The friendship quote.
    static let quote = Font.system(size: 14, design: .serif).italic()
    /// 11 serif. Page numbers — the only faint text in the app.
    static let pageNumber = Font.system(size: 11, design: .serif)

    // MARK: - Line spacing
    //
    // SwiftUI's `lineSpacing` is the gap BETWEEN lines, not the line height, so
    // these are (lineHeight − fontSize) rather than the ratios themselves.

    static let heroLeading: CGFloat      = 32 * 1.22 - 32   // ≈ 7.0
    static let ledeLeading: CGFloat      = 19 * 1.50 - 19   // ≈ 9.5
    static let writtenLeading: CGFloat   = 18 * 1.66 - 18   // ≈ 11.9
    static let diaryLeading: CGFloat     = 15 * 1.72 - 15   // ≈ 10.8
    static let quoteLeading: CGFloat     = 14 * 1.60 - 14   // ≈ 8.4
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

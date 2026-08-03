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

    // MARK: - Sans — what the app says

    /// 30 / 1.26, Light. Sign-in's warm line, "Take care of him".
    static let hero = Font.system(size: 30, weight: .light)
    /// 24 / Semibold. Screen titles.
    static let title = Font.system(size: 24, weight: .semibold)
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

    static let heroLeading: CGFloat      = 30 * 1.26 - 30   // ≈ 7.8
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

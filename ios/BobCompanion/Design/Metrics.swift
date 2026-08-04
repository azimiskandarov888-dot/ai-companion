// Where things sit — "look high, tap low".
//
// The design was drawn on a 430 × 932 pt canvas (iPhone Pro Max). Rather than
// hard-coding those points, every vertical position is expressed as a FRACTION
// of the real screen height, so the rhythm survives on a small iPhone and on a
// large one. The comments give the original canvas value so the design and the
// code can always be checked against each other.
//
//   What you LOOK at  → the optical centre, 45.5 % from the top.
//                       The optical centre of a rectangle sits slightly above
//                       the true middle; anything at exact 50 % reads as low.
//   What you TAP      → the bottom third, where the thumb reaches and tap
//                       accuracy is far higher.
//
// Nothing important ever sits in the top third.

import SwiftUI

enum Metrics {

    // MARK: - The vertical rhythm

    /// 45.5 % — y 424 of 932. The orb's centre and the scroll's centre.
    static let opticalCentre: CGFloat = 0.455
    /// 66.6 % — y 621. Primary controls live below this line.
    static let thumbZoneTop: CGFloat = 0.666
    /// 38 % — the keyboard's share of the screen (354 of 932).
    static let keyboardHeight: CGFloat = 0.38
    /// 62 % — y 578, where the keyboard's top edge lands.
    static let keyboardTop: CGFloat = 1 - keyboardHeight

    /// While writing, the whole scroll sits between these two lines — clear of
    /// the keyboard, optically centred in what's left. (112 → 466 of 932.)
    static let scrollWritingTop: CGFloat = 0.120
    static let scrollWritingBottom: CGFloat = 0.500

    /// The confirm button's blurred bar while writing (508 → 578 of 932).
    static let confirmBarTop: CGFloat = 0.545

    // MARK: - Spacing & shape

    static let sideMargin: CGFloat = 24
    static let groupSpacing: CGFloat = 24
    static let cardPadding: CGFloat = 20

    static let cardRadius: CGFloat = 20        // groups, cards, panels
    static let buttonRadius: CGFloat = 26      // near-pill
    static let buttonHeight: CGFloat = 56
    static let sheetRadius: CGFloat = 28
    static let parchmentRadius: CGFloat = 5    // paper isn't very round
    static let boardRadius: CGFloat = 7        // the diary's boards

    static let rowHeight: CGFloat = 56
    static let dividerInset: CGFloat = 18
    static let minTouch: CGFloat = 44

    /// The blur behind every translucent panel.
    static let panelBlur: CGFloat = 20

    // MARK: - The scroll

    static let rollerWidth: CGFloat = 28
    /// How far the paper is inset from the ends of its rollers.
    ///
    /// Exactly the width of a brass cap, because the caps sit ON TOP of the
    /// ends of the wood: the VISIBLE run of wood is the span between them, and
    /// that is what the paper has to match. Inset by less and the paper runs on
    /// underneath the caps and reads as oversized — which is what it did at 13.
    static let paperInset: CGFloat = brassCapSize.height
    static let brassCapSize = CGSize(width: 36, height: 18)
    static let scrollWidth: CGFloat = 366        // of a 430 canvas
    static let ledgerRuleSpacing: CGFloat = 30

    // MARK: - The orb (a placeholder circle until the owner's art lands)

    static let orbResting: CGFloat = 144
    static let orbListening: CGFloat = 150
    static let orbThinking: CGFloat = 146
    static let orbSpeaking: CGFloat = 156

    /// 56.9 % — y 530. The status word, below him.
    static let statusWordY: CGFloat = 0.569

    // MARK: - Helpers

    /// Turn a fraction of the canvas into points for this device.
    static func y(_ fraction: CGFloat, in height: CGFloat) -> CGFloat {
        height * fraction
    }
}

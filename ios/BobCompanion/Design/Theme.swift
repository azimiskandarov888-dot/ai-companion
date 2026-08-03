// "Sunlight through leaves" — the app's one colour system, in the Lamplight
// direction: golden hour, and the objects have weight.
//
// Green is the world (grass, leaves, moss); gold is the light falling on it
// (sun, flowers). Mostly deep green shade, with sunlight breaking through.
//
// Everything lives on one of two surfaces, and that alone decides text colour:
//   • over a photograph — the companion screen, sign-in, settings, all chrome
//   • parchment — anything written: the scroll, the diary book
//
// Rules worth keeping:
//   • Never pure white text or pure black panels — that reads as a tech app.
//   • Never blue, purple, or grey-blue. Nothing here is cold.
//   • Gold accents ONE action per screen; if everything glows, nothing does.
//   • Text over a photograph always sits on a scrim, never on a cropped photo.
//
// Every text pairing below is contrast-checked (WCAG AA at body size or better).

import SwiftUI

enum Theme {

    // MARK: - Over a photograph (and all dark chrome)

    static let night      = Color(hex: 0x0E1210)   // deepest background
    static let bark       = Color(hex: 0x1B211A)   // solid panel fallback
    static let barkRaised = Color(hex: 0x242B21)

    /// Text over a photograph or dark panel.
    static let linen  = Color(hex: 0xEFE9D8)       // primary   (15.6:1 on night)
    static let sage   = Color(hex: 0xBCC3AC)       // secondary (10.4:1)
    static let lichen = Color(hex: 0x8A9280)       // tertiary  (5.9:1)

    // MARK: - Parchment (the scroll, the diary)

    static let parchment     = Color(hex: 0xEFE2C4)  // the scroll's paper
    static let parchmentLeaf = Color(hex: 0xE8DBBC)  // the book's leaves
    static let parchmentEdge = Color(hex: 0xCBB88F)

    /// Text on parchment. Ink is a very dark warm brown, never black — that is
    /// the difference between handwriting and a print-out.
    static let ink      = Color(hex: 0x2E2718)     // primary   (12.1:1)
    static let inkSoft  = Color(hex: 0x574C36)     // secondary (6.9:1)
    static let inkFaint = Color(hex: 0x8A7C60)     // page numbers ONLY

    // MARK: - Leaf (green — the world)

    static let leaf900 = Color(hex: 0x1F2818)
    static let leaf700 = Color(hex: 0x37452A)
    static let leaf600 = Color(hex: 0x4A5C36)
    static let leaf500 = Color(hex: 0x5E7442)      // the quiet primary
    static let leaf400 = Color(hex: 0x7B9455)
    static let leaf300 = Color(hex: 0x9DB477)

    // MARK: - Sun (gold — the light)

    static let sun700 = Color(hex: 0x7E5A14)
    static let sun600 = Color(hex: 0xA9863A)       // the chosen-card hairline
    static let sun500 = Color(hex: 0xC9982F)
    static let sun400 = Color(hex: 0xE3B75A)       // THE accent, one per screen
    static let sun300 = Color(hex: 0xF2D188)       // the caution on screen 4

    /// Label on a filled sun-gold button (9.3:1).
    static let onSun = Color(hex: 0x191E14)

    // MARK: - Wood & brass (the scroll's rollers, the book's boards)

    static let woodDark   = Color(hex: 0x3F2E10)
    static let woodMid    = Color(hex: 0x4E3A14)
    static let woodLight  = Color(hex: 0x6A5330)
    static let brassDark  = Color(hex: 0x8E6C2A)
    static let brassLight = Color(hex: 0xE6CB8C)
    static let brass      = Color(hex: 0xA9863A)
    static let boardOuter = Color(hex: 0x3A2C1C)
    static let boardInner = Color(hex: 0x241A10)

    // MARK: - Semantic

    /// Parting with a friend is serious — but it is never an alarm.
    static let clay = Color(hex: 0xD2735A)

    // MARK: - Surfaces laid over a photograph

    /// The translucent panel fill used by every card, group and quiet button.
    /// Sits over a 20 pt blur of the photograph beneath.
    static let panelFill = Color(hex: 0x141813, alpha: 0.52)
    static let panelFillSolid = Color(hex: 0x1B211A, alpha: 0.92)   // Reduce Transparency

    static let hairline = Color(hex: 0xEFE9D8, alpha: 0.16)
    static let divider  = Color(hex: 0xEFE9D8, alpha: 0.10)
    static let ringUnchosen = Color(hex: 0xEFE9D8, alpha: 0.28)

    /// Bottom-up scrim that makes text readable on a photograph. Text sits over
    /// the dark end — never over the busy middle.
    static var bottomScrim: LinearGradient {
        LinearGradient(
            stops: [
                .init(color: Color(hex: 0x0A0E0A, alpha: 0.90), location: 0.00),
                .init(color: Color(hex: 0x0A0E0A, alpha: 0.45), location: 0.38),
                .init(color: Color(hex: 0x0A0E0A, alpha: 0.00), location: 0.72),
            ],
            startPoint: .bottom, endPoint: .top
        )
    }

    /// A soft radial plate behind a hero line, so it carries contrast without
    /// darkening the whole frame.
    static var heroPlate: RadialGradient {
        RadialGradient(
            colors: [Color(hex: 0x0A0E0A, alpha: 0.52), Color(hex: 0x0A0E0A, alpha: 0.0)],
            center: .center, startRadius: 0, endRadius: 240
        )
    }
}

extension Color {
    /// `Color(hex: 0x7B9455)` — hex codes live in this file and nowhere else.
    init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red:   Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue:  Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}

// "Sunlight through leaves" — the app's one color system.
//
// Green is the world (grass, leaves, moss); gold is the light falling on it
// (sun, flowers). Mostly deep green shade, with sunlight breaking through.
//
// Everything lives on one of two surfaces, and that alone decides text color:
//   • night     — the app itself: companion screen, settings, chrome.
//   • parchment — anything written: the scrolls, the diary book.
//
// Rules worth keeping (see ios/design/palette.html for the full system):
//   • Never pure white text or pure black backgrounds — that reads as a tech app.
//   • Never blue, purple, or gray-blue. Nothing here is cold.
//   • Gold accents ONE action per screen; if everything glows, nothing does.
//   • Text over a landscape painting always gets `Theme.paintingScrim` first.
//
// Every text pairing below is contrast-checked (WCAG AA at body size or better).

import SwiftUI

enum Theme {

    // MARK: - Night (dark surfaces)

    static let night     = Color(hex: 0x0E1210)   // base background
    static let hollow    = Color(hex: 0x141813)   // recessed
    static let bark      = Color(hex: 0x1B211A)   // panel / card
    static let barkRaised = Color(hex: 0x242B21)  // raised card / field
    static let line      = Color(hex: 0x2E3729)   // divider
    static let lineStrong = Color(hex: 0x3E4936)  // emphasized border

    /// Text on night surfaces.
    static let linen  = Color(hex: 0xEFE9D8)      // primary   (15.6:1)
    static let sage   = Color(hex: 0xBCC3AC)      // secondary (10.4:1)
    static let lichen = Color(hex: 0x8A9280)      // tertiary  (5.9:1)

    // MARK: - Parchment (paper surfaces)

    static let parchment     = Color(hex: 0xF2E8D0)
    static let parchmentWarm = Color(hex: 0xE8DBBC)
    static let parchmentEdge = Color(hex: 0xCBB88F)

    /// Text on parchment. Ink is a very dark warm brown, never black — that is
    /// the difference between handwriting and a print-out.
    static let ink      = Color(hex: 0x2E2718)    // primary   (12.1:1)
    static let inkSoft  = Color(hex: 0x574C36)    // secondary (6.9:1)
    static let inkFaint = Color(hex: 0x8A7C60)    // page numbers & flourishes only

    // MARK: - Leaf (green — the world)

    static let leaf900 = Color(hex: 0x1F2818)
    static let leaf700 = Color(hex: 0x37452A)
    static let leaf600 = Color(hex: 0x4A5C36)     // primary button ON parchment
    static let leaf500 = Color(hex: 0x5E7442)     // primary fill on dark
    static let leaf400 = Color(hex: 0x7B9455)     // the living green
    static let leaf300 = Color(hex: 0x9DB477)     // green text/icons on dark
    static let leaf200 = Color(hex: 0xC2D3A3)

    // MARK: - Sun (gold — the light)

    static let sun700 = Color(hex: 0x7E5A14)      // the only gold dark enough for paper
    static let sun600 = Color(hex: 0xA87C22)
    static let sun500 = Color(hex: 0xC9982F)
    static let sun400 = Color(hex: 0xE3B75A)      // THE accent
    static let sun300 = Color(hex: 0xF2D188)      // glow / highlight
    static let sun100 = Color(hex: 0xFBEDC8)

    // MARK: - Semantic

    static let clay     = Color(hex: 0xD2735A)    // destructive on night
    static let clayDark = Color(hex: 0xA4402A)    // destructive on parchment

    /// Label color for a filled sun-gold button (9.3:1).
    static let onSun = Color(hex: 0x161B14)

    // MARK: - Painting scrim
    //
    // Never put text straight onto a landscape painting. Lay this over the
    // bottom of the image, then use `linen` / `sage` on top: the painting keeps
    // its light, the words stay readable.

    static let paintingScrim = LinearGradient(
        stops: [
            .init(color: Color(hex: 0x0A0E0A, alpha: 0.82), location: 0.00),
            .init(color: Color(hex: 0x0A0E0A, alpha: 0.34), location: 0.42),
            .init(color: Color(hex: 0x0A0E0A, alpha: 0.00), location: 0.72),
        ],
        startPoint: .bottom,
        endPoint: .top
    )
}

extension Color {
    /// `Color(hex: 0x7B9455)` — kept private to the theme so hex codes live in
    /// exactly one file.
    fileprivate init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red:   Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue:  Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}

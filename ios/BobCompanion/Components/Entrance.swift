// How every screen arrives.
//
// Nothing in this app appears all at once. A screen assembles the way you notice
// a place you've walked into: the world resolves first — soft, then sharp — and
// only once you're standing in it do the words come, one thought at a time. The
// thing you came for is always last.
//
// This is the difference between an app that opens and an app that arrives.
//
// The order is fixed and shared by every screen, so the rhythm is the same
// wherever you are:
//
//     the world   →   first words   →   next words   →   the object
//
// Timings are slow on purpose. Anything quicker reads as a loading state; this
// has to read as light coming up.

import SwiftUI

/// Where a view sits in its screen's arrival.
enum Beat {
    /// The photograph, resolving out of soft focus.
    case world
    /// The first thing said.
    case first
    /// The thought after it.
    case second
    /// A third, where a screen has one.
    case third
    /// The scroll, the orb, the way in — whatever the screen is actually for.
    case object
    /// The quiet things that live at the very bottom: fine print, terms.
    case footnote

    var delay: Double {
        switch self {
        case .world:    return 0.00
        case .first:    return 0.75
        case .second:   return 1.45
        case .third:    return 2.00
        case .object:   return 2.35
        case .footnote: return 2.85
        }
    }
}

/// One piece of a screen, arriving on its beat: fading up, rising a little, and
/// coming out of soft focus at the same time. The blur is what stops it reading
/// as a plain fade — it's the same gesture as the eye settling on something.
private struct Arrive: ViewModifier {
    let beat: Beat
    var rise: CGFloat
    var enabled: Bool

    @State private var shown = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .opacity(shown ? 1 : 0)
            .offset(y: shown ? 0 : rise)
            .blur(radius: shown ? 0 : 5)
            .onAppear {
                guard enabled else { shown = true; return }
                // Reduce Motion still gets the screen in the same order and over
                // the same span — it simply doesn't travel.
                let duration = reduceMotion ? 0.5 : 1.1
                withAnimation(.easeOut(duration: duration).delay(beat.delay)) {
                    shown = true
                }
            }
    }
}

extension View {
    /// Arrive on this beat of the screen's entrance.
    ///
    /// - Parameters:
    ///   - beat: where this sits in the order.
    ///   - rise: how far it travels up as it lands. Small for text, larger for
    ///     an object that should feel like it was set down.
    ///   - enabled: pass `false` where a screen is continuing rather than
    ///     arriving — screen 4 keeps screen 3's clearing, so its world must not
    ///     fade in again.
    func arrive(_ beat: Beat, rise: CGFloat = 12, enabled: Bool = true) -> some View {
        modifier(Arrive(beat: beat, rise: rise, enabled: enabled))
    }
}

// MARK: - Text laid on a photograph

extension View {
    /// Text sitting directly on a landscape needs its own shadow to hold an
    /// edge, or it dissolves into whatever happens to be behind it. Two shadows:
    /// a tight one for the letterforms, a wide soft one that darkens the
    /// photograph itself just enough to seat them.
    func legible(_ strength: Double = 1) -> some View {
        self
            .shadow(color: Color(hex: 0x0A0D08, alpha: 0.55 * strength), radius: 2, x: 0, y: 1)
            .shadow(color: Color(hex: 0x0A0D08, alpha: 0.40 * strength), radius: 14, x: 0, y: 4)
    }
}

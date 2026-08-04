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
        case .first:    return 0.45
        case .second:   return 1.00
        case .third:    return 1.40
        case .object:   return 1.65
        case .footnote: return 2.00
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

// MARK: - Leaving
//
// There is deliberately no screen-removal transition here any more.
//
// Four attempts at one produced nothing visible, and the cause turned out to be
// z-order rather than animation: inside a ZStack, the incoming full-bleed
// photograph takes the departing screen's implicit z position and covers it, so
// the removal plays perfectly and is never seen. AppFlow crosses between places
// with a veil instead — see the note there — which has no identity, no
// insertion, no removal and no z-order to get wrong.
//
// `arrive` below is still the whole entrance system, and is unaffected: it
// animates properties of views that are already on screen, which is exactly the
// kind of animation SwiftUI is reliable about.

// MARK: - Text laid on a photograph

extension View {
    /// Text sitting directly on a landscape needs help holding its edge, or it
    /// dissolves into whatever happens to be behind it.
    ///
    /// The trick is WHERE the darkness goes. A tight offset shadow traces every
    /// letterform and stamps the words onto the photograph — hard, crisp, cheap.
    /// So there isn't one. Both of these are wide and centred, with no offset at
    /// all: they darken the PHOTOGRAPH behind the words rather than outlining
    /// the words themselves. The text keeps its own softness and simply has
    /// somewhere quieter to sit.
    func legible(_ strength: Double = 1) -> some View {
        self
            .shadow(color: Color(hex: 0x0A0D08, alpha: 0.42 * strength), radius: 12)
            .shadow(color: Color(hex: 0x0A0D08, alpha: 0.30 * strength), radius: 30)
    }
}

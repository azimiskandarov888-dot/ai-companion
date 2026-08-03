// The one rule, made into a component: every screen is a full-screen photograph.
//
// The photo fills the entire display — edge to edge, behind the status bar and
// under the home indicator — and all text, buttons and panels sit ON it.
// There is no screen in this app with a flat background.
//
// Legibility comes from a scrim or a blurred pass, NEVER from cropping the photo
// off and starting a panel.

import SwiftUI

/// Which photograph a screen stands in. The files are the graded exports from
/// `ios/design/grade/out/` — drop them into Assets.xcassets under these names.
enum Place: String {
    case signIn    = "1-signin"
    case takeCare  = "2-payment"
    case story     = "3-story"
    case meet      = "4-meet"
    case companion = "5-companion"
    case diary     = "6-diary"
    case account   = "7-account"
    case settings  = "8-settings"
}

/// How the photograph is treated on this screen.
enum PlaceTreatment {
    /// Full brightness, with a bottom-up scrim under the content. Sign-in,
    /// payment, the scroll scenes.
    case scrim
    /// Blurred and darkened so a long list reads cleanly — you can still tell
    /// you're outdoors. Account, Settings, the Diary.
    case blurred(radius: CGFloat = Metrics.panelBlur, dim: Double = 0.42)
    /// Nothing over it. The companion screen — its photo is already graded to
    /// night, and anything more would flatten it.
    case bare
}

struct PhotoBackground: View {
    let place: Place
    var treatment: PlaceTreatment = .scrim

    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    var body: some View {
        GeometryReader { geo in
            ZStack {
                // A deep base so the frame is never white for even one frame
                // while the image decodes.
                Theme.night

                Image(place.rawValue)
                    .resizable()
                    .scaledToFill()
                    .frame(width: geo.size.width, height: geo.size.height)
                    .clipped()
                    .modifier(TreatmentModifier(treatment: treatment,
                                                reduceTransparency: reduceTransparency))

                if case .scrim = treatment {
                    Theme.bottomScrim
                }
            }
            .ignoresSafeArea()
            .accessibilityHidden(true)   // decorative — VoiceOver skips the place
        }
        .ignoresSafeArea()
    }
}

private struct TreatmentModifier: ViewModifier {
    let treatment: PlaceTreatment
    let reduceTransparency: Bool

    func body(content: Content) -> some View {
        switch treatment {
        case .scrim, .bare:
            content
        case .blurred(let radius, let dim):
            // Reduce Transparency doesn't remove the place — it dims it further,
            // so the app still stands somewhere.
            content
                .blur(radius: reduceTransparency ? radius * 0.5 : radius, opaque: true)
                .overlay(Color(hex: 0x0E1210, alpha: reduceTransparency ? dim + 0.35 : dim))
        }
    }
}

// MARK: - The translucent panel every card, group and quiet button sits on

struct PanelBackground: View {
    var radius: CGFloat = Metrics.cardRadius
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    var body: some View {
        RoundedRectangle(cornerRadius: radius, style: .continuous)
            .fill(reduceTransparency ? Theme.panelFillSolid : Theme.panelFill)
            .background(
                reduceTransparency
                    ? nil
                    : RoundedRectangle(cornerRadius: radius, style: .continuous)
                        .fill(.ultraThinMaterial)
                        .environment(\.colorScheme, .dark)
            )
    }
}

extension View {
    /// Lay this content on the app's standard translucent panel.
    func panel(radius: CGFloat = Metrics.cardRadius) -> some View {
        self.background(PanelBackground(radius: radius))
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
}

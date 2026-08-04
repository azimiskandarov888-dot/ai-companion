// The only chrome on the companion screen.
//
// Three quiet words at the bottom edge — Diary · You · Settings — with a small
// brass rule above them. That's it.
//
// This started as a hidden pull-handle that showed the words only when tugged.
// It was beautiful and it did not work: the handle could not be found, twice,
// by the person who knew it was there. A control nobody can find is not
// minimalism — it's a missing feature, and the app has no other way to reach
// three of its screens.
//
// So the words are simply always there. It stays minimal by being SMALL and
// QUIET — three words in caption type at 78 % — rather than by being hidden.
// There is still no tab bar, no icons, nothing across the top; a tab bar would
// turn a friend into an app.

import SwiftUI

struct BrassRing: View {
    /// Kept so the companion screen's existing state and its swipe-to-dismiss
    /// still line up, though the words no longer need opening.
    @Binding var isOpen: Bool
    var onDiary: () -> Void
    var onAccount: () -> Void
    var onSettings: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            // The brass rule. Decoration now rather than a control — it marks
            // the bottom of his world the way the rollers mark the scroll, and
            // fades out at both ends so it never becomes a bar.
            Capsule()
                .fill(
                    LinearGradient(colors: [Theme.brassLight.opacity(0.0),
                                            Theme.brassLight.opacity(0.55),
                                            Theme.brass.opacity(0.45),
                                            Theme.brassLight.opacity(0.0)],
                                   startPoint: .leading, endPoint: .trailing)
                )
                .frame(width: 132, height: 1)

            HStack(spacing: 26) {
                word(Strings.navDiary(),    action: onDiary)
                word(Strings.navAccount(),  action: onAccount)
                word(Strings.navSettings(), action: onSettings)
            }
        }
        .padding(.bottom, 4)
    }

    private func word(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .appFont(AppType.caption)
                .tracking(AppType.statusTracking)
                .foregroundStyle(Theme.onLand.opacity(0.78))
                .legible(0.8)
                .padding(.horizontal, 8)
                .frame(minHeight: Metrics.minTouch)
        }
        .buttonStyle(SoftPress())
        .accessibilityAddTraits(.isButton)
    }
}

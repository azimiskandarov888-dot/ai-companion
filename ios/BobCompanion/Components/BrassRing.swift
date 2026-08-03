// The only chrome on the companion screen.
//
// A small brass ring at the bottom edge. Press or pull it and three quiet words
// rise — Diary · You · Settings. Let go and they sink again.
//
// Resting shows no words at all, which is the point: the screen has to stay
// empty enough to live with all day. There is no tab bar, because a tab bar
// would turn a friend into an app.

import SwiftUI

struct BrassRing: View {
    @Binding var isOpen: Bool
    var onDiary: () -> Void
    var onAccount: () -> Void
    var onSettings: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pull: CGFloat = 0

    private var springy: Animation {
        reduceMotion ? .easeInOut(duration: 0.35)
                     : .spring(response: 0.42, dampingFraction: 0.86)
    }

    var body: some View {
        VStack(spacing: 18) {
            if isOpen {
                HStack(spacing: 28) {
                    word(Strings.navDiary(),    action: onDiary)
                    word(Strings.navAccount(),  action: onAccount)
                    word(Strings.navSettings(), action: onSettings)
                }
                .transition(
                    reduceMotion
                        ? .opacity
                        : .asymmetric(
                            insertion: .move(edge: .bottom).combined(with: .opacity),
                            removal: .opacity)
                )
            }

            ring
        }
        .padding(.bottom, 6)
        .animation(springy, value: isOpen)
    }

    private func word(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: {
            withAnimation(springy) { isOpen = false }
            action()
        }) {
            Text(title)
                .appFont(AppType.caption)
                .tracking(AppType.statusTracking)
                .foregroundStyle(Theme.sage)
                .padding(.horizontal, 10)
                .frame(minHeight: Metrics.minTouch)
        }
        .buttonStyle(SoftPress())
    }

    private var ring: some View {
        Capsule()
            .strokeBorder(
                LinearGradient(colors: [Theme.brassLight.opacity(0.75),
                                        Theme.brass.opacity(0.55),
                                        Theme.brassDark.opacity(0.7)],
                               startPoint: .leading, endPoint: .trailing),
                lineWidth: 1.5
            )
            .frame(width: 46, height: 5)
            .offset(y: -pull * 0.35)
            .frame(minWidth: Metrics.minTouch * 2, minHeight: Metrics.minTouch)
            .contentShape(Rectangle())
            .onTapGesture { withAnimation(springy) { isOpen.toggle() } }
            .gesture(
                DragGesture(minimumDistance: 4)
                    .onChanged { value in
                        pull = max(-40, min(0, value.translation.height))
                        if pull < -18, !isOpen { withAnimation(springy) { isOpen = true } }
                    }
                    .onEnded { _ in withAnimation(springy) { pull = 0 } }
            )
            .accessibilityElement()
            .accessibilityLabel(Strings.language == .russian ? "Меню" : "Menu")
            .accessibilityHint(Strings.language == .russian
                               ? "Дневник, Ты, Настройки"
                               : "Diary, You, Settings")
            .accessibilityAddTraits(.isButton)
    }
}

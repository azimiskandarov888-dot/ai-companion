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
    /// The three words show themselves ONCE, the first time he is ever on
    /// screen, and then never again unasked. A handle nobody can find is not
    /// minimalism, it's a missing feature — but it only has to be taught once.
    @AppStorage("hasSeenNavHint") private var hasSeenHint = false
    @State private var hinting = false

    private var springy: Animation {
        reduceMotion ? .easeInOut(duration: 0.35)
                     : .spring(response: 0.42, dampingFraction: 0.86)
    }

    private var showingWords: Bool { isOpen || hinting }

    var body: some View {
        VStack(spacing: 18) {
            if showingWords {
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
        .animation(.easeInOut(duration: 0.9), value: hinting)
        .onAppear(perform: hintOnce)
    }

    /// Shown once, well after the screen has settled, and gone again on its own.
    private func hintOnce() {
        guard !hasSeenHint else { return }
        hasSeenHint = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.4) {
            hinting = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 4.2) { hinting = false }
        }
    }

    private func word(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: {
            withAnimation(springy) { isOpen = false }
            hinting = false
            action()
        }) {
            Text(title)
                .appFont(AppType.secondary)
                .tracking(AppType.statusTracking)
                .foregroundStyle(Theme.linen)
                .legible()
                .padding(.horizontal, 10)
                .frame(minHeight: Metrics.minTouch)
        }
        .buttonStyle(SoftPress())
    }

    private var ring: some View {
        Capsule()
            .fill(
                LinearGradient(colors: [Theme.brassLight.opacity(0.95),
                                        Theme.brass.opacity(0.85),
                                        Theme.brassDark.opacity(0.9)],
                               startPoint: .leading, endPoint: .trailing)
            )
            .frame(width: 64, height: 5)
            // A little light pooling under it, so it is findable on a dark
            // photograph without becoming a piece of furniture.
            .shadow(color: Theme.brassLight.opacity(0.35), radius: 8)
            .shadow(color: Color(hex: 0x0A0D08, alpha: 0.6), radius: 6, y: 2)
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

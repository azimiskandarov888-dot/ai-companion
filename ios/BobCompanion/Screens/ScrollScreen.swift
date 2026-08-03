// 3 · Tell your story   and   4 · Who you'd like to meet
//
// The same object, in the same clearing, an hour apart. One screen type serves
// both, because that is exactly what they are: you didn't get up, you turned to
// a second page.
//
// The two things that must not go wrong:
//
//   1. THE KEYBOARD MUST NEVER COVER THE SCROLL. At rest the paper's centre sits
//      on the optical centre (45.5 %). When the keyboard rises the whole object
//      rises with it, to 12 %–50 % of the screen, and the writing scrolls INSIDE
//      the parchment — the paper never grows and never slides under the keys.
//      If the scroll can't be seen, the screen has failed.
//
//   2. THE ROLL-AWAY IS THE SIGNATURE MOMENT. The sheet winds onto the far
//      roller, lifts, tilts, and drifts out past the right edge — and the
//      landscape behind it never moves.

import SwiftUI

struct ScrollScreen: View {

    enum Kind {
        case story      // 3
        case meet       // 4

        var place: Place { self == .story ? .story : .meet }
        var heading: String { self == .story ? Strings.storyHeading() : Strings.meetHeading() }
        var placeholder: String {
            self == .story ? Strings.storyPlaceholder() : Strings.meetPlaceholder()
        }
        var confirm: String { self == .story ? Strings.done() : Strings.meetHim() }
        /// Gold is spent on «Meet him» — the last step of onboarding. «Done» is
        /// the calm leaf green, so the two screens don't compete.
        var tone: ButtonTone { self == .story ? .leaf : .sun }
    }

    let kind: Kind
    @Binding var text: String
    var onConfirm: () -> Void

    @StateObject private var keyboard = KeyboardObserver()
    @FocusState private var writing: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// 0 at rest → 1 when the sheet has wound onto the far roller and gone.
    @State private var winding: CGFloat = 0
    @State private var showNudge = false

    var body: some View {
        GeometryReader { geo in
            let h = geo.size.height
            let isWriting = keyboard.isShowing

            ZStack(alignment: .top) {
                PhotoBackground(place: kind.place, treatment: .scrim)

                // ── screen 4's caution: the one thing that survives the keyboard
                if kind == .meet {
                    caution(isWriting: isWriting)
                        .padding(.horizontal, Metrics.sideMargin)
                        .padding(.top, isWriting ? h * 0.075 : h * 0.20)
                        .opacity(winding > 0.1 ? 0 : 1)
                }

                // ── the scroll itself
                scroll(width: geo.size.width, height: h, isWriting: isWriting)
                    .position(x: geo.size.width / 2 + winding * geo.size.width * 1.15,
                              y: centreY(in: h, isWriting: isWriting))
                    .rotationEffect(.degrees(-winding * 7), anchor: .center)
                    .offset(y: -winding * 10)

                // ── screen 4's quote: read before writing, steps back after
                if kind == .meet {
                    VStack {
                        Spacer()
                        Text(Strings.friendshipQuote())
                            .font(AppType.quote)
                            .lineSpacing(AppType.quoteLeading)
                            .foregroundStyle(Theme.sage)
                            .multilineTextAlignment(.leading)
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(.horizontal, Metrics.sideMargin)
                            .padding(.bottom, 18)
                            .opacity(isWriting || winding > 0.1 ? 0 : 1)
                        confirmButton
                            .padding(.horizontal, Metrics.sideMargin)
                            .padding(.bottom, geo.safeAreaInsets.bottom > 0 ? 8 : 24)
                            .opacity(isWriting ? 0 : 1)
                    }
                } else {
                    VStack {
                        Spacer()
                        confirmButton
                            .padding(.horizontal, Metrics.sideMargin)
                            .padding(.bottom, geo.safeAreaInsets.bottom > 0 ? 8 : 24)
                            .opacity(isWriting ? 0 : 1)
                    }
                }

                // ── while writing, the confirm moves to a blurred bar just
                //    above the keys, so it is never buried
                if isWriting {
                    VStack {
                        Spacer()
                        confirmButton
                            .padding(.horizontal, Metrics.sideMargin)
                            .padding(.vertical, 10)
                            .background(.ultraThinMaterial.opacity(0.9))
                            .environment(\.colorScheme, .dark)
                            .padding(.bottom, keyboard.height)
                    }
                    .transition(.opacity)
                    .ignoresSafeArea(.keyboard)
                }
            }
            .animation(.easeOut(duration: keyboard.duration), value: keyboard.height)
        }
        .ignoresSafeArea(.keyboard)      // we position against the keyboard ourselves
        .onTapGesture { writing = false }
    }

    // MARK: - where the paper sits

    /// Rest: the paper's centre on the optical centre, 45.5 %.
    /// Writing: optically centred in what's left above the keyboard — the
    /// midpoint of 12 % and 50 %.
    private func centreY(in height: CGFloat, isWriting: Bool) -> CGFloat {
        isWriting
            ? height * (Metrics.scrollWritingTop + Metrics.scrollWritingBottom) / 2
            : height * Metrics.opticalCentre
    }

    /// The paper never grows past the room it has — long writing scrolls inside
    /// it instead.
    private func maxPaperHeight(in height: CGFloat, isWriting: Bool) -> CGFloat {
        isWriting
            ? height * (Metrics.scrollWritingBottom - Metrics.scrollWritingTop)
            : height * 0.44
    }

    // MARK: - the scroll

    private func scroll(width: CGFloat, height: CGFloat, isWriting: Bool) -> some View {
        ParchmentScroll(winding: winding) {
            VStack(alignment: .leading, spacing: 12) {
                Text(kind.heading)
                    .font(AppType.writtenHeading)
                    .foregroundStyle(Theme.ink)

                if !isWriting, text.isEmpty, kind == .story {
                    Text(Strings.storyLine())
                        .appFont(AppType.caption)
                        .foregroundStyle(Theme.inkSoft.opacity(0.88))
                        .fixedSize(horizontal: false, vertical: true)
                }

                writingSurface

                if kind == .meet {
                    // The chips live ON the paper — drawn in ink, not linen.
                    // They insert a phrase into their own writing; they are
                    // never a field, and never required.
                    HStack(spacing: 8) {
                        SoftChip(title: Strings.chipAge())    { insert(Strings.chipAgeText()) }
                        SoftChip(title: Strings.chipGender()) { insert(Strings.chipGenderText()) }
                        SoftChip(title: Strings.chipOrigin()) { insert(Strings.chipOriginText()) }
                    }
                    .padding(.top, 2)
                }
            }
        }
        .frame(width: min(Metrics.scrollWidth, width - Metrics.sideMargin * 2))
        .frame(maxHeight: maxPaperHeight(in: height, isWriting: isWriting))
    }

    private var writingSurface: some View {
        ScrollView {
            ZStack(alignment: .topLeading) {
                if text.isEmpty {
                    Text(kind.placeholder)
                        .font(AppType.writtenBody)
                        .italic()
                        .foregroundStyle(Theme.inkSoft.opacity(0.88))
                        .allowsHitTesting(false)
                        .padding(.top, 8)
                }
                TextEditor(text: $text)
                    .font(AppType.writtenBody)
                    .lineSpacing(AppType.writtenLeading)
                    .foregroundStyle(Theme.ink)
                    .scrollContentBackground(.hidden)
                    .background(.clear)
                    .frame(minHeight: 120)
                    .focused($writing)
            }
        }
        .scrollBounceBehavior(.basedOnSize)
    }

    private func insert(_ phrase: String) {
        if !text.isEmpty, !text.hasSuffix(" "), !text.hasSuffix("\n") { text += " " }
        text += phrase
        writing = true
    }

    // MARK: - the caution (screen 4 only)

    private func caution(isWriting: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Rectangle()
                .fill(Theme.sun400)
                .frame(width: 2)
            VStack(alignment: .leading, spacing: 8) {
                Text(Strings.caution())
                    .font(.system(size: isWriting ? 14.5 : 19, weight: .regular))
                    .lineSpacing(isWriting ? 4 : 6)
                    .foregroundStyle(Theme.sun300)
                    .fixedSize(horizontal: false, vertical: true)
                if !isWriting {
                    Text(Strings.cautionSofter())
                        .appFont(AppType.caption)
                        .foregroundStyle(Theme.sage)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .fixedSize(horizontal: false, vertical: true)
    }

    // MARK: - confirm

    private var confirmButton: some View {
        VStack(spacing: 8) {
            if showNudge {
                Text(Strings.storyNudge())
                    .appFont(AppType.caption)
                    .foregroundStyle(Theme.sage)
                    .multilineTextAlignment(.center)
                    .transition(.opacity)
            }
            AppButton(title: kind.confirm, tone: kind.tone) { confirm() }
        }
    }

    private func confirm() {
        // Screen 3 genuinely needs something to build him from — so «Done» looks
        // quiet rather than disabled, and tapping it gives one gentle nudge.
        // Screen 4 may be left blank: that's a fine answer, arguably the best.
        if kind == .story, text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            withAnimation { showNudge = true }
            writing = true
            return
        }

        writing = false

        guard !reduceMotion else {          // Reduce Motion: a cross-fade, same duration
            withAnimation(.easeInOut(duration: 0.8)) { winding = 1 }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { onConfirm() }
            return
        }

        // The signature moment, ~0.8 s: winds onto the far roller, lifts, tilts,
        // and drifts out right. The landscape never moves.
        withAnimation(.timingCurve(0.32, 0, 0.2, 1, duration: 0.8)) { winding = 1 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.78) { onConfirm() }
    }
}

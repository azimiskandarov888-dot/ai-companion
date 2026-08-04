// 3 · Tell your story   and   4 · Who you'd like to meet
//
// The same object, in the same clearing, an hour apart. One screen type serves
// both, because that is exactly what they are: you didn't get up, you turned to
// a second page.
//
// The scroll hangs VERTICALLY — a roller above, a roller below, paper between —
// and writing behaves the way writing behaves everywhere else on a phone: type
// past the bottom line and the text slides up inside the paper. The paper never
// grows, never overruns its rollers, and never has to be fought with.
//
// The two things that must not go wrong:
//
//   1. THE KEYBOARD MUST NEVER COVER THE SCROLL. At rest the paper sits on the
//      optical centre (45.5 %). When the keyboard rises the whole object rises
//      with it and the paper shortens — the writing scrolls INSIDE the parchment
//      rather than sliding under the keys. If the scroll can't be seen, the
//      screen has failed.
//
//   2. THE ROLL-AWAY IS THE SIGNATURE MOMENT. The sheet winds up onto the top
//      roller, and the whole object lifts and drifts away — and the landscape
//      behind it never moves.
//
// Everything here is laid out in ONE vertical stack with definite heights.
// Nothing is placed by absolute coordinates, because that is how the caution on
// screen 4 ended up sitting on top of the paper.

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

    /// 0 at rest → 1 when the sheet has wound onto the top roller and gone.
    @State private var winding: CGFloat = 0
    @State private var showNudge = false

    var body: some View {
        GeometryReader { geo in
            let h = geo.size.height
            let isWriting = keyboard.isShowing
            let paper = paperHeight(in: h, isWriting: isWriting)

            ZStack {
                PhotoBackground(place: kind.place, treatment: .scrim)

                // Tapping the world outside the paper puts the pen down. This
                // has to sit BEHIND the scroll — as a modifier on the whole
                // screen it swallowed the taps meant for the writing surface,
                // and nothing could be typed at all.
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture { writing = false }

                VStack(spacing: 0) {
                    // ── screen 4's caution, above the paper and never on it
                    if kind == .meet {
                        caution(isWriting: isWriting)
                            .opacity(winding > 0.1 ? 0 : 1)
                        Spacer(minLength: 14)
                    }

                    // ── the scroll itself
                    scroll(isWriting: isWriting)
                        .frame(height: paper)
                        .offset(y: -winding * h * 0.28)
                        .opacity(1 - winding * 0.55)

                    Spacer(minLength: 12)

                    // ── screen 4's quote: read before writing, steps back after
                    if kind == .meet, !isWriting, winding < 0.1 {
                        Text(Strings.friendshipQuote())
                            .font(AppType.quote)
                            .lineSpacing(AppType.quoteLeading)
                            .foregroundStyle(Theme.sage)
                            .multilineTextAlignment(.leading)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.bottom, 18)
                    }

                    confirmButton
                }
                .padding(.horizontal, Metrics.sideMargin)
                .padding(.top, topInset(in: h, paper: paper, isWriting: isWriting))
                .padding(.bottom, isWriting
                         ? keyboard.height + 12
                         : (geo.safeAreaInsets.bottom > 0 ? 8 : 24))
            }
            .animation(.easeOut(duration: keyboard.duration), value: keyboard.height)
        }
        .ignoresSafeArea(.keyboard)      // we position against the keyboard ourselves
    }

    // MARK: - where the paper sits, and how tall it is
    //
    // Both are definite. The paper is exactly as tall as it is told to be, so it
    // can never overrun its rollers or collide with the words above it.

    private func paperHeight(in height: CGFloat, isWriting: Bool) -> CGFloat {
        let fraction: CGFloat
        switch (kind, isWriting) {
        case (.story, false): fraction = 0.42
        case (.story, true):  fraction = 0.34
        case (.meet,  false): fraction = 0.33
        case (.meet,  true):  fraction = 0.30
        }
        return height * fraction
    }

    /// Rest: the paper's centre lands on the optical centre, 45.5 %.
    /// Writing: it rises to just under the top of the screen.
    private func topInset(in height: CGFloat, paper: CGFloat, isWriting: Bool) -> CGFloat {
        if isWriting { return height * Metrics.scrollWritingTop }
        switch kind {
        case .story:
            return max(16, height * Metrics.opticalCentre - paper / 2)
        case .meet:
            // The caution sits above the paper, so the stack starts higher.
            return max(16, height * 0.11)
        }
    }

    // MARK: - the scroll

    private func scroll(isWriting: Bool) -> some View {
        ParchmentScroll(winding: winding) {
            VStack(alignment: .leading, spacing: 10) {
                Text(kind.heading)
                    .font(AppType.writtenHeading)
                    .foregroundStyle(Theme.ink)
                    .fixedSize(horizontal: false, vertical: true)

                if !isWriting, text.isEmpty, kind == .story {
                    Text(Strings.storyLine())
                        .appFont(AppType.caption)
                        .foregroundStyle(Theme.inkSoft.opacity(0.88))
                        .fixedSize(horizontal: false, vertical: true)
                }

                // The writing surface takes everything left over, and scrolls
                // its own contents. It is NOT inside a ScrollView — two nested
                // scrollers is what made the text vanish and stop accepting
                // more once it passed the bottom.
                writingSurface
                    .frame(maxHeight: .infinity)

                if kind == .meet, !isWriting {
                    // The chips live ON the paper — drawn in ink, not linen.
                    // They insert a phrase into their own writing; they are
                    // never a field, and never required.
                    HStack(spacing: 8) {
                        SoftChip(title: Strings.chipAge())    { insert(Strings.chipAgeText()) }
                        SoftChip(title: Strings.chipGender()) { insert(Strings.chipGenderText()) }
                        SoftChip(title: Strings.chipOrigin()) { insert(Strings.chipOriginText()) }
                    }
                }
            }
        }
        // Touching the paper anywhere picks the pen up — the margins count too,
        // not only the exact line you're writing on. Simultaneous, so the text
        // view still places its own cursor where you tapped.
        .contentShape(Rectangle())
        .simultaneousGesture(TapGesture().onEnded { writing = true })
    }

    private var writingSurface: some View {
        ZStack(alignment: .topLeading) {
            if text.isEmpty {
                Text(kind.placeholder)
                    .font(AppType.writtenBody)
                    .italic()
                    .foregroundStyle(Theme.inkSoft.opacity(0.88))
                    .allowsHitTesting(false)
                    .padding(.top, 8)
                    .padding(.leading, 5)    // sits on the text view's own inset
            }
            TextEditor(text: $text)
                .font(AppType.writtenBody)
                .lineSpacing(AppType.writtenLeading)
                .foregroundStyle(Theme.ink)
                .tint(Theme.leaf500)                 // the caret, in ink's world
                .scrollContentBackground(.hidden)
                .background(.clear)
                .focused($writing)
        }
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
                    .font(.system(size: isWriting ? 14.5 : 18, weight: .regular))
                    .lineSpacing(isWriting ? 4 : 5)
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

        // The signature moment, ~0.8 s: the sheet winds up onto the top roller
        // and the whole object lifts away. The landscape never moves.
        withAnimation(.timingCurve(0.32, 0, 0.2, 1, duration: 0.8)) { winding = 1 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.78) { onConfirm() }
    }
}

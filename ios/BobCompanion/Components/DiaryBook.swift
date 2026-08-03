// His diary — an old hand-bound book, drawn so its pages can hold real text and
// turn.
//
// Worn boards, thread showing in the gutter, rough parchment leaves. He writes;
// the user only reads. Nothing modern, and no skeuomorphic gloss — the point is
// that it looks made by hand, not rendered.
//
// The empty state is a single short page in his own voice with the right leaf
// blank: a book that has just been opened. Never "No entries yet."

import SwiftUI

struct DiaryBook: View {
    /// One string per leaf. The book lays them out two at a time.
    let leaves: [String]
    @Binding var spread: Int          // which pair of leaves is open
    /// Page numbers start here. The empty first page is page 1.
    var firstPageNumber: Int = 1

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var leftIndex: Int  { spread * 2 }
    private var rightIndex: Int { spread * 2 + 1 }

    var body: some View {
        HStack(spacing: 0) {
            Leaf(text: leaves[safe: leftIndex],
                 pageNumber: firstPageNumber + leftIndex,
                 side: .left)
            Gutter()
            Leaf(text: leaves[safe: rightIndex],
                 pageNumber: leaves[safe: rightIndex] == nil ? nil : firstPageNumber + rightIndex,
                 side: .right)
        }
        .padding(10)                         // the boards' reveal around the leaves
        .background(Boards())
        .shadow(color: Color(hex: 0x0A0704, alpha: 0.55), radius: 30, y: 14)
        .contentShape(Rectangle())
        .gesture(
            DragGesture(minimumDistance: 24)
                .onEnded { value in
                    guard abs(value.translation.width) > abs(value.translation.height) else { return }
                    turn(forward: value.translation.width < 0)
                }
        )
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isStaticText)
    }

    private func turn(forward: Bool) {
        let lastSpread = max(0, (leaves.count - 1) / 2)
        let target = forward ? min(spread + 1, lastSpread) : max(spread - 1, 0)
        guard target != spread else { return }
        withAnimation(reduceMotion
                      ? .easeInOut(duration: 0.5)
                      : .spring(response: 0.5, dampingFraction: 0.86)) {
            spread = target
        }
    }
}

// MARK: - The boards

private struct Boards: View {
    var body: some View {
        RoundedRectangle(cornerRadius: Metrics.boardRadius, style: .continuous)
            .fill(
                LinearGradient(colors: [Theme.boardOuter, Theme.boardInner],
                               startPoint: .topLeading, endPoint: .bottomTrailing)
            )
            .overlay(
                RoundedRectangle(cornerRadius: Metrics.boardRadius, style: .continuous)
                    .strokeBorder(Color(hex: 0x1A1209, alpha: 0.8), lineWidth: 1)
            )
    }
}

// MARK: - The gutter, with its thread

private struct Gutter: View {
    var body: some View {
        ZStack {
            // The shadow where the two leaves fall into the spine.
            LinearGradient(
                colors: [Color(hex: 0x8A7A5C, alpha: 0.45),
                         Color(hex: 0x4A3D28, alpha: 0.55),
                         Color(hex: 0x8A7A5C, alpha: 0.45)],
                startPoint: .leading, endPoint: .trailing)

            // Seven thread marks — hand-sewn, so they're not perfectly even.
            GeometryReader { geo in
                let count = 7
                ForEach(0..<count, id: \.self) { i in
                    let t = (CGFloat(i) + 0.5) / CGFloat(count)
                    let jitter: CGFloat = (i % 2 == 0) ? -0.6 : 0.6
                    Capsule()
                        .fill(Color(hex: 0x2A2015, alpha: 0.75))
                        .frame(width: 7, height: 2)
                        .position(x: geo.size.width / 2 + jitter, y: geo.size.height * t)
                }
            }
        }
        .frame(width: 16)
    }
}

// MARK: - A leaf

private struct Leaf: View {
    enum Side { case left, right }
    let text: String?
    let pageNumber: Int?
    let side: Side

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let text {
                Text(text)
                    .font(AppType.diaryBody)
                    .lineSpacing(AppType.diaryLeading)
                    .foregroundStyle(Theme.ink)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 12)
            if let pageNumber {
                Text("\(pageNumber)")
                    .font(AppType.pageNumber)
                    .foregroundStyle(Theme.inkFaint)
                    .frame(maxWidth: .infinity,
                           alignment: side == .left ? .leading : .trailing)
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 20)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(
            ZStack {
                Theme.parchmentLeaf
                // The page curves very slightly away toward the spine.
                LinearGradient(
                    colors: side == .left
                        ? [.clear, Color(hex: 0x8A7A5C, alpha: 0.16)]
                        : [Color(hex: 0x8A7A5C, alpha: 0.16), .clear],
                    startPoint: .leading, endPoint: .trailing)
            }
        )
        .clipShape(
            .rect(topLeadingRadius:     side == .left ? 5 : 2,
                  bottomLeadingRadius:  side == .left ? 5 : 2,
                  bottomTrailingRadius: side == .left ? 2 : 5,
                  topTrailingRadius:    side == .left ? 2 : 5)
        )
    }
}

extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}

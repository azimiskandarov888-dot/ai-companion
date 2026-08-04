// The scroll — the app's signature object, and its writing surface.
//
// A parchment sheet hanging between two turned wooden rollers, one above and one
// below, with aged brass end caps. VERTICAL, the way a scroll actually hangs:
// you read down it, and when you write past the bottom the writing slides up
// inside the paper exactly like any other text field. The paper never grows.
//
// Not photographed — drawn — because it has to hold live text, grow with Dynamic
// Type, scroll internally, and roll away when it's finished.
//
// It rests on the world rather than floating: a soft warm shadow beneath, and a
// faint highlight along its top edge where the light catches the paper.

import SwiftUI

struct ParchmentScroll<Content: View>: View {
    /// Winding progress for the roll-away, 0 (open) → 1 (wound onto the top
    /// roller and gone). Left at 0 for the ordinary resting and writing states.
    var winding: CGFloat = 0
    @ViewBuilder var content: Content

    var body: some View {
        VStack(spacing: 0) {
            Roller(thickness: 1 + winding * 0.57)     // the sheet winds up onto this one
            paper
            Roller(thickness: 1 - winding * 0.45)     // …and this one empties
        }
        .shadow(color: Color(hex: 0x120E06, alpha: 0.55),
                radius: 26 + winding * 10, x: 0, y: 12 + winding * 6)
    }

    private var paper: some View {
        content
            .padding(.horizontal, 22)
            .padding(.vertical, 18)
            // Fills whatever room the screen gave the scroll, and no more — so
            // the paper is always exactly as tall as the rollers are apart.
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .background(
                ZStack {
                    // The paper itself — soft cream, faintly warmer at the fold.
                    LinearGradient(
                        colors: [Color(hex: 0xF3E7CB), Theme.parchment, Color(hex: 0xE7D9B7)],
                        startPoint: .top, endPoint: .bottom)

                    LedgerRules()          // faint ruled lines, like real ledger paper
                    ParchmentGrain()       // fibres and age, very quiet
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: Metrics.parchmentRadius, style: .continuous))
            .overlay(alignment: .top) {
                // Light catching the top edge, so the sheet has thickness.
                Rectangle()
                    .fill(Color.white.opacity(0.35))
                    .frame(height: 1)
                    .blendMode(.softLight)
            }
            // The sheet is narrower than the rollers it hangs from, so the wood
            // and its brass caps stand proud at both ends — which is the whole
            // reason it reads as a scroll and not as a sheet of paper with two
            // stripes across it.
            .padding(.horizontal, Metrics.paperInset)
            // Rolls up into the top roller.
            .scaleEffect(y: max(0.02, 1 - winding), anchor: .top)
            .opacity(winding > 0.94 ? 0 : 1)
    }
}

// MARK: - The rollers
//
// Lying horizontally now, so the wood's shading runs top to bottom across the
// cylinder and the brass caps sit at the left and right ends.

private struct Roller: View {
    /// 1 at rest; grows as the sheet winds onto it.
    var thickness: CGFloat = 1

    var body: some View {
        ZStack {
            // Turned wood — the darker grooves are what make it read as lathed.
            RoundedRectangle(cornerRadius: 6, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [Theme.woodDark, Theme.woodLight, Theme.woodMid, Theme.woodDark],
                        startPoint: .top, endPoint: .bottom)
                )
            RoundedRectangle(cornerRadius: 6, style: .continuous)
                .strokeBorder(Color(hex: 0x241A08, alpha: 0.7), lineWidth: 1)
        }
        .frame(height: Metrics.rollerWidth * thickness)
        .overlay(alignment: .leading)  { BrassCap() }
        .overlay(alignment: .trailing) { BrassCap() }
    }
}

/// The aged brass end cap, with its little pin. 18 × 36 on a horizontal roller.
private struct BrassCap: View {
    var body: some View {
        ZStack {
            Capsule()
                .fill(
                    LinearGradient(colors: [Theme.brassLight, Theme.brass, Theme.brassDark],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                )
            Capsule()
                .strokeBorder(Color(hex: 0x5B441A, alpha: 0.8), lineWidth: 0.75)
            Circle()
                .fill(Color(hex: 0x5B441A, alpha: 0.55))
                .frame(width: 3, height: 3)      // the pin
        }
        .frame(width: Metrics.brassCapSize.height, height: Metrics.brassCapSize.width)
        .shadow(color: Color(hex: 0x1A1206, alpha: 0.5), radius: 3, y: 1)
    }
}

// MARK: - Paper texture
//
// Both of these are deliberately almost invisible. Parchment that announces
// itself looks like a texture; parchment you only notice when you look for it
// looks like paper.

private struct LedgerRules: View {
    var body: some View {
        GeometryReader { geo in
            let spacing = Metrics.ledgerRuleSpacing
            Path { path in
                var y = spacing
                while y < geo.size.height {
                    path.move(to: CGPoint(x: 0, y: y))
                    path.addLine(to: CGPoint(x: geo.size.width, y: y))
                    y += spacing
                }
            }
            .stroke(Theme.inkFaint.opacity(0.13), lineWidth: 0.5)
        }
    }
}

private struct ParchmentGrain: View {
    var body: some View {
        Canvas { context, size in
            // A fixed seed, so the paper doesn't shimmer between redraws.
            var seed: UInt64 = 0x9E3779B97F4A7C15
            func next() -> Double {
                seed = seed &* 6364136223846793005 &+ 1442695040888963407
                return Double((seed >> 33) % 10_000) / 10_000
            }
            for _ in 0..<220 {
                let x = next() * size.width
                let y = next() * size.height
                let w = 0.6 + next() * 2.2
                context.fill(
                    Path(ellipseIn: CGRect(x: x, y: y, width: w, height: 0.6)),
                    with: .color(Theme.inkFaint.opacity(0.05 + next() * 0.05))
                )
            }
        }
        .allowsHitTesting(false)
        .blendMode(.multiply)
    }
}

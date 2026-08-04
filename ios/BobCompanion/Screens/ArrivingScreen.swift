// He is coming.
//
// The one honest wait in the app: the server is composing a whole person out of
// what they wrote, and that takes real seconds. A blank screen here is the worst
// moment in the app to have one — it's the moment they've been building to, and
// nothing happening reads as broken.
//
// So it is a scene rather than a wait. Someone is walking to you from a long way
// off: a small far light low on the hill that comes steadily nearer, while four
// lines say where he's got to. No spinner, no percentage, no «creating your
// companion» — nothing is being MADE here as far as this app is concerned.
//
// The timing has to survive both extremes:
//
//   · A FAST server (2 s) must not be padded out to a fixed cutscene length —
//     that makes the app slower for no reason. There is a short floor so the
//     scene can't flicker past, and then it finishes as soon as he's ready.
//   · A SLOW server (40 s) must not run out of things to say. The lines hold on
//     the last one, and he closes only the final part of the distance when the
//     server actually answers — so «almost here» is never a lie.

import SwiftUI

struct ArrivingScreen: View {
    let story: String
    let wishes: String
    var onArrived: (String) -> Void

    /// How much of the walk is behind him, 0 → 1.
    @State private var journey: CGFloat = 0
    /// Which line is being said.
    @State private var line = 0
    /// He is written and waiting — the walk can finish whenever it's ready.
    @State private var ready = false
    @State private var name = ""
    @State private var finishing = false

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// He walks to here and no further until the server has answered. Arriving
    /// fully before he exists would be a lie, and it's the kind you feel.
    private let waitingDistance: CGFloat = 0.72
    /// Long enough that the scene registers as a scene; short enough that a fast
    /// server still feels fast.
    private let floorSeconds: Double = 5.5

    var body: some View {
        GeometryReader { geo in
            let h = geo.size.height
            let w = geo.size.width

            ZStack {
                PhotoBackground(place: .companion, treatment: .bare)

                // The light he brings with him — far and cold, near and warm.
                // This is what makes the distance readable at a glance.
                RadialGradient(
                    colors: [Theme.sun400.opacity(0.10 + 0.16 * journey),
                             Color.clear],
                    center: .init(x: 0.5, y: yFraction),
                    startRadius: 0,
                    endRadius: w * (0.4 + 0.5 * journey)
                )
                .allowsHitTesting(false)

                OrbView(state: finishing ? .speaking : .resting)
                    // Far off he is small. The scale carries the distance; the
                    // orb's own design does the rest.
                    .scaleEffect(0.24 + 0.76 * journey)
                    .opacity(0.45 + 0.55 * journey)
                    .position(x: w / 2, y: h * yFraction)

                // What's happening, in the voice of the world rather than the
                // voice of a progress bar.
                Text(Strings.arriving[min(line, Strings.arriving.count - 1)]())
                    .appFont(AppType.lede, leading: AppType.ledeLeading)
                    .foregroundStyle(Theme.onLand)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .legible()
                    .padding(.horizontal, Metrics.sideMargin)
                    .id(line)                     // so each line cross-fades in
                    .transition(.opacity)
                    .opacity(finishing ? 0 : 1)   // he's here; words step back
                    .position(x: w / 2, y: h * 0.78)
            }
        }
        .statusBarHidden(true)
        .task { await bringHim() }
    }

    /// Low on the hill when he's far, at his resting place when he's here.
    private var yFraction: CGFloat {
        let far: CGFloat = 0.60
        return far + (Metrics.opticalCentre - far) * journey
    }

    // MARK: - the walk

    private func bringHim() async {
        let started = Date()

        // The walk begins immediately, and takes its time. He covers most of
        // the ground on his own; the last of it waits for the server.
        withAnimation(.easeInOut(duration: reduceMotion ? 1.0 : 13)) {
            journey = waitingDistance
        }
        advanceLines()

        // Meanwhile, he is written.
        let client = BackendClient(baseURL: AppConfig.shared.backendURL)
        do {
            name = try await client.createCompanion(story: story, wishes: wishes).name
        } catch {
            // If the server can't be reached we don't strand them on a dead
            // screen. He arrives anyway, and says so himself once he's here.
            name = ""
        }
        ready = true

        // Don't let a two-second answer flash the whole scene past them.
        let elapsed = Date().timeIntervalSince(started)
        if elapsed < floorSeconds {
            try? await Task.sleep(nanoseconds: UInt64((floorSeconds - elapsed) * 1_000_000_000))
        }

        // The last of the distance, and the light coming up as he reaches it.
        withAnimation(.easeOut(duration: 1.5)) {
            journey = 1
            finishing = true
        }
        try? await Task.sleep(nanoseconds: 1_500_000_000)
        onArrived(name)
    }

    /// One line every few seconds, holding on the last if he's slow to come.
    private func advanceLines() {
        Task {
            for step in 1..<Strings.arriving.count {
                try? await Task.sleep(nanoseconds: 3_400_000_000)
                if finishing { return }
                withAnimation(.easeInOut(duration: 0.7)) { line = step }
            }
        }
    }
}

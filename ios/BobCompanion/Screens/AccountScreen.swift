// 7 · Account
//
// Your own things — still standing in the world, on a blurred pass of the
// meadow, kept bright enough to read as a place.
//
// The title sits high and the rows sit low: the app's own rhythm rather than a
// stock form pinned to the top. «My story» reopens the parchment scene, not a
// text box.

import SwiftUI

struct AccountScreen: View {
    @EnvironmentObject private var app: AppState
    var onClose: () -> Void

    @State private var editingStory = false

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .account, treatment: .blurred(radius: 20, dim: 0.38))

                VStack(alignment: .leading, spacing: Metrics.groupSpacing) {
                    Capsule()
                        .fill(Theme.linen.opacity(0.28))
                        .frame(width: 36, height: 5)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 12)

                    Text(Strings.accountTitle())
                        .appFont(AppType.title)
                        .foregroundStyle(Theme.linen)
                        .padding(.top, geo.size.height * 0.045)

                    Spacer(minLength: 0)

                    ListGroup {
                        HStack(spacing: 14) {
                            Monogram(letter: app.account?.initial ?? "•")
                            VStack(alignment: .leading, spacing: 2) {
                                Text(app.account?.name ?? "—")
                                    .appFont(AppType.body)
                                    .foregroundStyle(Theme.linen)
                                Text("\(Strings.rowSignedIn()) \(app.account?.provider ?? "—")")
                                    .appFont(AppType.caption)
                                    .foregroundStyle(Theme.lichen)
                            }
                            Spacer()
                            Text(Strings.rowEdit())
                                .appFont(AppType.secondary)
                                .foregroundStyle(Theme.lichen)
                        }
                        .padding(.horizontal, Metrics.dividerInset)
                        .frame(minHeight: 76)
                    }

                    ListGroup {
                        ListRow(label: Strings.rowMyStory(),
                                value: Strings.rowMyStoryHint(),
                                showsDivider: false) { editingStory = true }
                    }

                    ListGroup {
                        ListRow(label: Strings.rowSubscription(),
                                value: app.isSubscribed ? Plan.yearly.title : "—",
                                showsDivider: false) { }
                    }

                    ListGroup {
                        ListRow(label: Strings.rowSignOut(),
                                value: "›",
                                showsDivider: false) { app.signOut() }
                    }
                }
                .padding(.horizontal, Metrics.sideMargin)
                .padding(.bottom, 32)
            }
        }
        .gesture(
            DragGesture(minimumDistance: 60)
                .onEnded { if $0.translation.height > 80 { onClose() } }
        )
        // Opening "My story" returns to the parchment scene — the same scroll,
        // recognisably theirs, not a settings text field.
        .fullScreenCover(isPresented: $editingStory) {
            ScrollScreen(kind: .story, text: storyBinding) {
                editingStory = false
            }
        }
    }

    private var storyBinding: Binding<String> {
        Binding(get: { app.story }, set: { app.saveStory($0) })
    }
}

private struct Monogram: View {
    let letter: String

    var body: some View {
        ZStack {
            Circle().fill(Theme.leaf700)
            Circle().strokeBorder(Theme.hairline, lineWidth: 1)
            Text(letter)
                .appFont(AppType.title)
                .foregroundStyle(Theme.parchment)
        }
        .frame(width: 46, height: 46)
    }
}

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
    @State private var deletingAccount = false

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .account, treatment: .blurred(radius: 20, dim: 0.38))

                VStack(alignment: .leading, spacing: Metrics.groupSpacing) {
                    SheetGrabber(onClose: onClose)
                        .padding(.top, 8)

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

                    // LEAVING, and it lives here rather than in Settings on
                    // purpose: it is about the account, not about him, and it
                    // is a different thing from «Начать заново». Those two
                    // shared one button once, which is how the app came to
                    // promise a deletion that nothing performed.
                    //
                    // Clay, never red, like every other serious thing in this
                    // app — and last, where you have to have gone looking.
                    ListGroup {
                        ListRow(label: Strings.rowDeleteAccount(),
                                value: "›",
                                tone: Theme.clay,
                                showsDivider: false) { deletingAccount = true }
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
        .sheet(isPresented: $deletingAccount) {
            DeleteAccountSheet(name: app.displayName) {
                await app.deleteEverything()
            }
        }
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

// MARK: - Leaving altogether

/// The only screen in the app where a failure may NOT be softened into silence.
///
/// Everywhere else the rule holds: never show a lonely person an error. Here
/// somebody has asked for their life to be erased, and if it was not erased
/// they have to be told so plainly — an app that closes the sheet quietly and
/// leaves them believing it is done would be a worse falsehood than the one
/// this whole endpoint exists to end, because it looks like it worked.
private struct DeleteAccountSheet: View {
    let name: String
    /// True when the server actually did it.
    var onConfirm: () async -> Bool
    @Environment(\.dismiss) private var dismiss

    @State private var working = false
    @State private var failed = false

    var body: some View {
        ZStack {
            Theme.night.ignoresSafeArea()
            VStack(alignment: .leading, spacing: 22) {
                Spacer()
                Text(Strings.deleteAccountTitle())
                    .appFont(AppType.title)
                    .foregroundStyle(Theme.linen)
                Text(Strings.deleteAccountBody(name)())
                    .appFont(AppType.body, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.sage)
                    .fixedSize(horizontal: false, vertical: true)
                if failed {
                    Text(Strings.deleteAccountFailed())
                        .appFont(AppType.body, leading: AppType.bodyLeading)
                        .foregroundStyle(Theme.clay)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
                VStack(spacing: 12) {
                    AppButton(title: working ? Strings.deleteAccountWorking()
                                             : Strings.deleteAccountConfirm(),
                              tone: .quiet,
                              labelColour: Theme.clay) {
                        guard !working else { return }
                        working = true
                        failed = false
                        Task {
                            let done = await onConfirm()
                            working = false
                            if done { dismiss() } else { failed = true }
                        }
                    }
                    AppButton(title: Strings.cancel(), tone: .leaf) { dismiss() }
                        .disabled(working)
                }
            }
            .padding(.horizontal, Metrics.sideMargin)
            .padding(.bottom, 28)
        }
        .presentationDetents([.medium])
        .presentationCornerRadius(Metrics.sheetRadius)
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

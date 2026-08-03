// 6 · His Diary
//
// Not a "memory screen" — his own book, in which he writes about his friend.
// He writes; the user only reads.
//
// His REAL memory is a different thing: distilled notes, as short as possible,
// optimised so he can recall fast. That is never shown to anyone. The diary is
// written by him FROM that memory, and rewritten only when his memory of you has
// actually grown — so opening the book is instant and free most of the time.

import SwiftUI

struct DiaryScreen: View {
    @EnvironmentObject private var app: AppState
    var onClose: () -> Void

    @State private var leaves: [String] = []
    @State private var spread = 0
    @State private var isLoading = true

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .diary, treatment: .blurred(radius: 16, dim: 0.42))

                VStack(spacing: 0) {
                    // The grabber — 36 × 5 at y 62 — and the title, high.
                    Capsule()
                        .fill(Theme.linen.opacity(0.28))
                        .frame(width: 36, height: 5)
                        .padding(.top, 12)

                    Text(Strings.diaryTitle(app.displayName)())
                        .appFont(AppType.writtenHeading)
                        .foregroundStyle(Theme.linen)
                        .padding(.top, 20)

                    Spacer(minLength: 16)

                    DiaryBook(leaves: leaves.isEmpty ? [emptyPage, ""] : leaves,
                              spread: $spread)
                        .frame(maxHeight: geo.size.height * 0.62)
                        .opacity(isLoading ? 0 : 1)
                        .animation(.easeOut(duration: 0.5), value: isLoading)

                    Spacer(minLength: 12)

                    if leaves.count > 2 {
                        Text(Strings.turnThePage())
                            .appFont(AppType.caption)
                            .foregroundStyle(Theme.lichen)
                    }
                }
                .padding(.horizontal, Metrics.sideMargin)
                .padding(.bottom, 20)
            }
        }
        .task { await load() }
        // Back is a gentle downward dismiss, never a chevron in a nav bar.
        .gesture(
            DragGesture(minimumDistance: 60)
                .onEnded { if $0.translation.height > 80 { onClose() } }
        )
    }

    /// Before he knows anything: one short page in his own voice on the left
    /// leaf, the right leaf simply blank — a book that has just been opened.
    /// Never "No entries yet."
    private var emptyPage: String { Strings.diaryEmpty() }

    private func load() async {
        let client = BackendClient(baseURL: AppConfig.shared.backendURL)
        do {
            let diary = try await client.diary()
            if !diary.companion.isEmpty { app.remember(companionName: diary.companion) }
            let pages = diary.leaves()
            leaves = pages.isEmpty ? [emptyPage, ""] : pages
        } catch {
            // He simply hasn't written yet, as far as the reader is concerned.
            leaves = [emptyPage, ""]
        }
        isLoading = false
    }
}

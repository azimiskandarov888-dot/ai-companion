// How the screens connect.
//
// FIRST RUN — once, in order:
//   Sign in → Take care of him → Tell your story → Who you'd like to meet → him
//
// EVERY TIME AFTER THAT the app opens straight to the companion screen. Nothing
// else. From there, three quiet ways out — Diary, Account, Settings — each of
// which returns with a gentle downward dismiss.
//
// There is no tab bar. A tab bar would turn a friend into an app.
//
// And nobody introduces him: there is deliberately no "meet your companion"
// screen. Screen 4 ends, the companion screen opens, and he says hello and tells
// you who he is himself — the way a person would.

import SwiftUI

enum AppScreen: Equatable {
    case signIn
    case takeCare
    case story
    case meet
    case arriving        // he is being written — the one honest wait in the app
    case companion
}

enum Overlay: Identifiable, Equatable {
    case diary, account, settings
    var id: Int { hashValue }
}

struct AppFlow: View {
    @EnvironmentObject private var app: AppState
    @ObservedObject var conversation: ConversationController

    @State private var screen: AppScreen = .signIn
    @State private var overlay: Overlay?
    @State private var story = ""
    @State private var wishes = ""

    var body: some View {
        ZStack {
            switch screen {
            case .signIn:
                SignInScreen { go(.takeCare) }
                    .transition(.opacity)

            case .takeCare:
                TakeCareScreen { go(.story) }
                    .transition(.opacity)

            case .story:
                ScrollScreen(kind: .story, text: $story) {
                    app.saveStory(story)
                    go(.meet)
                }
                .transition(.opacity)

            case .meet:
                ScrollScreen(kind: .meet, text: $wishes) {
                    app.saveWishes(wishes)
                    go(.arriving)
                }
                .transition(.opacity)

            case .arriving:
                ArrivingScreen(story: app.story, wishes: app.wishes) { name in
                    if !name.isEmpty { app.remember(companionName: name) }
                    go(.companion)
                }
                .transition(.opacity)

            case .companion:
                CompanionScreen(
                    conversation: conversation,
                    onDiary:    { overlay = .diary },
                    onAccount:  { overlay = .account },
                    onSettings: { overlay = .settings }
                )
                .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.35), value: screen)
        .onAppear {
            screen = app.startingScreen
            story = app.story
            wishes = app.wishes
        }
        // The three ways out. Each rises over him and sinks back down.
        .fullScreenCover(item: $overlay) { which in
            Group {
                switch which {
                case .diary:    DiaryScreen    { overlay = nil }
                case .account:  AccountScreen  { overlay = nil }
                case .settings: SettingsScreen { overlay = nil }
                }
            }
            .environmentObject(app)
            .presentationBackground(.clear)
        }
        // He only listens while he's the screen in front of you.
        .onChange(of: screen) { _, now in
            now == .companion ? conversation.start() : conversation.stop()
        }
        .onChange(of: overlay) { _, now in
            guard screen == .companion else { return }
            now == nil ? conversation.start() : conversation.stop()
        }
    }

    private func go(_ next: AppScreen) {
        withAnimation(.easeInOut(duration: 0.35)) { screen = next }
    }
}

// MARK: - He is being written
//
// The one honest wait in the app: the server is composing a whole person from
// their story. It takes a few seconds, so instead of a spinner the scene simply
// holds, and he warms into being. No progress bar, no "generating…".

private struct ArrivingScreen: View {
    let story: String
    let wishes: String
    var onArrived: (String) -> Void

    @State private var state: OrbState = .resting

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .companion, treatment: .bare)
                OrbView(state: state)
                    .position(x: geo.size.width / 2, y: geo.size.height * Metrics.opticalCentre)
            }
        }
        .task {
            // He wakes as he is written.
            withAnimation(.easeInOut(duration: 1.2)) { state = .thinking }

            let client = BackendClient(baseURL: AppConfig.shared.backendURL)
            var name = ""
            do {
                name = try await client.createCompanion(story: story, wishes: wishes).name
            } catch {
                // If the server can't be reached, we don't strand them on a
                // dead screen — he arrives anyway and says so himself.
                name = ""
            }

            withAnimation(.easeInOut(duration: 0.8)) { state = .speaking }
            try? await Task.sleep(nanoseconds: 900_000_000)
            onArrived(name)
        }
    }
}

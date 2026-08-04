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
                    .transition(.screenChange)

            case .takeCare:
                TakeCareScreen { go(.story) }
                    .transition(.screenChange)

            // 3 and 4 are ONE place. The photograph is drawn here, once, and
            // only the sheet changes — the first rolls away, the next unrolls in
            // the same spot. Nothing about the clearing moves.
            case .story, .meet:
                ZStack {
                    PhotoBackground(place: .story, treatment: .scrim)

                    if screen == .story {
                        ScrollScreen(kind: .story, text: $story, drawsBackground: false) {
                            app.saveStory(story)
                            go(.meet)
                        }
                        .transition(.screenChange)
                    } else {
                        ScrollScreen(kind: .meet, text: $wishes, drawsBackground: false) {
                            app.saveWishes(wishes)
                            go(.arriving)
                        }
                        .transition(.screenChange)
                    }
                }
                // The land doesn't transition BETWEEN 3 and 4 — it's one view
                // that simply stays put while the sheet inside it changes. But
                // this pair still has to arrive and leave like any other screen,
                // and .identity here silently killed the outro on the two
                // screens you pass through most.
                .transition(.screenChange)

            case .arriving:
                ArrivingScreen(story: app.story, wishes: app.wishes) { name in
                    if !name.isEmpty { app.remember(companionName: name) }
                    app.markArrived()
                    go(.companion)
                }
                .transition(.screenChange)

            case .companion:
                CompanionScreen(
                    conversation: conversation,
                    onDiary:    { overlay = .diary },
                    onAccount:  { overlay = .account },
                    onSettings: { overlay = .settings }
                )
                .transition(.screenChange)
            }
        }
        .animation(.easeInOut(duration: 0.55), value: screen)
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
        // «Start over» keeps their story and clears only the friend, so the
        // app returns to screen 4 — choosing who to meet next — rather than
        // making them retell their whole life.
        .onChange(of: app.hasArrived) { _, arrived in
            guard !arrived, screen == .companion else { return }
            overlay = nil
            withAnimation(.easeInOut(duration: 0.55)) { screen = .meet }
        }
        .onChange(of: overlay) { _, now in
            guard screen == .companion else { return }
            now == nil ? conversation.start() : conversation.stop()
        }
    }

    private func go(_ next: AppScreen) {
        withAnimation(.easeInOut(duration: 0.55)) { screen = next }
    }
}

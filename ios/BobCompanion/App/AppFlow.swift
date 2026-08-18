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

    @Environment(\.scenePhase) private var scenePhase
    @State private var screen: AppScreen = .signIn
    @State private var overlay: Overlay?
    @State private var story = ""
    @State private var wishes = ""
    /// 0 the world is visible · 1 the light is fully down. The screen is only
    /// ever swapped at 1.
    @State private var veil: Double = 0
    @State private var crossing = false

    var body: some View {
        ZStack {
            // WHY THIS IS A VEIL AND NOT A .transition()
            //
            // Four attempts at SwiftUI transitions produced no visible outro,
            // and the reason is z-order, not timing. Inside a ZStack, z
            // positions are assigned IMPLICITLY by order. When the screen
            // changes, the incoming screen — a full-bleed, fully opaque
            // photograph — takes the departing screen's z position and is drawn
            // ON TOP of it. The removal transition runs perfectly and is
            // completely invisible underneath. Nothing about the animation
            // itself could ever have fixed that.
            //
            // Both documented fixes (explicit .zIndex, or an outer container)
            // work by fighting that ordering. This does something simpler and
            // deterministic: it never relies on two screens being on screen at
            // once. One always-present veil dims the world, the screen is
            // swapped while nothing can be seen, and the veil lifts. It is the
            // dissolve a film uses, and it has no identity, no insertion, no
            // removal and no z-order to get wrong.
            //
            // It also suits the app better than a cross-fade: every screen is
            // the same world, so dipping through its own deep green reads as
            // the light going down and coming back up, rather than as one
            // picture being swapped for another.
            currentScreen
                .id(placeID)
                .zIndex(0)

            Theme.night
                .ignoresSafeArea()
                .opacity(veil)
                .allowsHitTesting(veil > 0.02)   // no taps land mid-change
                .zIndex(10)                      // explicitly above everything
        }
        .onAppear {
            screen = app.startingScreen
            story = app.story
            wishes = app.wishes
        }
        // Once, quietly, at launch: does the server actually have a friend for
        // this person? It runs after the screen is already up, so nothing waits
        // on the network, and it only ever acts on a clear "no" — see
        // AppState.reconcileWithServer. If it does clear the arrival, the
        // .onChange below carries them to «кого бы вы хотели встретить».
        .task { await app.reconcileWithServer() }
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
            now == .companion ? conversation.resume() : conversation.suspend()
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
            now == nil ? conversation.resume() : conversation.suspend()
        }
        // HE HAS TO START LISTENING AGAIN AFTERWARDS. This is the other half
        // of the app-level rule that stops the loop whenever we leave the
        // foreground (BobCompanionApp) — which existed on its own, with no
        // counterpart, so the FIRST interruption of any kind made him deaf
        // permanently.
        //
        // And the very first interruption is guaranteed: a system permission
        // alert — microphone, local network — makes the app `.inactive` while
        // it is up. So the sequence that greets every new user is: he arrives,
        // the loop starts, iOS asks for the microphone, the app goes inactive,
        // the loop stops, you tap «Разрешить», the app comes back… and nothing
        // ever calls start() again. `screen` hasn't changed and `overlay`
        // hasn't changed, so neither watcher above fires.
        //
        // What that looks like is the whole of the bug report: he is on screen,
        // resting, no word beneath him, not hearing anything, indefinitely.
        // `.idle` is the one state that renders no status word at all, and
        // stop() sets exactly that.
        //
        // Every later interruption did it too — a notification banner, Control
        // Centre, a phone call, switching apps and back.
        .onChange(of: scenePhase) { _, phase in
            guard screen == .companion, overlay == nil else { return }
            guard phase == .active else {
                conversation.suspend()
                return
            }
            // Opened BY a "start talking" Shortcut — Back Tap, the Action
            // button, a Control Centre control, a widget, an NFC sticker.
            // Recording cannot begin in the background at all (iOS refuses
            // it), so the whole point of those surfaces is to arrive here
            // already listening rather than needing a second tap.
            if PendingWish.takeStartListening() {
                conversation.turnOn()
            } else {
                conversation.resume()
            }
        }
    }

    @ViewBuilder private var currentScreen: some View {
        switch screen {
        case .signIn:
            SignInScreen { go(.takeCare) }

        case .takeCare:
            TakeCareScreen { go(.story) }

        // 3 and 4 are ONE place. The photograph is drawn here, once, and only
        // the sheet changes — the first rolls away, the next unrolls in the
        // same spot. Nothing about the clearing moves.
        case .story, .meet:
            ZStack {
                PhotoBackground(place: .story, treatment: .scrim)

                if screen == .story {
                    ScrollScreen(kind: .story, text: $story, drawsBackground: false) {
                        app.saveStory(story)
                        go(.meet)
                    }
                    .transition(.opacity)
                } else {
                    ScrollScreen(kind: .meet, text: $wishes, drawsBackground: false) {
                        app.saveWishes(wishes)
                        go(.arriving)
                    }
                    .transition(.opacity)
                }
            }

        case .arriving:
            ArrivingScreen(story: app.story, wishes: app.wishes) { name in
                if !name.isEmpty { app.remember(companionName: name) }
                app.markArrived()
                go(.companion)
            }

        case .companion:
            CompanionScreen(
                conversation: conversation,
                onDiary:    { overlay = .diary },
                onAccount:  { overlay = .account },
                onSettings: { overlay = .settings }
            )
        }
    }

    /// What counts as «somewhere else» for the purpose of transitions.
    ///
    /// Screens 3 and 4 deliberately share one value: they are the same clearing
    /// an hour apart, so moving between them must NOT rebuild the screen or
    /// re-fade the land. Everywhere else gets its own, and so gets a full
    /// arrival and departure.
    private var placeID: Int { placeID(for: screen) }

    private func placeID(for screen: AppScreen) -> Int {
        switch screen {
        case .signIn:        return 0
        case .takeCare:      return 1
        case .story, .meet:  return 2
        case .arriving:      return 3
        case .companion:     return 4
        }
    }

    // MARK: - crossing from one place to another

    /// How long the light takes to go down, and to come back up. Down is
    /// quicker than up: leaving should feel decisive, arriving unhurried.
    private enum Cross {
        static let down = 0.34
        static let up   = 0.50
    }

    private func go(_ next: AppScreen) {
        // Screens 3 and 4 are the same clearing. Moving between them must not
        // dim anything — the scroll rolls away and the next unrolls in place.
        guard placeID(for: next) != placeID(for: screen) else {
            withAnimation(.easeInOut(duration: 0.55)) { screen = next }
            return
        }
        guard !crossing else { return }          // a double tap can't double-fire
        crossing = true

        withAnimation(.easeIn(duration: Cross.down)) { veil = 1 }

        DispatchQueue.main.asyncAfter(deadline: .now() + Cross.down + 0.05) {
            screen = next                        // swapped while nothing shows
            withAnimation(.easeOut(duration: Cross.up)) { veil = 0 }
            DispatchQueue.main.asyncAfter(deadline: .now() + Cross.up) {
                crossing = false
            }
        }
    }
}

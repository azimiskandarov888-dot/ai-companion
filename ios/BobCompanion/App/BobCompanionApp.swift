// The app entry point.
//
// A voice friend. He never speaks first — the conversation starts when you do.
// The backend holds every API key and does the thinking; this app is ears, a
// mouth, and a place to stand.
//
// After the first run the app opens on the companion screen forever, so the
// thing you see when you pick up the phone is him, not a menu.

import SwiftUI

@main
struct BobCompanionApp: App {
    @StateObject private var app = AppState()
    @StateObject private var conversation = ConversationController()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            AppFlow(conversation: conversation)
                .environmentObject(app)
                .preferredColorScheme(.dark)      // the world is always in shade
                .tint(Theme.sun400)
                .onChange(of: scenePhase) { _, phase in
                    // iOS suspends a normal app's microphone when it's
                    // backgrounded, so the loop lives only while we're on
                    // screen. The docked design keeps this screen foregrounded
                    // all day (Guided Access). Background listening is a later
                    // layer — see docs/ALWAYS-ON.md.
                    //
                    // STOPPING ONLY. Starting again lives in AppFlow, which is
                    // the only place that knows whether the companion screen
                    // is even the one in front of you. This half is kept here
                    // anyway, deliberately: releasing the microphone the
                    // instant we lose the foreground is a promise to the
                    // person holding the phone, and it should not depend on
                    // any screen's logic being right.
                    //
                    // For a long time this was the ONLY half that existed, and
                    // the first permission alert — which makes the app
                    // inactive while it is up — left him permanently deaf.
                    if phase != .active { conversation.suspend() }
                }
        }
    }
}

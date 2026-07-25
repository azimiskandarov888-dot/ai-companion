// The app entry point.
//
// Bob is voice-only. He never speaks first — the conversation starts when the
// elder speaks. This app runs "docked": a phone in a stand by his chair, plugged
// in, this one screen always open (mode A in docs/BUILD-PLAN.md). It listens,
// sends his voice to our backend, and plays Bob's warm reply back.
//
// The backend holds all the API keys and does the thinking. This app is just
// ears + mouth + a gentle face.

import SwiftUI

@main
struct BobCompanionApp: App {
    @StateObject private var conversation = ConversationController()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            CompanionView(conversation: conversation)
                .onChange(of: scenePhase) { _, phase in
                    // Keep the loop alive only while the app is on screen. iOS
                    // suspends a normal app's microphone when it's backgrounded;
                    // the docked design keeps this screen foregrounded all day
                    // (Guided Access). Background listening / floating window is a
                    // later layer — see docs/BUILD-PLAN.md §6 and ALWAYS-ON.md.
                    switch phase {
                    case .active:   conversation.start()
                    case .inactive, .background: conversation.stop()
                    @unknown default: break
                    }
                }
        }
    }
}

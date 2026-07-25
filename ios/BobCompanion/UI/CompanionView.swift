// The one and only screen. A gentle face fills it, plus a soft Russian status
// word. There is NO text box and NO button to press — he can't read or type, and
// he never has to. He just talks; Bob answers.
//
// A long-press anywhere opens the hidden Settings screen (for you, to set the
// backend address). He would never find it by accident.

import SwiftUI

struct CompanionView: View {
    @ObservedObject var conversation: ConversationController
    @State private var showSettings = false

    private var statusWord: String {
        switch conversation.status {
        case .idle:       return " "
        case .listening:  return "слушаю"
        case .thinking:   return "думаю…"
        case .speaking:   return "говорю"
        case .problem:    return "минутку…"
        }
    }

    var body: some View {
        ZStack {
            Color(red: 0.09, green: 0.10, blue: 0.13).ignoresSafeArea()

            VStack(spacing: 44) {
                BreathingFace(status: conversation.status)

                Text(statusWord)
                    .font(.system(size: 26, weight: .light, design: .rounded))
                    .foregroundStyle(.white.opacity(0.55))
                    .animation(.easeInOut, value: statusWord)

                #if DEBUG
                // Only while testing: shows what Bob heard and said, so you can
                // watch the conversation. Never shown in a release build.
                VStack(spacing: 8) {
                    if !conversation.lastHeard.isEmpty {
                        Text("он: \(conversation.lastHeard)")
                            .foregroundStyle(.white.opacity(0.35))
                    }
                    if !conversation.lastReply.isEmpty {
                        Text("Боб: \(conversation.lastReply)")
                            .foregroundStyle(.white.opacity(0.5))
                    }
                }
                .font(.system(size: 14))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
                #endif
            }
            .padding()
        }
        .contentShape(Rectangle())
        .onLongPressGesture(minimumDuration: 1.5) { showSettings = true }
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
        .statusBarHidden(true)
        .persistentSystemOverlays(.hidden)
    }
}

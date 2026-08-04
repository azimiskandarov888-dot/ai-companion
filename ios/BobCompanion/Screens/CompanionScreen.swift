// 5 · Companion — the hero, and after onboarding the only screen the app opens to.
//
// They just talk — hands-free, out loud — and he answers. He listens by default:
// no button to hold, no "tap to speak". A natural pause ends their turn.
// Interrupting him stops him, like a person.
//
// The ONLY feedback is the orb. No waveform, no level meter, no microphone icon,
// no transcript. The hills stay readable at 52 % brightness so you can tell where
// you are at 2 a.m.
//
// The brass ring at the bottom edge is the only chrome. Resting shows no word at
// all, which is the point: this screen has to be liveable with all day.

import SwiftUI

struct CompanionScreen: View {
    @ObservedObject var conversation: ConversationController
    @EnvironmentObject private var app: AppState

    var onDiary: () -> Void
    var onAccount: () -> Void
    var onSettings: () -> Void

    @State private var navOpen = false
    @State private var showMicHelp = false

    /// The conversation's state, expressed as the orb sees it.
    private var orbState: OrbState {
        switch conversation.status {
        case .idle:      return .resting
        case .listening: return .listening
        case .thinking:  return .thinking
        case .speaking:  return .speaking
        case .problem:   return .unreachable
        }
    }

    var body: some View {
        GeometryReader { geo in
            let h = geo.size.height

            ZStack {
                // Already graded to night by grade.py — nothing more over it, or
                // it flattens into a black rectangle.
                PhotoBackground(place: .companion, treatment: .bare)

                // Him, on the optical centre. `.position` puts his CENTRE there,
                // which is what 45.5 % means.
                OrbView(state: orbState)
                    .arrive(.first, rise: 0)
                    .position(x: geo.size.width / 2, y: h * Metrics.opticalCentre)

                // The status word, below him at 56.9 %.
                StatusWord(state: orbState)
                    .arrive(.second)
                    .position(x: geo.size.width / 2, y: h * Metrics.statusWordY)

                // When he can't hear you, he says so himself — on this screen,
                // in his own words. Never a banner, never an error code.
                if case .problem = conversation.status {
                    Text(Strings.cannotHear())
                        .appFont(AppType.body)
                        .foregroundStyle(Theme.onLand)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, Metrics.sideMargin)
                        .position(x: geo.size.width / 2, y: h * 0.63)
                        .transition(.opacity)
                }

                VStack {
                    Spacer()
                    BrassRing(isOpen: $navOpen,
                              onDiary: onDiary,
                              onAccount: onAccount,
                              onSettings: onSettings)
                }
                .arrive(.object)
            }
            .animation(.easeInOut(duration: 0.45), value: conversation.status)
        }
        .statusBarHidden(true)
        .persistentSystemOverlays(.hidden)
        .task { await checkMicrophone() }
        .sheet(isPresented: $showMicHelp) { MicrophoneHelp() }
    }

    private func checkMicrophone() async {
        showMicHelp = !(await AudioSessionManager.requestMicPermission())
    }
}

/// He needs to be able to hear you. Warm, not scolding — and one button, not a
/// list of instructions.
private struct MicrophoneHelp: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            PhotoBackground(place: .companion, treatment: .blurred())
            VStack(spacing: 24) {
                Spacer()
                Text(Strings.needsMicrophone())
                    .appFont(AppType.body, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.linen)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer()
                AppButton(title: Strings.openSettings(), tone: .sun) {
                    if let url = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(url)
                    }
                    dismiss()
                }
            }
            .padding(.horizontal, Metrics.sideMargin)
            .padding(.bottom, 32)
        }
        .presentationDetents([.medium])
        .presentationBackground(.clear)
    }
}

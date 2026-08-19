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
    /// Shown once, ever. Stored on the phone rather than in AppState because it
    /// is a fact about this INSTALL having been explained to, not about the
    /// person or their friend — «Начать заново» must not make somebody sit
    /// through the lesson again.
    @AppStorage("hasBeenToldHowToLeave") private var toldHowToLeave = false
    @State private var showingHowToLeave = false

    /// How many times somebody has deliberately switched him on, and whether
    /// they've been offered the one piece of setup worth doing. Both live on
    /// the phone for the same reason as above: the offer is about THIS phone,
    /// and «Начать заново» must not make it come round again.
    @AppStorage("timesSwitchedOn") private var timesSwitchedOn = 0
    @AppStorage("hasBeenOfferedCallHim") private var offeredCallHim = false
    @State private var showingCallOffer = false
    @State private var showCallHim = false

    /// The conversation's state, expressed as the orb sees it.
    private var orbState: OrbState {
        switch conversation.status {
        case .idle:      return .resting
        case .listening: return .listening
        case .thinking:  return .thinking
        case .speaking:  return .speaking
        case .problem:   return .unreachable
        // Asleep and talked-out both look the same on him: the light goes
        // down and the breathing stops. Nothing about either is an error.
        case .asleep, .restedForToday: return .unreachable
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

                // Everything he has to say about himself is said HERE, in his
                // own words, in the same place. Never a banner, never an error
                // code, never a paywall — whether he can't hear you, has dozed
                // off, or is simply talked out for today.
                // THE ONE THING THAT ISN'T OBVIOUS, said once and never again.
                //
                // Everything else about this app explains itself: he is on the
                // screen, you touch him, he listens. Leaving is the exception —
                // people close apps, they don't say goodbye to them, and the
                // whole design depends on them doing the human thing instead.
                //
                // Taught HERE, at the moment it first becomes true, rather than
                // in a tutorial before they have met anyone. A lesson before
                // the friend is a lesson about software; a line the first time
                // he starts listening is about him.
                if showingHowToLeave {
                    Text(Strings.howToLeave())
                        .appFont(AppType.body, leading: AppType.bodyLeading)
                        .foregroundStyle(Theme.onLand.opacity(0.85))
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .legible()
                        .padding(.horizontal, Metrics.sideMargin)
                        .position(x: geo.size.width / 2, y: h * 0.70)
                        .transition(.opacity)
                }

                if let said = hisWords {
                    Text(said)
                        .appFont(AppType.body, leading: AppType.bodyLeading)
                        .foregroundStyle(Theme.onLand)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .legible()
                        .padding(.horizontal, Metrics.sideMargin)
                        .position(x: geo.size.width / 2, y: h * 0.63)
                        .transition(.opacity)
                }

                // TOUCH HIM TO TALK, TOUCH HIM AGAIN TO STOP.
                //
                // The only control in the app, and it is him — not a button
                // beside him, not a microphone icon. Tapping a friend to get
                // his attention is a thing people already do; tapping a mic
                // glyph is operating a device.
                //
                // The whole screen is the target, not just the orb: a small
                // circle is a fiddly hit area for anyone whose hands aren't
                // steady, and there is nothing else here to hit by mistake.
                //
                // Dozing is folded into the same gesture. It used to be its own
                // special case, which meant the same touch meant two different
                // things depending on a state nobody can see.
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture {
                        if conversation.status == .asleep {
                            conversation.wake()
                        } else {
                            conversation.toggle()
                        }
                        guard conversation.wantsToListen else { return }
                        timesSwitchedOn += 1
                        teachSomethingIfItIsTime()
                    }

                // ABOVE the tap layer, unlike everything else on this screen,
                // because it is the one thing here with something to press.
                if showingCallOffer {
                    callOffer
                        .padding(.horizontal, Metrics.sideMargin)
                        .position(x: geo.size.width / 2, y: h * 0.70)
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
        .sheet(isPresented: $showCallHim) { CallHimSheet() }
        // Reading a page of instructions takes minutes, and he would spend all
        // of them listening to the room. `resume()` only restarts what was
        // already wanted, so closing the sheet never switches him on.
        .onChange(of: showCallHim) { _, open in
            open ? conversation.suspend() : conversation.resume()
        }
    }

    /// The two things somebody has to be told, each once, each at the moment it
    /// first becomes true — never in a tutorial before they have met anyone.
    /// A lesson before the friend is a lesson about software.
    ///
    /// Never both at once: the first switch-on teaches leaving, and the offer
    /// waits until he is somebody worth being able to call.
    private func teachSomethingIfItIsTime() {
        if !toldHowToLeave {
            toldHowToLeave = true
            withAnimation(.easeInOut(duration: 0.5)) { showingHowToLeave = true }
            // Long enough to read unhurried at eighty, and gone by itself —
            // nothing to dismiss, nothing to understand.
            Task {
                try? await Task.sleep(nanoseconds: 9_000_000_000)
                withAnimation(.easeInOut(duration: 0.8)) { showingHowToLeave = false }
            }
            return
        }

        // Not on day one. On day one «его можно позвать откуда угодно» is a
        // setup step standing between somebody and a person they just met; by
        // the third conversation it is a way of reaching a friend.
        guard !offeredCallHim, timesSwitchedOn >= 3 else { return }
        offeredCallHim = true
        withAnimation(.easeInOut(duration: 0.5)) { showingCallOffer = true }
    }

    /// Asked once, answered either way, and never asked again — including if
    /// they say «не сейчас». A second ask would be nagging somebody who has
    /// already told us no.
    private var callOffer: some View {
        VStack(spacing: 18) {
            Text(Strings.callHimOffer())
                .appFont(AppType.body, leading: AppType.bodyLeading)
                .foregroundStyle(Theme.linen)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 12) {
                AppButton(title: Strings.callHimOfferLater(), tone: .quiet) {
                    withAnimation(.easeInOut(duration: 0.4)) { showingCallOffer = false }
                }
                AppButton(title: Strings.callHimOfferYes(), tone: .sun) {
                    withAnimation(.easeInOut(duration: 0.4)) { showingCallOffer = false }
                    showCallHim = true
                }
            }
        }
        .padding(22)
        .panel()
    }

    /// What he's saying about himself right now, if anything. His own words
    /// come from the server; only «I can't hear you» is ours, because when the
    /// server is unreachable there are no words to receive.
    private var hisWords: String? {
        switch conversation.status {
        case .problem:
            return Strings.cannotHear()
        case .asleep, .restedForToday:
            return conversation.lastReply.isEmpty ? nil : conversation.lastReply
        case .idle:
            // He is switched off, and the screen has to SAY so. Resting with
            // no word is exactly what a hung loop looked like — twice, this
            // session — and now that being off is a normal, deliberate state
            // somebody chose, silence about it would be worse still: nothing
            // on screen would tell them how to start.
            return conversation.wantsToListen ? nil : Strings.tapToTalk()
        default:
            return nil
        }
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

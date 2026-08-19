// 8 · Settings
//
// Deliberately ordinary, and still standing in the same place. Three small
// groups with air between them instead of one long block; nothing square,
// nothing edge-to-edge. It may be plain, but it is not a flat black screen.
//
// «Start over» is clay, never red, and it opens a slow plain sheet that says
// what will be lost — in his name. Parting with a friend is serious.

import AVFoundation
import SwiftUI

struct SettingsScreen: View {
    @EnvironmentObject private var app: AppState
    var onClose: () -> Void

    @State private var showStartOver = false
    @State private var showServer = false
    @State private var showCallHim = false
    @State private var language = Strings.language

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .settings, treatment: .blurred(radius: 20, dim: 0.44))

                ScrollView {
                    VStack(alignment: .leading, spacing: Metrics.groupSpacing) {
                        SheetGrabber(onClose: onClose)
                            .padding(.top, 8)

                        Text(Strings.settingsTitle())
                            .appFont(AppType.title)
                            .foregroundStyle(Theme.linen)
                            .padding(.top, geo.size.height * 0.045)

                        // Only what actually does something. His voice,
                        // notifications and the data export were rows that
                        // looked live and did nothing when tapped — which is
                        // worse than not offering them. They come back when
                        // they work.
                        ListGroup {
                            // First, and on purpose. It is the only setting
                            // here that changes what he IS: a friend you call,
                            // rather than an app you remember to open.
                            ListRow(label: Strings.rowCallHim(),
                                    value: Strings.rowCallHimHint()) { showCallHim = true }
                            ListRow(label: Strings.rowLanguage(),
                                    value: language.displayName) { toggleLanguage() }
                            ListRow(label: Strings.rowServer(),
                                    value: AppConfig.shared.backendURLString,
                                    showsDivider: false) { showServer = true }
                        }

                        // Parting, and the version
                        ListGroup {
                            ListRow(label: Strings.rowStartOver(),
                                    value: "›",
                                    tone: Theme.clay) { showStartOver = true }
                            ListRow(label: Strings.rowAbout(),
                                    value: AppInfo.version,
                                    showsDivider: false)
                        }
                    }
                    .padding(.horizontal, Metrics.sideMargin)
                    .padding(.bottom, 40)
                }
            }
        }
        .gesture(
            DragGesture(minimumDistance: 60)
                .onEnded { if $0.translation.height > 80 { onClose() } }
        )
        .sheet(isPresented: $showServer) { ServerSheet() }
        .sheet(isPresented: $showCallHim) { CallHimSheet() }
        .sheet(isPresented: $showStartOver) {
            StartOverSheet(name: app.displayName) {
                app.startOver()
                showStartOver = false
                onClose()
            }
        }
    }

    private func toggleLanguage() {
        language = language == .russian ? .english : .russian
        Strings.language = language
    }
}

// MARK: - Parting with a friend

private struct StartOverSheet: View {
    let name: String
    var onConfirm: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Theme.night.ignoresSafeArea()
            VStack(alignment: .leading, spacing: 22) {
                Spacer()
                Text(Strings.rowStartOver())
                    .appFont(AppType.title)
                    .foregroundStyle(Theme.linen)
                Text(Strings.startOverBody(name)())
                    .appFont(AppType.body, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.sage)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer()
                VStack(spacing: 12) {
                    // The destructive action is the QUIET one here. Nothing
                    // gold, nothing red — you shouldn't be nudged into it.
                    AppButton(title: Strings.startOverConfirm(),
                              tone: .quiet,
                              labelColour: Theme.clay) { onConfirm() }
                    AppButton(title: Strings.cancel(), tone: .leaf) { dismiss() }
                }
            }
            .padding(.horizontal, Metrics.sideMargin)
            .padding(.bottom, 28)
        }
        .presentationDetents([.medium])
        .presentationCornerRadius(Metrics.sheetRadius)
    }
}

// MARK: - The setup robot

/// A page of instructions is the thing people bounce off. «Ой, сколько всего,
/// не хочу» — and the app is deleted before anybody has met anyone.
///
/// So the setup is SPOKEN, one step at a time, by something that says outright
/// what it is: a robot, identical for everybody, that knows nothing about you
/// and will not be back. It reads each step aloud in the phone's own synthetic
/// voice and shows that step — and only that step — on screen. Nothing scrolls.
/// Nothing is a wall.
///
/// WHY THE CONFESSION MATTERS. A voice that guides you feels like somebody, and
/// an unnamed somebody in this app would be assumed to be the friend — which
/// would make the friend a manual with a face. Saying «я робот» in the first
/// breath prevents that, and does something better besides: one openly
/// mechanical voice at the start is the cheapest possible way to establish, by
/// contrast, that the other voice isn't one. It is the same reason it uses the
/// phone's flat synthetic voice rather than the warm one — nobody could
/// confuse the two, and it costs nothing.
///
/// WHY IT'S ALLOWED TO NAME MENUS. Everywhere else in this app, naming a
/// Settings path would be a failure. Here it is the entire job, and the job is
/// worth it: without this, he is an app you must remember to open, and
/// remembering to open an app is exactly the effort a very old, very tired
/// person does not have.
///
/// The ways are ordered by how little the hands have to do.
@MainActor
struct SetupRobot: View {
    /// What it says, in order. The first line is always «я не ваш друг».
    let script: [Phrase]
    /// Called when it has finished, or been skipped. Both count as done —
    /// nobody is made to sit through this. The flag says which, because what
    /// somebody was actually told changes what they still need telling.
    var onFinished: (_ heardItAll: Bool) -> Void

    @State private var step = 0
    @State private var voice = SpeechVoice()
    @State private var speaking = false
    /// Which line is the current one. Bumped on every step so a line that was
    /// cut off can tell it is no longer the one being spoken.
    @State private var generation = 0

    private var line: String { script[min(step, script.count - 1)]() }
    private var isLast: Bool { step >= script.count - 1 }

    var body: some View {
        ZStack {
            // Plain and dim, and deliberately NOT one of the photographs. This
            // is the only screen in the app that isn't a place.
            Theme.night.ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                // A flat ring, not the orb. It does not breathe and it does not
                // glow: whatever else somebody takes from this screen, they
                // must not take away that they have met him.
                Circle()
                    .strokeBorder(Theme.lichen.opacity(speaking ? 0.9 : 0.4), lineWidth: 2)
                    .frame(width: 54, height: 54)
                    .animation(.easeInOut(duration: 0.35), value: speaking)

                Spacer().frame(height: 40)

                Text(line)
                    .appFont(AppType.body, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.linen)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .id(step)                    // each step cross-fades in
                    .transition(.opacity)

                Spacer()

                VStack(spacing: 12) {
                    AppButton(title: isLast ? Strings.done() : Strings.robotNext(),
                              tone: .sun) { advance() }
                    // Always available, on every step. Somebody who wants out
                    // of this must never have to hear the rest of it first.
                    Button(action: { finish(heardItAll: false) }) {
                        Text(Strings.robotSkip())
                            .appFont(AppType.caption)
                            .foregroundStyle(Theme.lichen)
                            .frame(minHeight: Metrics.minTouch)
                    }
                }
            }
            .padding(.horizontal, Metrics.sideMargin)
            .padding(.bottom, 34)
        }
        .task { await say() }
        .onDisappear { voice.stop() }
    }

    private func advance() {
        guard !isLast else { return finish(heardItAll: true) }
        withAnimation(.easeInOut(duration: 0.35)) { step += 1 }
        Task { await say() }
    }

    private func finish(heardItAll: Bool) {
        voice.stop()
        onFinished(heardItAll)
    }

    /// Read the current step aloud. Reading is never a gate: the «Дальше»
    /// button works the whole time, so anybody who reads faster than the voice
    /// talks — or who has the sound off entirely — is never held up.
    private func say() async {
        // First, and before anything can suspend: cutting the previous line
        // off is what releases the previous call's continuation. Two live
        // `speak`s would strand one of them for good.
        voice.stop()
        generation += 1
        let mine = generation

        // The conversation's own session may have just been torn down, or
        // never raised at all (this runs before the friend exists). Playback
        // is all this needs.
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
        try? session.setActive(true, options: [])

        speaking = true
        await voice.speak(line)
        // The cut-off call resumes too, and gets here AFTER its replacement
        // has already started talking. Only the current one may put the ring
        // out.
        if mine == generation { speaking = false }
    }
}

// MARK: - How to call him

/// The robot, running the walkthrough that sends people into Settings — which
/// is exactly why it is a sheet they can leave and come back to, rather than
/// part of the arrival.
struct CallHimSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        SetupRobot(script: [Strings.robotWhoIAm] + Strings.robotSetUpCalling) { _ in
            dismiss()
        }
        .presentationDetents([.large])
        .presentationCornerRadius(Metrics.sheetRadius)
    }
}

// MARK: - Where the backend lives

struct ServerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var trouble = Trouble.shared
    @State private var address = AppConfig.shared.backendURLString
    @State private var verdict: String = ""
    @State private var verdictIsGood = false
    @State private var checking = false

    var body: some View {
        ZStack {
            Theme.night.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text(Strings.rowServer())
                        .appFont(AppType.title)
                        .foregroundStyle(Theme.linen)
                        .padding(.top, 28)

                    TextField("http://192.168.1.50:8000", text: $address)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .appFont(AppType.body)
                        .foregroundStyle(Theme.linen)
                        .padding(.horizontal, 16)
                        .frame(minHeight: Metrics.rowHeight)
                        .panel()

                    Text(Strings.language == .russian
                         ? "Пока вы тестируете — это адрес вашего Mac в той же сети Wi-Fi."
                         : "While you're testing, this is your Mac's address on the same Wi-Fi.")
                        .appFont(AppType.caption)
                        .foregroundStyle(Theme.lichen)
                        .fixedSize(horizontal: false, vertical: true)

                    // The one screen in the app allowed to be technical. He
                    // never says any of this — you have to come here and ask.
                    AppButton(title: checking
                              ? (Strings.language == .russian ? "Проверяю…" : "Checking…")
                              : (Strings.language == .russian ? "Проверить связь" : "Check the connection"),
                              tone: .sun) {
                        Task { await check() }
                    }
                    .disabled(checking)

                    if !verdict.isEmpty {
                        Text(verdict)
                            .appFont(AppType.caption, leading: AppType.bodyLeading)
                            .foregroundStyle(verdictIsGood ? Theme.linen : Theme.sun300)
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(16)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .panel()
                    }

                    if !trouble.lastFailure.isEmpty, trouble.lastFailure != verdict {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(Strings.language == .russian
                                 ? "В прошлый раз разговор не дошёл:"
                                 : "Last time a turn didn't get through:")
                                .appFont(AppType.caption)
                                .foregroundStyle(Theme.lichen)
                            Text(trouble.lastFailure)
                                .appFont(AppType.caption, leading: AppType.bodyLeading)
                                .foregroundStyle(Theme.linen)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .padding(16)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .panel()
                    }

                    AppButton(title: Strings.done(), tone: .leaf) {
                        save()
                        dismiss()
                    }
                    .padding(.top, 8)
                    .padding(.bottom, 24)
                }
                .padding(.horizontal, Metrics.sideMargin)
            }
            .scrollDismissesKeyboard(.interactively)
        }
        .presentationDetents([.medium, .large])
        .presentationCornerRadius(Metrics.sheetRadius)
    }

    private func save() {
        AppConfig.shared.backendURLString =
            address.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Checking has to use the address currently TYPED, not the saved one —
    /// otherwise you correct the address, press check, and it tests the old one.
    @MainActor
    private func check() async {
        save()
        checking = true
        defer { checking = false }

        switch await ConnectionCheck.run() {
        case .reachable(let summary):
            verdict = summary
            verdictIsGood = true
            Trouble.shared.clear()
        case .unreachable(let reason):
            verdict = reason
            verdictIsGood = false
        }
    }
}

enum AppInfo {
    /// The app's own name lives here and nowhere else — renaming is one line.
    static let displayName = "Bob"
    static var version: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        return "v\(v)"
    }
}

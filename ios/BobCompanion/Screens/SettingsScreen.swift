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
        // Passed explicitly rather than relying on a sheet inheriting it —
        // which is how every other cover in this app is written, and the
        // reason it opens at all instead of trapping on a missing object.
        .sheet(isPresented: $showCallHim) { CallHimSheet().environmentObject(app) }
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

/// Whether the robot is on screen right now.
///
/// It exists because the robot's whole job is to send people OUT of the app —
/// into Settings — and bring them back. Coming back to the foreground is
/// exactly what AppFlow watches for to start him listening again, and without
/// this the microphone would come on underneath the robot, mid-sentence,
/// every single time somebody followed an instruction correctly.
///
/// A plain static rather than anything cleverer because the two sides can't
/// hold a reference to each other: the sheet belongs to the companion screen,
/// and the rule about the foreground belongs to the flow above it.
@MainActor
enum SetupRobotIsUp {
    static var yes = false
}

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
    /// What it says and asks for, in order.
    let script: [RobotStep]
    /// Called when it has finished, or been skipped. Both count as done —
    /// nobody is made to sit through this. The flag says which, because what
    /// somebody was actually told changes what they still need telling.
    var onFinished: (_ heardItAll: Bool) -> Void

    @State private var step = 0
    @State private var voice = SpeechVoice()
    @State private var player = AudioPlayer()
    @State private var speaking = false
    /// The ring is lit the same way his orb is lit when he's listening. That
    /// is the entire point of the two tap steps: the state somebody switches
    /// on here is the state they'll be looking at for the next ten years.
    @State private var lit = false
    /// Which line is the current one. Bumped on every step so a line that was
    /// cut off can tell it is no longer the one being spoken.
    @State private var generation = 0

    private var here: RobotStep { script[min(step, script.count - 1)] }
    private var isLast: Bool { step >= script.count - 1 }
    private var awaitingTouch: Bool {
        here.wants == .aTapOnHim || here.wants == .anotherTap
    }

    var body: some View {
        ZStack {
            // Plain and dim, and deliberately NOT one of the photographs. This
            // is the only screen in the app that isn't a place.
            Theme.night.ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()
                ring
                Spacer().frame(height: 44)

                Text(here.line())
                    .appFont(AppType.body, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.linen)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .id(step)                    // each step cross-fades in
                    .transition(.opacity)

                Spacer()
                controls
            }
            .padding(.horizontal, Metrics.sideMargin)
            .padding(.bottom, 34)
        }
        .task { await say() }
        .onAppear { SetupRobotIsUp.yes = true }
        .onDisappear {
            SetupRobotIsUp.yes = false
            voice.stop()
            player.stop()
        }
    }

    /// A flat ring, never the orb. It lights up and goes out exactly as he
    /// does, because that is the lesson — but it does not breathe and it does
    /// not glow, because whatever else somebody takes away from this screen,
    /// it must not be that they have already met him.
    private var ring: some View {
        Circle()
            .strokeBorder(ringColour, lineWidth: lit ? 3 : 2)
            // Bigger on the steps that are asking to be touched, so the thing
            // to do is obvious without an arrow or the word «кнопка».
            .frame(width: awaitingTouch ? 78 : 64, height: awaitingTouch ? 78 : 64)
            // And a far bigger target than it looks, because on those steps it
            // is the only thing on screen that does anything — and the hands
            // reaching for it are the reason this app exists.
            .frame(width: 150, height: 150)
            .contentShape(Circle())
            .animation(.easeInOut(duration: 0.35), value: lit)
            .animation(.easeInOut(duration: 0.35), value: speaking)
            .animation(.easeInOut(duration: 0.35), value: step)
            .onTapGesture {
                guard awaitingTouch else { return }
                // Lit after the first tap, out after the second — which is the
                // whole lesson, performed rather than described.
                lit = (here.wants == .aTapOnHim)
                advance()
            }
    }

    private var ringColour: Color {
        if lit { return Theme.sun300.opacity(0.95) }
        if awaitingTouch { return Theme.linen.opacity(0.8) }
        return Theme.lichen.opacity(speaking ? 0.85 : 0.4)
    }

    @ViewBuilder
    private var controls: some View {
        VStack(spacing: 12) {
            // On a tap step there is deliberately NO «Дальше». The tap is the
            // lesson; offering a way past it teaches nothing and everybody
            // takes it.
            switch here.wants {
            // He is mid-flow and carries on by himself. Nothing to press —
            // which is the whole point: being told something should not be
            // twenty small decisions.
            case .nothing, .aTapOnHim, .anotherTap:
                EmptyView()

            // The one real choice in the script.
            case .nowOrLater:
                AppButton(title: Strings.robotNow(), tone: .sun) { advance() }
                AppButton(title: Strings.robotLater(), tone: .quiet) { skipTheOptionalPart() }

            case .tapNextOrOpenShortcuts:
                AppButton(title: Strings.robotOpenShortcuts(), tone: .quiet) {
                    open("shortcuts://")
                }
                nextButton

            // Apple has no way to send anybody to a particular page of
            // Settings — only to this app's own — and the private URLs that
            // do get apps rejected. So this lands one tap away from the top
            // of Settings, which is still one whole problem fewer: finding a
            // grey cog on a crowded home screen.
            case .tapNextOrOpenSettings:
                AppButton(title: Strings.robotOpenSettings(), tone: .quiet) {
                    open(UIApplication.openSettingsURLString)
                }
                nextButton

            case .tapNext:
                nextButton
            }

            // Always available, on every step including the tap ones. Somebody
            // who wants out of this must never have to hear the rest first.
            Button(action: { finish(heardItAll: false) }) {
                Text(Strings.robotSkip())
                    .appFont(AppType.caption)
                    .foregroundStyle(Theme.lichen)
                    .frame(minHeight: Metrics.minTouch)
            }
        }
    }

    private var nextButton: some View {
        AppButton(title: isLast ? Strings.done() : Strings.robotNext(),
                  tone: .sun) { advance() }
    }

    /// A bundled recording of this line, if one has been added. Several
    /// extensions are tried so nobody has to convert anything: record it
    /// however is easiest, drop it in, name it after the slug.
    private func recording(named slug: String?) -> Data? {
        guard let slug else { return nil }
        for ext in ["m4a", "mp3", "caf", "wav", "aiff"] {
            if let url = Bundle.main.url(forResource: slug, withExtension: ext),
               let data = try? Data(contentsOf: url), !data.isEmpty {
                return data
            }
        }
        return nil
    }

    private func open(_ address: String) {
        guard let url = URL(string: address) else { return }
        UIApplication.shared.open(url)
    }

    private func advance() {
        guard !isLast else { return finish(heardItAll: true) }
        go(to: step + 1)
    }

    /// «Потом» — past the whole setup section, to whatever he says afterwards.
    /// Never straight out: he still has a last word, and being dropped back
    /// onto a screen mid-sentence reads as something having gone wrong.
    private func skipTheOptionalPart() {
        var next = step + 1
        while next < script.count, script[next].optional { next += 1 }
        guard next < script.count else { return finish(heardItAll: true) }
        go(to: next)
    }

    private func go(to next: Int) {
        withAnimation(.easeInOut(duration: 0.35)) { step = next }
        Task { await say() }
    }

    private func finish(heardItAll: Bool) {
        voice.stop()
        // A self-advancing step may have a sleep in flight. Bumping this makes
        // it a no-op when it wakes, so «Пропустить» can't be followed by the
        // script carrying on underneath a screen that has already gone.
        generation += 1
        onFinished(heardItAll)
    }

    /// Say the current step, then — unless it is waiting for something — carry
    /// straight on to the next one.
    private func say() async {
        // First, and before anything can suspend: cutting the previous line
        // off is what releases the previous call's continuation. Two live
        // `speak`s would strand one of them for good.
        voice.stop()
        player.stop()
        generation += 1
        let mine = generation

        // What is SAID may differ from what is shown — on the steps that
        // involve the friend's name, which is shown and never pronounced.
        let words = (here.spoken ?? here.line)()
        let began = Date()

        if !here.silent {
            // The conversation's own session may have just been torn down, or
            // never raised at all (this runs before the friend exists).
            // Playback is all this needs.
            let session = AVAudioSession.sharedInstance()
            try? session.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
            try? session.setActive(true, options: [])

            speaking = true
            // A REAL VOICE IF THERE IS ONE. A person doing a robot beats a
            // robot doing a robot by a mile, and the character is most of
            // what this screen is for. Missing recordings are not a failure —
            // the synthesiser simply takes the line, exactly as before — so
            // they can be added one at a time, in any order, whenever.
            if let recorded = recording(named: here.voiceover) {
                await player.play(data: recorded)
            } else {
                await voice.speak(words, as: .machine)
            }
            // The cut-off call resumes too, and gets here AFTER its
            // replacement has already started talking. Only the current one
            // may put the ring out.
            if mine == generation { speaking = false }
        }

        guard mine == generation, here.wants == .nothing else { return }

        // HOLD IT LONG ENOUGH TO BE READ, whatever happened to the sound.
        //
        // Speech usually takes longer than this, so usually nothing is added.
        // But if the voice never sounded — no Russian voice installed, a
        // simulator, an audio session that wouldn't come up — `speak` returns
        // in milliseconds, and without a floor the entire script would flick
        // past in a second and a half with nobody able to read a word of it.
        // Measured on what is READ, not on what is said — they differ on the
        // name steps, and the screen is the thing somebody is looking at.
        let floor = 2.0 + Double(here.line().count) / 16.0
        let left = floor - Date().timeIntervalSince(began)
        if left > 0 {
            try? await Task.sleep(nanoseconds: UInt64(left * 1_000_000_000))
        }
        // And a breath, so one sentence doesn't tread on the next.
        try? await Task.sleep(nanoseconds: 550_000_000)

        if mine == generation { advance() }
    }
}

// MARK: - How to call him

/// The robot, running the walkthrough that sends people into Settings — which
/// is exactly why it is a sheet they can leave and come back to, rather than
/// part of the arrival.
struct CallHimSheet: View {
    @EnvironmentObject private var app: AppState
    @Environment(\.dismiss) private var dismiss

    /// His real name once they've met, and the robot's own until then — the
    /// same placeholder the arrival screen used, so anybody redoing this
    /// before meeting him isn't quietly handed a different word.
    private var phrase: String {
        app.companionName.isEmpty ? "Боб" : app.companionName
    }

    var body: some View {
        // The vocal shortcut FIRST, because whoever opens this either skipped
        // it on the arrival screen («потом») or wants to redo it — and it is
        // the one worth having. The other three come after, for anybody who
        // would rather press something than speak.
        SetupRobot(script: Strings.robotHelloAgain
                         + Strings.robotVocalShortcut(phrase: phrase)
                         + Strings.robotSetUpCalling) { _ in dismiss() }
        .presentationDetents([.large])
        .presentationCornerRadius(Metrics.sheetRadius)
    }
}

/// The robot coming back after the first conversation to swap its own name
/// out for the friend's. Shorter than the full walkthrough — they have done
/// this once already, and being talked through it twice is how a helpful
/// thing turns into a tiresome one.
struct HisNameSheet: View {
    let name: String
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        SetupRobot(script: Strings.robotAboutHisName(name)
                         + Strings.robotVocalShortcut(phrase: name)) { _ in dismiss() }
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

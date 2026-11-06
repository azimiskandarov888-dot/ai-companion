// The way a person comes to him: the approved prototype (ios/design/journey.html) as the app itself (his choice,
// 2026-11-06: «the screens over the world — in SwiftUI»). Under everything, the living world (WorldView); over it:
//   0 black, two lines, in the phone's language or the one chosen here — a touch begins;
//   1 the world comes up out of the dark, the words go 0.8 s later, and we walk up the hill toward him. On the way the
//     third voice asks a few things, a tap each (docs/FIRST-MEETING.md §2), and the server writes him while we walk;
//   2 he notices us: a hop, «О, привет… как ты?», and «Поговори с ним» asks for the microphone — the real iOS alert;
//   3 the talk: the voice loop (ConversationController), his words as subtitles, his state in small capitals;
//   4 midway, a contact exchange (Sign in with Apple), and the talk goes on;
//   5 only when today's free minutes are over (a minute's notice first): the one calm screen to pay;
//   and a menu: subscription, restore, sign-in, language, help, who he is, the microphone, privacy, terms, delete.
// Coming back, the app opens straight to him.

import SwiftUI

// MARK: - the look: «Ghost» — a quiet serif straight on the world; buttons are words with a hairline

enum Ghost {
    static let ink = Color(red: 1, green: 0.98, blue: 0.95)
    static let soft = ink.opacity(0.8)
    static let faint = ink.opacity(0.56)
    static let line = ink.opacity(0.32)
    static let gold = Color(red: 0.945, green: 0.843, blue: 0.635)
    static let shade = Color(red: 0.047, green: 0.031, blue: 0.02)
}

extension View {
    /// Legible over the moving world, as the prototype's text-shadow.
    func overWorld(_ radius: CGFloat = 11) -> some View { shadow(color: .black.opacity(0.6), radius: radius, x: 0, y: 1) }
}

/// A word with a hairline under it. At least 44 points tall (Apple), its words scale with the text size.
struct WordButton: View {
    let title: String
    var primary = false
    var wide = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            // (the hairline as wide as the word — or as the button, if it is a wide one — never stretched across the row)
            Text(title)
                .font(.system(.title3, design: .serif))
                .foregroundStyle(primary ? Ghost.gold : Ghost.ink)
                .multilineTextAlignment(.center)
                .frame(minWidth: wide ? 220 : nil)
                .padding(.bottom, 7)
                .overlay(alignment: .bottom) { Rectangle().fill(primary ? Ghost.gold.opacity(0.6) : Ghost.line).frame(height: 1) }
                .frame(minHeight: 44)
                .contentShape(Rectangle())
                .overWorld()
        }
        .buttonStyle(.plain)
    }
}

// MARK: - the journey

struct JourneyFlow: View {
    @EnvironmentObject private var app: AppState
    @ObservedObject var conversation: ConversationController
    @StateObject private var world = World()
    @StateObject private var store = Purchases()
    @StateObject private var walk = Walk()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    @AppStorage("appLanguage") private var language = Language.russian.rawValue   // (re-draws every word when changed)
    @AppStorage("journey.heIs") private var heIs = true                             // whom the person met
    @AppStorage("journey.iAmHe") private var iAmHe = true                           // for his Russian
    @AppStorage("journey.keepAsked") private var keepAsked = false

    enum Stage { case begin, film, talk }
    enum Question { case me, age, who, old }
    enum Sheet: String, Identifiable { case keep, pay, menu; var id: String { rawValue } }
    struct Picks { var me: Bool?; var age: Int?; var who: String?; var old: String? }

    @State private var stage: Stage = .begin
    @State private var veil = 1.0                                     // the dark over the world
    @State private var lineOn = [false, false]
    @State private var hintOn = false
    @State private var starting = false
    @State private var question: Question?
    @State private var questionOn = false
    @State private var picks = Picks()
    @State private var skipOn = false
    @State private var said: String?
    @State private var saidFaint = false
    @State private var stateWord = ""
    @State private var talkOn = false
    @State private var talking = false
    @State private var micDenied = false
    @State private var note: String?
    @State private var noted = false
    @State private var replies = 0
    @State private var sheet: Sheet?
    @State private var timers: [DispatchWorkItem] = []

    var body: some View {
        GeometryReader { geo in
            ZStack {
                WorldView(world: world)
                    .scaleEffect(walk.scale, anchor: UnitPoint(x: 0.25, y: 0.71))
                    .offset(x: walk.x, y: walk.y)
                Color.black.opacity(veil).ignoresSafeArea().allowsHitTesting(false)
                if stage != .talk { words }
                switch stage {
                case .begin: beginControls
                case .film:  filmScreen
                case .talk:  talk(height: geo.size.height)
                }
            }
        }
        .id(language)                                                  // (a new language: every word anew)
        .sheet(item: $sheet, onDismiss: sheetClosed) { which in
            switch which {
            case .keep: KeepSheet(he: heIs) { sheet = nil }
            case .pay:  PaySheet(store: store, he: heIs, teen: app.isTeenager) { sheet = nil }
            case .menu: MenuSheet(store: store, he: heIs, signIn: { sheet = nil; after(0.6) { sheet = .keep } }) { sheet = nil }
            }
        }
        .onChange(of: sheet) { _, now in if now != nil { conversation.suspend() } }
        .onAppear(perform: start)
        .onChange(of: conversation.status) { _, s in hear(s) }
        .onChange(of: conversation.lastReply) { _, reply in heard(reply) }
        .onChange(of: conversation.secondsLeft) { _, left in minuteLeft(left) }
        .onChange(of: app.hasArrived) { _, arrived in if !arrived && stage == .talk { restart() } }   // (his data deleted)
        .onChange(of: scenePhase) { _, phase in
            if phase == .active, stage == .talk, talking, sheet == nil { conversation.resume() }
        }
        .preferredColorScheme(.dark)
    }

    // MARK: 0 · black, two lines; a touch begins

    private var words: some View {
        VStack(spacing: 2) {
            Text(Words.w1).opacity(lineOn[0] ? 1 : 0)
            Text(Words.w2).opacity(lineOn[1] ? 1 : 0)
        }
        .font(.system(.title2, design: .serif))                        // (two lines on the smallest phone, as designed)
        .foregroundStyle(Ghost.ink)
        .multilineTextAlignment(.center)
        .overWorld()
        .padding(.horizontal, 28)
        .accessibilityElement(children: .combine)
        .allowsHitTesting(false)
    }

    private var beginControls: some View {
        ZStack {
            Color.clear.contentShape(Rectangle()).onTapGesture(perform: film)
                .accessibilityLabel(Words.tap).accessibilityAddTraits(.isButton).accessibilityAction { film() }
            VStack(spacing: 18) {
                Spacer()
                Text(Words.tap).font(.footnote).foregroundStyle(Ghost.faint).allowsHitTesting(false)
                HStack(spacing: 22) {
                    ForEach([Language.russian, .english], id: \.self) { l in
                        Button(l == .russian ? "Русский" : "English") { language = l.rawValue }
                            .font(.footnote)
                            .foregroundStyle(language == l.rawValue ? Ghost.ink : Ghost.faint)
                            .frame(minWidth: 44, minHeight: 44)
                            .accessibilityAddTraits(language == l.rawValue ? .isSelected : [])
                    }
                }
            }
            .opacity(hintOn ? 1 : 0)
            .padding(.bottom, 20)
        }
    }

    #if DEBUG
    /// -journeyDemo: it walks itself through (a touch, the answers, him, the screen to pay, the menu), to look at on a
    /// simulator nobody is touching
    private let demo = ProcessInfo.processInfo.arguments.contains("-journeyDemo")
    #else
    private let demo = false
    #endif

    private func start() {
        if app.hasArrived && !demo { return comeBack() }
        if demo { after(5) { film() } }
        stage = .begin
        after(0.7) { withAnimation(.easeInOut(duration: 2.2)) { lineOn[0] = true } }
        after(2.2) { withAnimation(.easeInOut(duration: 2.2)) { lineOn[1] = true } }
        after(4.2) { withAnimation(.easeInOut(duration: 1.6)) { hintOn = true } }
    }

    /// Coming back: no film — a short fade, and he is there.
    private func comeBack() {
        stage = .talk
        lineOn = [false, false]
        whenWhole {
            withAnimation(.easeOut(duration: 1.2)) { veil = 0 }
            after(1.4) {
                world.set(way: "speak"); stateWord = Words.speaking
                say(Words.back(iAmHe), for: 3.8)
                after(4) { world.set(way: "listen"); stateWord = ""; listenIfAllowed() }
            }
        }
    }

    // MARK: 1 · the film, and the third voice's few questions on the way

    private func film() {
        guard stage == .begin, !starting else { return }
        starting = true
        withAnimation(.easeOut(duration: 1)) { hintOn = false }
        whenWhole {
            withAnimation(.easeInOut(duration: 3.2)) { veil = 0 }
            walk.begin(still: reduceMotion) { arrive() }
            after(0.8) { withAnimation(.easeInOut(duration: 1.8)) { lineOn[0] = false } }
            after(1.1) { withAnimation(.easeInOut(duration: 1.8)) { lineOn[1] = false } }
            after(3.4) { stage = .film; walk.asking = 1; ask(order.first) }
        }
    }

    private var order: [Question] {
        (Words.askGender ? [.me] : []) + [.age, .who] + ((picks.age ?? 30) < 18 ? [] : [.old])   // (a teenager meets someone of their own age)
    }

    private func ask(_ q: Question?) {
        question = q
        guard let q else { return asked() }
        withAnimation(.easeInOut(duration: 0.7)) { questionOn = true }
        if demo {
            after(1.8) {
                switch q {
                case .me:  picked(.me) { picks.me = true }
                case .age: picked(.age) { picks.age = 30 }
                case .who: picked(.who) { picks.who = "him" }
                case .old: picked(.old) { picks.old = "как я" }
                }
            }
        }
    }

    private func picked(_ q: Question, _ apply: () -> Void) {
        apply()
        withAnimation(.easeInOut(duration: 0.6)) { questionOn = false }
        let next = order.firstIndex(of: q).flatMap { $0 + 1 < order.count ? order[$0 + 1] : nil }
        after(0.9) { ask(next) }
    }

    private func asked() {
        walk.asking = 2
        iAmHe = picks.me != false
        heIs = picks.who == "her" ? false : picks.who == "him" ? true : Bool.random()   // («всё равно»: the dice, as the server's)
        withAnimation(.easeInOut(duration: 0.9)) { skipOn = true }
        if demo { after(1.5) { walk.finish() } }
        // the server writes him now, while we walk. (Until it takes these as fields — stage 3 on the server — they go as
        // the person's wishes, which the matchmaker reads)
        let age = String(picks.age ?? 30), country = Locale.current.region?.identifier ?? ""
        let wishes = [picks.who.map { "кого встретить: \($0 == "him" ? "его" : $0 == "her" ? "её" : "всё равно")" },
                      picks.old.map { "его возраст: \($0)" }, picks.me.map { "я: \($0 ? "он" : "она")" }].compactMap { $0 }.joined(separator: "; ")
        app.saveAge(age); app.saveCountry(country); app.saveWishes(wishes)
        Task {
            if let made = try? await BackendClient(baseURL: AppConfig.shared.backendURL)
                .createCompanion(story: "", wishes: wishes, country: country, age: age) {
                app.remember(companionName: made.name)
            }
            app.markArrived()
        }
    }

    private var filmScreen: some View {
        VStack(spacing: 20) {
            Spacer()
            if let q = question { questionView(q).opacity(questionOn ? 1 : 0).allowsHitTesting(questionOn) }
            Spacer()
            Button(Words.skip) { walk.finish() }
                .font(.footnote).foregroundStyle(Ghost.faint).frame(minWidth: 44, minHeight: 44)
                .opacity(skipOn ? 1 : 0).disabled(!skipOn)
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 8)
    }

    @ViewBuilder private func questionView(_ q: Question) -> some View {
        VStack(spacing: 18) {
            Text(line(q))
                .font(.system(.title, design: .serif)).foregroundStyle(Ghost.ink)
                .multilineTextAlignment(.center).overWorld()
                .accessibilityAddTraits(.isHeader)
            switch q {
            case .me:
                answers([(Words.aCame, { picks.me = true }), (Words.aCameF, { picks.me = false })], q)
            case .age:
                AgeRow { n in picked(.age) { picks.age = n } }
                Text(Words.qAgeHint).font(.footnote).foregroundStyle(Ghost.soft).overWorld()
            case .who:
                answers([(Words.aHim, { picks.who = "him" }), (Words.aHer, { picks.who = "her" }), (Words.aAny, { picks.who = "any" })], q)
                Text(Words.ai).font(.footnote).foregroundStyle(Ghost.soft).multilineTextAlignment(.center).overWorld()
            case .old:
                answers([(Words.aSame, { picks.old = "как я" }), (Words.aOlder, { picks.old = "постарше" }),
                         (Words.aYounger, { picks.old = "помладше" }), (Words.aNoMatter, { picks.old = "неважно" })], q)
            }
        }
    }

    private func line(_ q: Question) -> String {
        switch q { case .me: Words.qMe; case .age: Words.qAge; case .who: Words.qWho; case .old: Words.qOld }
    }

    /// In a row when they fit; one under another when the text is large.
    private func answers(_ items: [(String, () -> Void)], _ q: Question) -> some View {
        let buttons = ForEach(items.indices, id: \.self) { i in
            WordButton(title: items[i].0, wide: false) { picked(q, items[i].1) }
        }
        return ViewThatFits(in: .horizontal) {
            HStack(spacing: 22) { buttons }
            VStack(spacing: 10) { buttons }
        }
    }

    // MARK: 2–3 · him, and the talk

    private func arrive() {
        cancelTimers()
        walk.stop()
        stage = .talk
        withAnimation(.easeOut(duration: 0.8)) { veil = 0 }
        world.set(way: "rest", act: "jump")
        after(1.6) { world.set(way: "speak"); stateWord = Words.speaking; say(Words.hi, for: nil) }
        after(3.6) { world.set(way: "listen"); stateWord = ""; withAnimation(.easeInOut(duration: 0.9)) { talkOn = true } }
        after(14) { if !talking { world.set(way: "speak"); say(Words.hello, for: 2.2, faint: true); after(2.3) { world.set(way: "listen") } } }
        after(26) { if !talking { world.set(way: "speak"); say(Words.there, for: 2.2, faint: true); after(2.3) { world.set(way: "listen") } } }
        if demo { after(7) { sheet = .pay }; after(13) { sheet = nil }; after(14.5) { sheet = .menu } }
    }

    private func talk(height: CGFloat) -> some View {
        VStack(spacing: 14) {
            HStack {
                Text(stateWord.uppercased())
                    .font(.caption2.weight(.semibold)).tracking(3).foregroundStyle(Ghost.soft).overWorld()
                    .accessibilityHidden(stateWord.isEmpty)
                Spacer()
                Button { sheet = .menu } label: {
                    Image(systemName: "ellipsis").font(.body.weight(.semibold)).foregroundStyle(Ghost.ink)
                        .frame(width: 44, height: 44).background(.ultraThinMaterial, in: Circle())
                }
                .accessibilityLabel(Words.menu)
            }
            .padding(.horizontal, 20)
            Spacer().frame(height: height*0.16)
            if let said {
                Text(said)
                    .font(.system(saidFaint ? .body : .title3, design: .serif))
                    .foregroundStyle(saidFaint ? Ghost.soft : Ghost.ink)
                    .multilineTextAlignment(.center).overWorld(14)
                    .padding(.horizontal, 28).frame(maxWidth: 560)
                    .transition(.opacity)
                    .accessibilityAddTraits(.updatesFrequently)
            }
            if talkOn && !talking { WordButton(title: Words.talk(heIs), primary: true, action: startTalking).transition(.opacity) }
            if micDenied {
                VStack(spacing: 10) {
                    Text(Words.micDenied(heIs)).font(.subheadline).foregroundStyle(Ghost.soft).multilineTextAlignment(.center).overWorld()
                    WordButton(title: Words.openSettings) { if let u = URL(string: UIApplication.openSettingsURLString) { openURL(u) } }
                }
                .padding(.horizontal, 28)
            }
            if let note { Text(note).font(.footnote).foregroundStyle(Ghost.soft).overWorld().transition(.opacity) }
            if let alarm = conversation.emergency { helpNow(alarm) }
            Spacer()
        }
        .padding(.top, 8)
    }

    private func startTalking() {
        Task {
            if await AudioSessionManager.requestMicPermission() {
                withAnimation { talkOn = false; micDenied = false; talking = true; said = nil }
                conversation.turnOn()
            } else {
                withAnimation { micDenied = true }
            }
        }
    }

    /// Returning: listen at once if the microphone was allowed before; else the button asks.
    private func listenIfAllowed() {
        if AVAudioApplicationGranted.now { talking = true; conversation.turnOn() } else { withAnimation { talkOn = true } }
    }

    private func hear(_ status: ConversationController.Status) {
        guard stage == .talk else { return }
        switch status {
        case .listening: world.set(way: "listen"); stateWord = Words.listening
        case .thinking:  world.set(way: "think");  stateWord = Words.thinking
        case .speaking:  world.set(way: "speak");  stateWord = Words.speaking
        case .problem:   world.set(way: "cant");   stateWord = ""; say(Strings.cannotHear(), for: 4, faint: true)
        case .asleep:    world.set(way: "sleep");  stateWord = ""
        case .idle:      world.set(way: "rest");   stateWord = ""
        case .restedForToday:
            // today's free minutes are over: his warm words came from the server; a pause; the third voice's calm screen
            world.set(way: "rest"); stateWord = ""
            if !store.active { after(2.4) { sheet = .pay } }
        }
    }

    private func heard(_ reply: String) {
        guard stage == .talk, !reply.isEmpty else { return }
        say(reply, for: max(4, Double(reply.count)*0.065))
        replies += 1
        // midway through the first meeting, the contact exchange — never right before the money
        if replies == 4, app.account == nil, !keepAsked { keepAsked = true; after(1.5) { sheet = .keep } }
    }

    private func minuteLeft(_ left: Int?) {
        guard let left, left <= 60, !noted, !store.active else { return }
        noted = true
        withAnimation { note = Words.minute }
        after(6) { withAnimation { note = nil } }
    }

    private func sheetClosed() {
        if stage == .talk, talking { conversation.resume() }
    }

    private func say(_ text: String, for seconds: Double?, faint: Bool = false) {
        withAnimation(.easeInOut(duration: 0.7)) { said = text; saidFaint = faint }
        if let seconds { after(seconds) { if said == text { withAnimation(.easeInOut(duration: 0.7)) { said = nil } } } }
    }

    /// Help, now: this person's own emergency number first (the server raised it), dialled by them, never by us.
    private func helpNow(_ alarm: EmergencyAlarm) -> some View {
        VStack(spacing: 12) {
            Text(alarm.isAboutHimself ? Strings.helpNowSelf() : Strings.helpNowBody())
                .font(.body).foregroundStyle(Ghost.ink).multilineTextAlignment(.center)
            ForEach(alarm.dialable, id: \.self) { number in
                WordButton(title: Strings.helpNowCall(number)(), primary: true) {
                    let digits = number.filter(\.isNumber)
                    if !digits.isEmpty, let url = URL(string: "tel://\(digits)") { openURL(url) }
                }
            }
            WordButton(title: Strings.helpNowPutAway()) { withAnimation { conversation.dismissEmergency() } }
        }
        .padding(20)
        .background(Ghost.shade.opacity(0.82), in: RoundedRectangle(cornerRadius: 22))
        .padding(.horizontal, 20)
    }

    // MARK: helpers

    private func restart() {
        cancelTimers(); walk.stop()
        stage = .begin; veil = 1; lineOn = [false, false]; hintOn = false; starting = false
        question = nil; questionOn = false; picks = Picks(); skipOn = false
        said = nil; stateWord = ""; talkOn = false; talking = false; micDenied = false; replies = 0; keepAsked = false
        start()
    }

    /// The world is shown only once drawn whole (at most 8 s of waiting, then anyway).
    private func whenWhole(_ then: @escaping () -> Void) {
        Task { @MainActor in
            let t0 = Date()
            while !world.ready && Date().timeIntervalSince(t0) < 8 { try? await Task.sleep(nanoseconds: 150_000_000) }
            then()
        }
    }

    private func after(_ seconds: Double, _ then: @escaping () -> Void) {
        let item = DispatchWorkItem(block: then)
        timers.append(item)
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds, execute: item)
    }

    private func cancelTimers() { timers.forEach { $0.cancel() }; timers = [] }
}

import AVFAudio

/// Whether the microphone was already allowed (not asking).
enum AVAudioApplicationGranted {
    static var now: Bool { AVAudioApplication.shared.recordPermission == .granted }
}

// MARK: - the walk up the hill: the picture slowly closes in to where we stand, with the sway of steps that settles as
// we stop (the camera itself stays: the world keeps its light worked out for this one view). It walks slower while the
// third voice asks, and never arrives with a question open. Reduce Motion: no closing in, no sway — only the time

@MainActor
final class Walk: NSObject, ObservableObject {
    @Published private(set) var scale: CGFloat = 1
    @Published private(set) var x: CGFloat = 0
    @Published private(set) var y: CGFloat = 0
    var asking = 0                                                       // 0 not yet · 1 asking · 2 all answered
    private var link: CADisplayLink?
    private var went: Double = 0, last: CFTimeInterval = 0, still = false
    private var arrived: (() -> Void)?
    private static let T = 26.0

    func begin(still: Bool, arrived: @escaping () -> Void) {
        stop()
        self.still = still; self.arrived = arrived; went = 0; last = 0; asking = 0
        if !still { scale = 1.34; y = 26 }
        link = CADisplayLink(target: self, selector: #selector(tick(_:)))
        link?.add(to: .main, forMode: .common)
    }

    /// «Пропустить»: straight to him.
    func finish() { guard link != nil else { return }; stop(); let a = arrived; arrived = nil; a?() }

    func stop() {
        link?.invalidate(); link = nil
        scale = 1; x = 0; y = 0
    }

    @objc private func tick(_ l: CADisplayLink) {
        let now = l.timestamp, dt = last == 0 ? 0 : now - last
        last = now
        went += dt*(asking == 1 ? 0.5 : 1)
        if asking != 2 { went = min(went, 0.9*Self.T) }
        let k = min(1, went/Self.T), e = k < 0.5 ? 4*k*k*k : 1 - pow(-2*k + 2, 3)/2, sway = 1 - e
        if !still {
            scale = 1.34 - 0.34*e
            y = 3.2*sway*sin(now*2*Double.pi/0.95) + 26*sway
            x = 1.4*sway*sin(now*Double.pi/0.95)
        }
        if k >= 1 { finish() }
    }
}

// MARK: - the age, as a row of numbers to leaf through; the one in the middle is lit; a touch takes it.
// VoiceOver: swipe up or down to change it, double-tap to take it (WCAG 2.5.7: no dragging needed)

struct AgeRow: View {
    var from = 13, to = 95, first = 30
    let take: (Int) -> Void
    @State private var centred: Int?

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 0) {
                    ForEach(from...to, id: \.self) { n in
                        Button { withAnimation { proxy.scrollTo(n, anchor: .center) }; DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { take(n) } } label: {
                            Text("\(n)")
                                .font(.system(.largeTitle, design: .serif))
                                .foregroundStyle(centred == n ? Ghost.gold : Ghost.soft)
                                .scaleEffect(centred == n ? 1.18 : 1)
                                .frame(width: 64, height: 64)
                                .overWorld()
                        }
                        .buttonStyle(.plain)
                        .id(n)
                    }
                }
                .scrollTargetLayout()
            }
            .scrollTargetBehavior(.viewAligned)
            .scrollPosition(id: $centred, anchor: .center)
            .contentMargins(.horizontal, 128, for: .scrollContent)
            .onAppear { DispatchQueue.main.async { proxy.scrollTo(first, anchor: .center); centred = first } }   // (opens on 30)
            .accessibilityElement()
            .accessibilityLabel(Words.qAge)
            .accessibilityValue("\(centred ?? first)")
            .accessibilityAdjustableAction { direction in
                let n = centred ?? first, m = direction == .increment ? min(to, n + 1) : direction == .decrement ? max(from, n - 1) : n
                proxy.scrollTo(m, anchor: .center); centred = m
            }
            .accessibilityAction { take(centred ?? first) }
        }
        .frame(width: 320, height: 72)
        .mask(LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: .black, location: 0.3),
                                     .init(color: .black, location: 0.7), .init(color: .clear, location: 1)],
                             startPoint: .leading, endPoint: .trailing))
    }
}

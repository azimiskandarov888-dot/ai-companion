// 3 · Tell your story   and   4 · Who you'd like to meet
//
// The same object, in the same clearing, an hour apart. One screen type serves
// both, because that is exactly what they are: you didn't get up, you turned to
// a second page.
//
// The scroll hangs VERTICALLY — a roller above, a roller below, paper between —
// and writing behaves the way writing behaves everywhere else on a phone: type
// past the bottom line and the text slides up inside the paper. The paper never
// grows, never overruns its rollers, and never has to be fought with.
//
// The two things that must not go wrong:
//
//   1. THE KEYBOARD MUST NEVER COVER THE SCROLL. At rest the paper sits on the
//      optical centre (45.5 %). When the keyboard rises the whole object rises
//      with it and the paper shortens — the writing scrolls INSIDE the parchment
//      rather than sliding under the keys. If the scroll can't be seen, the
//      screen has failed.
//
//   2. THE ROLL-AWAY IS THE SIGNATURE MOMENT. The sheet winds up onto the top
//      roller, and the whole object lifts and drifts away — and the landscape
//      behind it never moves.
//
// Everything here is laid out in ONE vertical stack with definite heights.
// Nothing is placed by absolute coordinates, because that is how the caution on
// screen 4 ended up sitting on top of the paper.

import SwiftUI

struct ScrollScreen: View {

    enum Kind {
        case story      // 3
        case meet       // 4

        var place: Place { self == .story ? .story : .meet }
        var heading: String { self == .story ? Strings.storyHeading() : Strings.meetHeading() }
        var placeholder: String {
            self == .story ? Strings.storyPlaceholder() : Strings.meetPlaceholder()
        }
        var confirm: String { self == .story ? Strings.done() : Strings.meetHim() }
        /// Gold is spent on «Meet him» — the last step of onboarding. «Done» is
        /// the calm leaf green, so the two screens don't compete.
        var tone: ButtonTone { self == .story ? .leaf : .sun }
    }

    let kind: Kind
    @Binding var text: String
    /// Screens 3 and 4 are the same clearing an hour apart, so the flow draws
    /// ONE photograph behind both and passes `false` here. Nothing about the
    /// land may change when the second scroll is brought out.
    var drawsBackground: Bool = true
    var onConfirm: () -> Void

    @StateObject private var keyboard = KeyboardObserver()
    @FocusState private var writing: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// 0 at rest → 1 when the sheet has wound onto the top roller and gone.
    /// Screen 4 starts at 1 and unrolls, so it reads as a NEW SHEET being drawn
    /// out in the same place — not as a new screen.
    @State private var winding: CGFloat
    @State private var showNudge = false

    init(kind: Kind,
         text: Binding<String>,
         drawsBackground: Bool = true,
         onConfirm: @escaping () -> Void) {
        self.kind = kind
        self._text = text
        self.drawsBackground = drawsBackground
        self.onConfirm = onConfirm
        self._winding = State(initialValue: kind == .meet ? 1 : 0)
    }

    var body: some View {
        // Screen 3 is no longer a blank sheet. A blank box asking «расскажите
        // о себе» is a FORM, and a form is the one thing this app must not put
        // in front of a lonely person: nobody knows where to start, what does
        // get written is a résumé, and a composed paragraph is the single
        // register in which none of the signals the reading looks for survive.
        // So it asks instead — one small question at a time. Screen 4 keeps
        // the scroll: «кого бы вы хотели встретить» is a different question,
        // and one you're gently advised not to answer at length.
        if kind == .story {
            IntakeConversation(story: $text,
                               drawsBackground: drawsBackground,
                               onDone: onConfirm)
        } else {
            scrollBody
        }
    }

    private var scrollBody: some View {
        GeometryReader { geo in
            let h = geo.size.height
            let isWriting = keyboard.isShowing
            let paper = paperHeight(in: h, isWriting: isWriting)

            ZStack {
                if drawsBackground {
                    PhotoBackground(place: kind.place, treatment: .scrim)
                }

                // Tapping the world outside the paper puts the pen down. This
                // has to sit BEHIND the scroll — as a modifier on the whole
                // screen it swallowed the taps meant for the writing surface,
                // and nothing could be typed at all.
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture { writing = false }

                VStack(spacing: 0) {
                    // ── screen 4's words, above the paper and never on it.
                    // Both of these are things to read BEFORE writing, in the
                    // order you'd read them, and both step out of the way the
                    // moment the keyboard comes up — the paper needs that room,
                    // and nobody re-reads a caution while they're typing.
                    if kind == .meet, !isWriting {
                        VStack(alignment: .leading, spacing: 12) {
                            caution()
                                .arrive(.first)

                            Group {
                                Text(Strings.friendshipQuote())
                                    .font(AppType.quote)
                                    .lineSpacing(AppType.quoteLeading)
                                    .foregroundStyle(Theme.onLand)
                                    .multilineTextAlignment(.leading)
                                    .fixedSize(horizontal: false, vertical: true)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .legible()
                                    .arrive(.second)
                            }
                        }
                        .opacity(winding > 0.1 ? 0 : 1)
                        Spacer(minLength: 16)
                    }

                    // ── the scroll itself
                    scroll(isWriting: isWriting)
                        .frame(height: paper)
                        .offset(y: -winding * h * 0.28)
                        .opacity(1 - winding * 0.55)
                        // Screen 3 sets the scroll down as the screen arrives.
                        // Screen 4 unrolls instead, so it must not fade in.
                        .arrive(.object, rise: 22, enabled: kind == .story)

                    Spacer(minLength: 12)

                    confirmButton
                        .arrive(.footnote, enabled: kind == .story)
                }
                .padding(.horizontal, Metrics.sideMargin)
                .padding(.top, topInset(in: h, paper: paper, isWriting: isWriting))
                .padding(.bottom, isWriting
                         ? keyboard.height + 12
                         : (geo.safeAreaInsets.bottom > 0 ? 8 : 24))
            }
            .animation(.easeOut(duration: keyboard.duration), value: keyboard.height)
        }
        .ignoresSafeArea(.keyboard)      // we position against the keyboard ourselves
        .onAppear {
            guard kind == .meet else { return }
            // The same hand, drawing out the next sheet.
            withAnimation(.timingCurve(0.32, 0, 0.2, 1, duration: 0.85).delay(0.15)) {
                winding = 0
            }
        }
    }

    // MARK: - where the paper sits, and how tall it is
    //
    // Both are definite. The paper is exactly as tall as it is told to be, so it
    // can never overrun its rollers or collide with the words above it.

    private func paperHeight(in height: CGFloat, isWriting: Bool) -> CGFloat {
        let fraction: CGFloat
        switch (kind, isWriting) {
        case (.story, false): fraction = 0.42
        case (.story, true):  fraction = 0.34
        case (.meet,  false): fraction = 0.33
        case (.meet,  true):  fraction = 0.30
        }
        return height * fraction
    }

    /// Rest: the paper's centre lands on the optical centre, 45.5 %.
    /// Writing: it rises to just under the top of the screen.
    private func topInset(in height: CGFloat, paper: CGFloat, isWriting: Bool) -> CGFloat {
        if isWriting { return height * Metrics.scrollWritingTop }
        switch kind {
        case .story:
            return max(16, height * Metrics.opticalCentre - paper / 2)
        case .meet:
            // The caution sits above the paper, so the stack starts higher.
            return max(16, height * 0.11)
        }
    }

    // MARK: - the scroll

    private func scroll(isWriting: Bool) -> some View {
        ParchmentScroll(winding: winding) {
            VStack(alignment: .leading, spacing: 10) {
                Text(kind.heading)
                    .font(AppType.writtenHeading)
                    .foregroundStyle(Theme.ink)
                    .fixedSize(horizontal: false, vertical: true)

                if !isWriting, text.isEmpty, kind == .story {
                    Text(Strings.storyLine())
                        .appFont(AppType.caption)
                        .foregroundStyle(Theme.inkSoft.opacity(0.88))
                        .fixedSize(horizontal: false, vertical: true)
                }

                // The writing surface takes everything left over, and scrolls
                // its own contents. It is NOT inside a ScrollView — two nested
                // scrollers is what made the text vanish and stop accepting
                // more once it passed the bottom.
                writingSurface
                    .frame(maxHeight: .infinity)

                if kind == .meet, !isWriting {
                    // The chips live ON the paper — drawn in ink, not linen.
                    // They insert a phrase into their own writing; they are
                    // never a field, and never required.
                    HStack(spacing: 8) {
                        SoftChip(title: Strings.chipAge())    { insert(Strings.chipAgeText()) }
                        SoftChip(title: Strings.chipGender()) { insert(Strings.chipGenderText()) }
                        SoftChip(title: Strings.chipOrigin()) { insert(Strings.chipOriginText()) }
                    }
                }
            }
        }
        // Touching the paper anywhere picks the pen up — the margins count too,
        // not only the exact line you're writing on. Simultaneous, so the text
        // view still places its own cursor where you tapped.
        .contentShape(Rectangle())
        .simultaneousGesture(TapGesture().onEnded { writing = true })
    }

    private var writingSurface: some View {
        ZStack(alignment: .topLeading) {
            if text.isEmpty {
                Text(kind.placeholder)
                    .font(AppType.writtenBody)
                    .italic()
                    .foregroundStyle(Theme.inkSoft.opacity(0.88))
                    .allowsHitTesting(false)
                    .padding(.top, 8)
                    .padding(.leading, 5)    // sits on the text view's own inset
            }
            TextEditor(text: $text)
                .font(AppType.writtenBody)
                .lineSpacing(AppType.writtenLeading)
                .foregroundStyle(Theme.ink)
                .tint(Theme.leaf500)                 // the caret, in ink's world
                .scrollContentBackground(.hidden)
                .background(.clear)
                .focused($writing)
        }
    }

    private func insert(_ phrase: String) {
        if !text.isEmpty, !text.hasSuffix(" "), !text.hasSuffix("\n") { text += " " }
        text += phrase
        writing = true
    }

    // MARK: - the caution (screen 4 only)

    private func caution() -> some View {
        HStack(alignment: .top, spacing: 12) {
            Rectangle()
                .fill(Theme.sun400)
                .frame(width: 2)
            VStack(alignment: .leading, spacing: 8) {
                // One caution, said once. It used to be followed by a softer
                // restatement of itself, which was a third helping of the same
                // thought on a screen that already carries the quote.
                Text(Strings.caution())
                    .appFont(AppType.lede, leading: AppType.ledeLeading)
                    .foregroundStyle(Theme.sun300)
                    .fixedSize(horizontal: false, vertical: true)
                    .legible()
            }
        }
        .fixedSize(horizontal: false, vertical: true)
    }

    // MARK: - confirm

    private var confirmButton: some View {
        VStack(spacing: 8) {
            if showNudge {
                Text(Strings.storyNudge())
                    .appFont(AppType.caption)
                    .foregroundStyle(Theme.onLand)
                    .multilineTextAlignment(.center)
                    .transition(.opacity)
            }
            AppButton(title: kind.confirm, tone: kind.tone) { confirm() }
        }
    }

    private func confirm() {
        // Screen 3 genuinely needs something to build him from — so «Done» looks
        // quiet rather than disabled, and tapping it gives one gentle nudge.
        // Screen 4 may be left blank: that's a fine answer, arguably the best.
        if kind == .story, text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            withAnimation { showNudge = true }
            writing = true
            return
        }

        writing = false

        guard !reduceMotion else {          // Reduce Motion: a cross-fade, same duration
            withAnimation(.easeInOut(duration: 0.8)) { winding = 1 }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { onConfirm() }
            return
        }

        // The signature moment, ~0.8 s: the sheet winds up onto the top roller
        // and the whole object lifts away. The landscape never moves.
        withAnimation(.timingCurve(0.32, 0, 0.2, 1, duration: 0.8)) { winding = 1 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.78) { onConfirm() }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// 3 · «Пока его нет» — the conversation that replaced the blank page
//
// WHAT WAS WRONG. A sheet of parchment saying «Расскажите о себе» is a form.
// It freezes people — hardest of all the eighty-year-old this app is for —
// and what does get written comes out as a résumé: «Люблю рыбалку и тишину.»
// Nothing to read there. Ask the same person what's out of their window and
// they talk for five minutes, in their own voice, and every signal the
// reading looks for is right there in it.
//
// WHO IS ASKING. Nobody, and that is deliberate. The obvious build is a blank
// "interviewer companion", and it's a trap twice over: a personality-less
// interviewer IS an AI questionnaire with a voice, and a fake person is worse
// — you'd tell a stranger your life and then watch them be replaced by
// someone else. So there is no name, no "I", no character. Only questions,
// arriving one at a time, and one honest sentence at the start: HE ISN'T HERE
// YET, HE WILL BE MADE OUT OF WHAT YOU SAY. That's true, which is why it
// works — it turns the tedious part into the consequential part.
//
// ONE QUESTION ON THE SCREEN, AND NOTHING ELSE. No transcript above, no
// progress bar, no counter. Re-reading your own answers is not the point and
// a counter turns a conversation back into a form; a question you can't see
// past is what makes the next sentence come easily.
//
// It writes into the same `story` binding screen 3 always wrote into, so
// nothing else in the flow changes: what reaches the backend is what they
// actually said.
// ═══════════════════════════════════════════════════════════════════════════

private struct IntakeConversation: View {
    @Binding var story: String
    var drawsBackground: Bool = true
    var onDone: () -> Void

    @State private var preamble = ""
    @State private var reaction = ""
    @State private var question = ""
    @State private var answer = ""
    /// Tappable choices for this question. Empty = it wants writing.
    @State private var options: [String] = []
    /// The last, real question — it gets a taller box, because the size of the
    /// space you're given is itself an instruction about how much to say.
    @State private var deepAnswer = false
    @State private var turns: [IntakeTurn] = []
    /// False at birth: the first question is local and instant, so the screen
    /// must never open in the dimmed "waiting" state.
    @State private var asking = false
    @State private var finished = false
    /// Bumped on every new question so the arrival animation replays.
    @State private var questionID = 0

    @StateObject private var keyboard = KeyboardObserver()
    @FocusState private var writing: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var client: BackendClient { BackendClient(baseURL: AppConfig.shared.backendURL) }

    /// Enough to build on. Someone who said three real sentences has given the
    /// reading more than the old blank page ever did, so the way out is never
    /// locked — but it isn't offered on the very first question either, where
    /// it would read as permission to skip the whole thing.
    /// Not offered during the greeting. An exit put in front of someone who
    /// has said two words reads as permission to leave, and they take it;
    /// after the introductions it reads as courtesy, which is what it is.
    private var mayFinishEarly: Bool { turns.count >= 4 }

    var body: some View {
      GeometryReader { geo in
        let isWriting = keyboard.isShowing

        ZStack {
            if drawsBackground { PhotoBackground(place: .story, treatment: .scrim) }

            // Putting the pen down. This must sit BEHIND the content, not as a
            // modifier on the whole screen — as a modifier it competes with
            // the TextEditor's own gestures and the keyboard becomes
            // impossible to dismiss. Exactly the bug the scroll screen had.
            Color.clear
                .contentShape(Rectangle())
                .onTapGesture { writing = false }

            VStack(spacing: 0) {
                Spacer(minLength: 0)

                // The reaction to what they just said. One short line, above
                // the question, in a quieter voice — this is the entire
                // personality of a thing with no identity.
                if !reaction.isEmpty && !isWriting {
                    Text(reaction)
                        .appFont(AppType.body)
                        .foregroundStyle(Theme.onLand.opacity(0.75))
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .legible()
                        .padding(.horizontal, Metrics.sideMargin)
                        .padding(.bottom, 14)
                        .transition(.opacity)
                }

                if !preamble.isEmpty && turns.isEmpty && !isWriting {
                    Text(preamble)
                        .appFont(AppType.caption, leading: AppType.bodyLeading)
                        .foregroundStyle(Theme.onLand.opacity(0.85))
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .legible()
                        .padding(.horizontal, Metrics.sideMargin)
                        .padding(.bottom, 28)
                        .transition(.opacity)
                }

                // THE QUESTION. Large, because it is the only thing on screen
                // and because it will be read by someone whose eyes are tired.
                Text(question)
                    .appFont(AppType.title, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.onLand)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .legible()
                    .padding(.horizontal, Metrics.sideMargin)
                    .id(questionID)
                    .transition(.opacity)
                    .opacity(asking ? 0.35 : 1)

                if !options.isEmpty {
                    // TAP TO ANSWER. Nothing about «горы или море?» is worth a
                    // keyboard — and typing it would kill the tempo that makes
                    // the rapid-fire half enjoyable at all. No wrong answers,
                    // no effort, one finger.
                    VStack(spacing: 12) {
                        ForEach(options, id: \.self) { option in
                            AppButton(title: option, tone: .quiet) { choose(option) }
                        }
                    }
                    .padding(.horizontal, Metrics.sideMargin)
                    .padding(.top, 30)
                    .disabled(asking || finished)
                    .transition(.opacity)

                } else {
                    // Their answer, on a quiet panel — not the parchment
                    // scroll, whose two rollers are a whole ceremonial object;
                    // bringing one out per question would turn a light
                    // conversation into twelve formal documents.
                    TextEditor(text: $answer)
                        .scrollContentBackground(.hidden)
                        .background(.clear)
                        .appFont(AppType.body, leading: AppType.bodyLeading)
                        .foregroundStyle(Theme.linen)
                        .focused($writing)
                        .frame(height: answerHeight(isWriting: isWriting))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .panel()
                        .padding(.horizontal, Metrics.sideMargin)
                        .padding(.top, 26)
                        .disabled(asking || finished)
                        .opacity(asking ? 0.5 : 1)

                    AppButton(title: Strings.language == .russian ? "Дальше" : "Next",
                              tone: .leaf) { send() }
                        .disabled(asking || answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .opacity(answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.45 : 1)
                        .padding(.horizontal, Metrics.sideMargin)
                        .padding(.top, 20)
                }

                // Never trapped, never rushed. Both ways out sit quietly below
                // the real action rather than competing with it.
                HStack(spacing: 22) {
                    // Nothing to skip on a two-button question — the whole
                    // point is that answering costs nothing.
                    if options.isEmpty && !asking {
                        quietly(Strings.language == .russian ? "пропустить" : "skip") {
                            answer = ""
                            send(skipping: true)
                        }
                    }
                    if mayFinishEarly && !asking {
                        quietly(Strings.language == .russian ? "хватит, дальше" : "that's enough") {
                            finish()
                        }
                    }
                }
                .padding(.top, 16)

                Spacer(minLength: 0)
            }
            // We position against the keyboard OURSELVES (see .ignoresSafeArea
            // below). Setting this padding while SwiftUI was also shifting the
            // view for the keyboard moved everything twice, which is how the
            // question ended up above the top of the screen — answering a
            // question you cannot see.
            .padding(.bottom, isWriting ? keyboard.height + 10
                                        : (geo.safeAreaInsets.bottom > 0 ? 12 : 30))
            .animation(reduceMotion ? nil : .easeInOut(duration: 0.45), value: questionID)
            .animation(.easeOut(duration: keyboard.duration), value: keyboard.height)
        }
      }
      .ignoresSafeArea(.keyboard)
      .statusBarHidden(true)
      .task { await ask() }
    }

    private func quietly(_ title: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .appFont(AppType.caption)
                .foregroundStyle(Theme.onLand.opacity(0.7))
                .legible()
        }
    }

    // MARK: - the conversation

    /// A short answer gets a small box, the last real question gets a tall
    /// one. The size of the space you're handed is itself an instruction
    /// about how much is wanted — a one-line field asks for one line.
    private func answerHeight(isWriting: Bool) -> CGFloat {
        if deepAnswer { return isWriting ? 150 : 210 }
        return isWriting ? 96 : 120
    }

    /// The warm line to show above the next question, given what they just
    /// answered. Silence is the common case: a remark on every single answer
    /// is exhausting, and is exactly what gives a machine away.
    private func reactionAfterLastAnswer() -> String {
        guard let last = turns.last, turns.count - 1 < Self.warmUp.count else { return "" }
        let step = Self.warmUp[turns.count - 1]
        if !step.reaction.isEmpty { return step.reaction }
        if let keyed = step.reactions[last.a] { return keyed }
        // The name is the one answer that always deserves an answer.
        if turns.count == 1, !last.a.isEmpty {
            return Strings.language == .russian
                ? "Очень приятно, \(last.a)."
                : "Good to know, \(last.a)."
        }
        return ""
    }

    private func choose(_ option: String) {
        turns.append(IntakeTurn(q: question, a: option))
        options = []
        rebuildStory()
        Task { await ask() }
    }

    private func send(skipping: Bool = false) {
        writing = false
        let said = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        turns.append(IntakeTurn(q: question, a: skipping ? "" : said))
        answer = ""
        rebuildStory()
        Task { await ask() }
    }

    // ── The warm-up, held locally ───────────────────────────────────────────
    //
    // THE LADDER. Aron's fast-friends work found what actually opens strangers
    // up: ESCALATING self-disclosure. Light first, deeper as you warm. Ask the
    // deep question cold and people close; ask it warm and they answer it.
    //
    // BUT LIGHT MEANS LOW-INTIMACY, NOT LOW-EFFORT — and getting that wrong is
    // how the previous version went «Как вас зовут?» → «Горы или море?», which
    // is meeting someone and immediately firing a quiz at them. Aron's opening
    // questions are still real questions; they are simply not intimate ones. A
    // quiz is not gentle conversation, it is not conversation at all.
    //
    // So the shape is now: a normal greeting → ordinary getting-to-know-you
    // talk → and only THEN, once someone is actually talking, the quick tapped
    // ones arrive as an ASIDE («кстати, а что вам ближе…»), worded the way a
    // person asks rather than the way a form does. They're a change of pace in
    // the middle of a conversation, not the opening act.
    //
    // All of it lives HERE, in the app, because it must feel instant and none
    // of it depends on the person, so there is nothing to generate. By the
    // time the network is needed, they're already talking.
    //
    // The reactions are the whole personality. No name, no "I", nothing about
    // itself — just someone taking an interest. Not every answer gets one:
    // constant reacting is exhausting and is what gives a bot away.

    private struct Step {
        let say: String
        /// Empty = typed answer. Otherwise the tappable choices.
        var options: [String] = []
        /// Warm one-liner shown before the NEXT question, keyed by their answer.
        var reactions: [String: String] = [:]
        /// Shown before the next question regardless of what they answered.
        var reaction: String = ""
    }

    private static let warmUp: [Step] = Strings.language == .russian ? [
        // 1 · Знакомство. Ordinary, unhurried, the way anyone would begin.
        Step(say: "Как вас зовут?"),
        Step(say: "Как ваш день сегодня?"),
        Step(say: "А чем обычно занимаетесь? Работа, дом, что-то своё —\nкак проходят дни?"),
        Step(say: "Сколько вам лет, если не секрет?",
             reaction: "Спасибо."),

        // 2 · Только теперь — лёгкие, и как бы между делом. Разговор уже идёт,
        // так что смена темпа читается как оживление, а не как анкета.
        Step(say: "Кстати, а что вам ближе по духу — горы или море?",
             options: ["Горы", "Море"],
             reactions: ["Горы": "Простор, значит.", "Море": "К воде тянет."]),
        Step(say: "А просыпаться пораньше или сидеть допоздна?",
             options: ["Утро моё", "Скорее вечер"],
             reactions: ["Скорее вечер": "Тихое время, понимаю."]),
        Step(say: "И что чаще пьёте?",
             options: ["Чай", "Кофе", "Просто воду"],
             reaction: "Хорошо. Теперь чуть серьёзнее."),
    ] : [
        Step(say: "What's your name?"),
        Step(say: "How's your day been?"),
        Step(say: "What do you usually get up to? Work, home,\nsomething of your own — how do the days go?"),
        Step(say: "How old are you, if you don't mind?",
             reaction: "Thank you."),

        Step(say: "By the way — are you more of a mountains or a sea person?",
             options: ["Mountains", "The sea"],
             reactions: ["Mountains": "Room to breathe.", "The sea": "Drawn to water."]),
        Step(say: "And do you wake early, or sit up late?",
             options: ["Early riser", "More of an evening"],
             reactions: ["More of an evening": "The quiet hours."]),
        Step(say: "And what do you usually drink?",
             options: ["Tea", "Coffee", "Just water"],
             reaction: "Good. Something a bit more serious now."),
    ]

    private static let firstPreamble = Strings.language == .russian
        ? "Его ещё нет — он появится из того, что вы расскажете.\n"
          + "Сначала несколько быстрых, потом пара настоящих. "
          + "Закончить можно в любой момент."
        : "He isn't here yet — he'll be made out of what you say.\n"
          + "A few quick ones first, then a couple of real ones. "
          + "You can stop whenever."

    /// The warm-up step this answer belongs to, or nil once it's finished.
    private var warmUpStep: Step? {
        turns.count < Self.warmUp.count ? Self.warmUp[turns.count] : nil
    }

    private func ask() async {
        // The warm-up needs no network at all, so it runs at the speed of a
        // finger. This is the part that has to feel like play.
        if let step = warmUpStep {
            if turns.isEmpty { preamble = Self.firstPreamble }
            reaction = reactionAfterLastAnswer()
            question = step.say
            options = step.options
            deepAnswer = false
            questionID += 1
            asking = false
            return
        }

        asking = true
        defer { asking = false }
        do {
            let next = try await client.intakeNext(conversation: turns)
            if next.enough || next.say.isEmpty {
                finish()
                return
            }
            reaction = next.reaction ?? ""
            question = next.say
            options = []
            deepAnswer = (next.kind == "open")
            questionID += 1
        } catch {
            // A broken question must never strand someone mid-sentence about
            // their own life. Whatever they've already said is enough to build
            // on, so the conversation ends rather than showing an error.
            Trouble.shared.record(error, url: AppConfig.shared.backendURL)
            finish()
        }
    }

    private func finish() {
        guard !finished else { return }
        finished = true
        rebuildStory()
        onDone()
    }

    /// Their words, in the shape the reading expects: the question as quiet
    /// context, the answer as the thing that counts. Skipped questions vanish
    /// entirely — an unanswered question is not a fact about anyone.
    private func rebuildStory() {
        story = turns
            .filter { !$0.a.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            .map { "— \($0.q)\n\($0.a)" }
            .joined(separator: "\n\n")
    }
}

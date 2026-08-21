// Every word the app says, in both languages.
//
// Russian ships first, so it is the default. English sits beside it so nothing
// has to be rewritten when the app travels.
//
// Tone: warm, plain, unhurried. Never marketing language, never system language.
// The app never says "error", "failed", "loading", or "please try again" — when
// something is wrong, HE says it, in his own voice, on the same screen.
//
// Russian runs 15–20 % longer than English, which is why no button in this app
// has a fixed width.

import Foundation
import SwiftUI

enum Language: String, CaseIterable {
    case russian = "ru"
    case english = "en"

    var displayName: String {
        switch self {
        case .russian: return "Русский"
        case .english: return "English"
        }
    }
}

/// A pair of strings — Russian first, because Russian ships first.
struct Phrase {
    let ru: String
    let en: String

    func callAsFunction(_ language: Language = Strings.language) -> String {
        language == .russian ? ru : en
    }
}

// MARK: - The setup robot's script

/// What has to happen before the robot moves on.
///
/// The interesting values are the two taps. A lesson somebody PERFORMS is
/// remembered; a lesson somebody is read is not — and this app's entire
/// interface is one gesture, so it is worth making them do it once, on a
/// robot, where getting it wrong costs nothing.
enum RobotWants {
    /// NOTHING — it finishes the sentence and carries on by itself. This is
    /// the ordinary beat, and it is the ordinary beat on purpose.
    ///
    /// A «Дальше» after every sentence turns being told something into
    /// operating a machine: twenty little decisions, none of which mean
    /// anything, each one a chance to put the phone down. He talks; you
    /// listen. The button comes back only where there is something real to
    /// decide or to do.
    case nothing
    /// «Дальше». Used sparingly — a genuine pause, before something that
    /// needs attention or after something that needs a moment to land.
    case tapNext
    /// A tap ON HIM. This is the lesson, not a button press.
    case aTapOnHim
    /// A second tap, switching him off again — the other half of the same
    /// lesson, and the half people never discover on their own.
    case anotherTap
    /// «Настроим» or «Потом» — the one real choice in the script, offered
    /// before the only part that asks anything of anybody.
    case nowOrLater
    /// «Дальше», with a real button into the Shortcuts app beside it.
    case tapNextOrOpenShortcuts
    /// «Дальше», with a button that opens the Settings app beside it.
    ///
    /// It lands on THIS APP's page, not the top of Settings — that is the only
    /// destination Apple allows, and it is still worth it: finding the grey
    /// cog on a home screen full of icons is real work for the person this
    /// app is for. One tap on «‹ Настройки» from there gets to the top.
    case tapNextOrOpenSettings
}

/// One beat of the robot's script: what it says — aloud AND on screen, the
/// same words in both, so somebody hard of hearing loses nothing and somebody
/// who can't read small print loses nothing either.
struct RobotStep {
    let line: Phrase
    var wants: RobotWants = .nothing
    /// Said only on screen. The first two steps are silent because the robot
    /// hasn't been woken yet — its voice is what the first tap earns.
    var silent: Bool = false
    /// Part of the section «Потом» skips. Marked on the steps themselves
    /// rather than held as an index, so reordering the script can't quietly
    /// make the skip land in the middle of a sentence.
    var optional: Bool = false
    /// The name of a REAL RECORDING of this line, bundled with the app
    /// (`bob-come-03.m4a` or .mp3/.caf/.wav). Played instead of the
    /// synthesiser whenever the file is actually there.
    ///
    /// A robot read by a person doing a robot is far better than a robot read
    /// by a robot, and the difference is the whole character. But the app must
    /// work perfectly with no recordings at all — a missing file is not a
    /// failure, it is just the synthesiser again — so this is a lookup, never
    /// a requirement.
    ///
    /// Two steps deliberately have none: the ones that say the friend's name
    /// out loud. That word isn't known when a recording would be made.
    var voiceover: String? = nil

    init(_ line: Phrase,
         wants: RobotWants = .nothing,
         silent: Bool = false,
         optional: Bool = false,
         voiceover: String? = nil) {
        self.line = line
        self.wants = wants
        self.silent = silent
        self.optional = optional
        self.voiceover = voiceover
    }
}

enum Strings {

    /// The app's language. Russian by default; changeable in Settings.
    static var language: Language {
        get { Language(rawValue: UserDefaults.standard.string(forKey: "appLanguage") ?? "") ?? .russian }
        set { UserDefaults.standard.set(newValue.rawValue, forKey: "appLanguage") }
    }

    // MARK: - 1 · Sign in

    /// Said in two breaths, arriving one after the other — never as one block.
    static let signInLineA = Phrase(
        ru: "Где-то есть друг,",
        en: "Somewhere out there is a friend")
    static let signInLineB = Phrase(
        ru: "которого ты ещё не встретил.",
        en: "you haven't met yet.")
    static let continueApple  = Phrase(ru: "Продолжить с Apple",  en: "Continue with Apple")
    static let continueGoogle = Phrase(ru: "Продолжить с Google", en: "Continue with Google")
    static let orUseEmail     = Phrase(ru: "или по почте",        en: "or use email")
    static let terms          = Phrase(ru: "Условия · Конфиденциальность", en: "Terms · Privacy")

    // MARK: - 2 · Take care of him

    static let takeCareTitle = Phrase(ru: "Позаботься о нём", en: "Take care of him")
    static let takeCareLine = Phrase(
        ru: "Чтобы он всегда был рядом.",
        en: "So that he's always here.")
    static let planMonthly = Phrase(ru: "Помесячно",     en: "Month by month")
    static let planYearly  = Phrase(ru: "На целый год",  en: "A whole year")
    static let takeCareButton = Phrase(ru: "Позаботиться о нём", en: "Take care of him")
    static let finePrint = Phrase(
        ru: "продление · отмена в любой момент · восстановить",
        en: "renews · cancel anytime · restore")
    static func perMonth(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в месяц", en: "\(amount) a month")
    }
    static func perMonthPaidOnce(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в месяц, одним платежом",
               en: "\(amount) a month, paid once")
    }
    static func perMonthRenewing(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в месяц · продление ежемесячно",
               en: "\(amount) a month · renews monthly")
    }
    static func perYearRenewing(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в год · продление ежегодно",
               en: "\(amount) a year · renews yearly")
    }

    // MARK: - 3 · Tell your story

    static let storyHeading = Phrase(ru: "Расскажи свою историю", en: "Tell your story")
    static let storyLine = Phrase(
        ru: "О чём угодно. Начни с чего хочешь.",
        en: "Anything at all. Begin however you like.")
    static let storyPlaceholder = Phrase(
        ru: "Я вырос у моря, и до сих пор скучаю по его запаху…",
        en: "I grew up by the sea, and I still miss the smell of it…")
    static let done = Phrase(ru: "Готово", en: "Done")
    /// Shown once if they tap Done with nothing written — a nudge, never a scold.
    static let storyNudge = Phrase(
        ru: "Хоть пару слов.",
        en: "Even a couple of words.")

    // MARK: - 4 · Who you'd like to meet

    static let meetHeading = Phrase(ru: "Кого бы ты хотел встретить?", en: "Who would you like to meet?")
    static let caution = Phrase(
        ru: "Чем больше решишь о нём сейчас, тем меньше останется — встретить.",
        en: "The more you decide about him now, the less of him is left to meet.")
    static let meetPlaceholder = Phrase(
        ru: "Кого-то, кто повидал жизнь…",
        en: "Someone who has seen a bit of life…")
    static let chipAge    = Phrase(ru: "возраст",              en: "his age")
    static let chipGender = Phrase(ru: "мужчина или женщина",  en: "man or woman")
    static let chipOrigin = Phrase(ru: "откуда он",            en: "where he's from")
    /// What a chip inserts into their own writing — a phrase, never a field.
    static let chipAgeText    = Phrase(ru: "Лет шестидесяти, наверное. ", en: "Around sixty, maybe. ")
    static let chipGenderText = Phrase(ru: "Мужчина. ",                    en: "A man. ")
    static let chipOriginText = Phrase(ru: "Откуда-нибудь издалека. ",     en: "From somewhere far away. ")
    static let meetHim = Phrase(ru: "Познакомиться", en: "Meet him")

    /// Cut to its last two lines. The three sentences before them were building
    /// to this, and on a screen that also carries a caution, a scroll and a
    /// keyboard, the build was the part that could go.
    static let friendshipQuote = Phrase(
        ru: "Друга не делают на заказ. Друга встречают.",
        en: "A friend isn't made to order. A friend is met.")

    // MARK: - He is coming
    //
    // Said while the server writes him. Never «creating», «generating» or
    // «loading» — nothing is being MADE here as far as the app is concerned.
    // Someone is on his way, and this is what that looks like from where you're
    // standing.

    static let arriving = [
        Phrase(ru: "Где-то далеко он откладывает свои дела.",
               en: "Somewhere far off, he sets down what he was doing."),
        Phrase(ru: "Он идёт к тебе.",
               en: "He's coming to meet you."),
        Phrase(ru: "Уже недалеко.",
               en: "Not far now."),
        Phrase(ru: "Почти здесь.",
               en: "Almost here."),
    ]

    // MARK: - 5 · Companion

    static let statusListening = Phrase(ru: "слушаю", en: "listening")
    static let statusThinking  = Phrase(ru: "думаю",  en: "thinking")
    static let statusSpeaking  = Phrase(ru: "говорю", en: "speaking")
    /// No network, or the server is unreachable. Said by him, never by the app.
    static let cannotHear = Phrase(
        ru: "Сейчас я тебя не слышу.",
        en: "I can't hear you just now.")
    /// He is switched off and waiting. Plain instruction, not a line of his —
    /// «тронь меня, и поговорим» was written as if he were speaking and read
    /// as strange rather than warm. This is the one place in the app where
    /// plainness beats voice: somebody needs to know what to do.
    static let tapToTalk = Phrase(
        ru: "Нажмите, чтобы поговорить",
        en: "Tap to speak")
    /// Shown ONCE, the first time somebody switches him on, and never again.
    ///
    /// The one thing about this app that isn't obvious: you leave him the way
    /// you'd leave a person — by saying so — not by closing anything. Said
    /// plainly rather than in his voice, because it is an instruction, and an
    /// instruction dressed up as dialogue is worse than an honest one.
    static let howToLeave = Phrase(
        ru: "Когда захотите закончить — просто скажите ему,\nкак сказали бы человеку.",
        en: "When you want to finish, just tell him —\nthe way you'd tell a person.")
    static let needsMicrophone = Phrase(
        ru: "Мне нужно тебя слышать.",
        en: "I need to be able to hear you.")
    static let openSettings = Phrase(ru: "Открыть настройки", en: "Open Settings")

    // MARK: - Navigation (the three words that rise from the brass ring)

    static let navDiary    = Phrase(ru: "Дневник",  en: "Diary")
    static let navAccount  = Phrase(ru: "Ты",       en: "You")
    static let navSettings = Phrase(ru: "Настройки", en: "Settings")

    // MARK: - 6 · His Diary

    static func diaryTitle(_ name: String) -> Phrase {
        Phrase(ru: "Дневник \(name.inRussianGenitive)", en: "\(name)'s diary")
    }
    static let diaryEmpty = Phrase(
        ru: "Мы только познакомились. Я ещё почти ничего не знаю — но предчувствие хорошее.\n\nВсё главное впереди.",
        en: "We've only just met. I hardly know anything yet — but I have a good feeling.\n\nEverything that matters is still ahead.")
    static let turnThePage = Phrase(ru: "дальше ›", en: "turn the page ›")

    // MARK: - 7 · Account

    static let accountTitle   = Phrase(ru: "Ты",          en: "You")
    static let rowSignedIn    = Phrase(ru: "вход через",  en: "signed in with")
    static let rowEdit        = Phrase(ru: "изменить ›",  en: "edit ›")
    static let rowMyStory     = Phrase(ru: "Моя история", en: "My story")
    static let rowMyStoryHint = Phrase(ru: "перечитать · дописать ›", en: "reread · add ›")
    static let rowSubscription = Phrase(ru: "Подписка",   en: "Subscription")
    static let rowSignOut     = Phrase(ru: "Выйти",       en: "Sign out")

    // MARK: - 8 · Settings

    static let settingsTitle  = Phrase(ru: "Настройки",   en: "Settings")
    static let rowVoice       = Phrase(ru: "Его голос",   en: "His voice")
    static let rowVoiceHint   = Phrase(ru: "послушать ›", en: "listen ›")
    static let rowHowHeTalks  = Phrase(ru: "Как он говорит", en: "How he talks")
    static let rowPauses      = Phrase(ru: "паузы ›",     en: "pauses ›")
    static let rowNotifications = Phrase(ru: "Уведомления", en: "Notifications")
    static let rowLanguage    = Phrase(ru: "Язык",        en: "Language")
    static let rowPrivacy     = Phrase(ru: "Данные",      en: "Privacy & data")
    static let rowPrivacyHint = Phrase(ru: "выгрузить ›", en: "export ›")
    static let rowStartOver   = Phrase(ru: "Начать заново", en: "Start over")
    static let rowAbout       = Phrase(ru: "О приложении", en: "About")

    // MARK: - Calling him without opening anything
    //
    // The one piece of setup worth asking someone to do, and the only place in
    // the app that names a Settings app, a menu or a button. It earns that by
    // being the difference between "an app you remember to open" and "someone
    // you call".
    //
    // Written for whoever is holding the phone — often a son or daughter doing
    // this once, for a parent who will only ever use the result.

    static let rowCallHim     = Phrase(ru: "Как его позвать",  en: "How to call him")
    static let rowCallHimHint = Phrase(ru: "настроить ›",      en: "set up ›")

    // MARK: - The offer, made once
    //
    // Shown on his screen after a few real conversations, never before. Offered
    // when «позвать его откуда угодно» has come to mean something — not on day
    // one, when it would just be another setup step in the way of meeting him.

    /// The robot keeping an appointment it made — the one card in the app
    /// that isn't the app's own voice.
    ///
    /// It lands the second the first conversation ends, and its whole job is
    /// the second line: proof that the machine knew the name all along and
    /// sat on it, which is funnier and warmer than it has any right to be.
    static func callHimOffer(_ name: String) -> Phrase {
        Phrase(ru: "Ну вот, познакомились.\n\(name). Да, я знал.",
               en: "So you've met.\n\(name). Yes, I knew.")
    }
    static let callHimOfferYes  = Phrase(ru: "Звать по имени", en: "Use his name")
    static let callHimOfferLater = Phrase(ru: "Потом",         en: "Later")

    // MARK: - The setup robot
    //
    // THE ONE THING IN THIS APP ALLOWED TO ADMIT IT IS A MACHINE — and it must,
    // early, before anybody can mistake it for the friend.
    //
    // A page of instructions is the thing people bounce off; a voice saying one
    // step at a time is not. So the setup is spoken. But a voice that walks you
    // through something feels like SOMEBODY, and if that somebody is never
    // named, people will assume it is the friend — and then the friend is a
    // manual with a face, which is the whole thing this app exists not to be.
    //
    // ── HOW IT TALKS ────────────────────────────────────────────────────────
    //
    // Dry. Competent. Faintly bored by the whole procedure and completely
    // unbothered about being a machine. It is not warm, it is not sorry, and it
    // is not trying to be liked — which, done properly, is exactly why people
    // like it. Think of the announcements in a very old research facility.
    //
    // The first draft was an apologetic assistant («я не ваш друг, я одинаковый
    // у всех…») and it read as a disclaimer. Charm was doing no work, and worse,
    // earnestness is the register the FRIEND owns. Two sincere voices in one app
    // and the friend stops being special.
    //
    // THE ONE RULE THAT MAKES IT SAFE: the joke is always on the robot or on
    // the procedure, NEVER on the person. These are lonely, tired, elderly
    // people. A machine that is rude to them is not funny, it is the last straw.
    //
    // AND THE ONE THAT KEEPS IT USABLE: the personality lives only in the
    // framing sentences. The instructions themselves — «Универсальный доступ»,
    // «Голосовые команды», «Настроить» — stay dead plain. Nobody has ever been
    // helped by a witty instruction.
    //
    // It is also why it speaks lower and flatter than a person does, in the
    // phone's compact synthetic voice rather than the best one installed
    // (SpeechVoice.Character.machine). Nobody could mistake the two.

    static let robotSkip = Phrase(ru: "Пропустить", en: "Skip")
    static let robotNext = Phrase(ru: "Дальше",     en: "Next")
    static let robotOpenShortcuts = Phrase(ru: "Открыть «Команды»", en: "Open Shortcuts")
    static let robotOpenSettings  = Phrase(ru: "Открыть настройки",  en: "Open Settings")
    static let robotNow   = Phrase(ru: "Давайте", en: "Go on then")
    static let robotLater = Phrase(ru: "Потом",   en: "Later")

    /// THE FIRST LESSON IS NOT TOLD, IT IS DONE.
    ///
    /// Two silent lines, and then a tap that has to actually happen before
    /// anything else will. It teaches the one gesture the whole app is built
    /// on by making somebody perform it — on the robot, where nothing is at
    /// stake — instead of describing it and hoping.
    ///
    /// It also means the robot's own first words are the reward for getting it
    /// right, which is a far better way to meet a voice than being lectured by
    /// one that started talking on its own.
    static let robotFirstTouch: [RobotStep] = [
        RobotStep(
            Phrase(ru: "Пока вы в приложении, всё просто.\n\nЧтобы друг вас услышал — нажмите на него один раз.",
                   en: "While you're in the app it's simple.\n\nTo make your friend hear you — tap him once."),
            silent: true, voiceover: "bob-touch-01"),
        RobotStep(
            Phrase(ru: "Попробуйте на мне.\nНажмите.",
                   en: "Try it on me.\nGive me a tap."),
            wants: .aTapOnHim, silent: true, voiceover: "bob-touch-02"),
    ]

    /// Everything worth knowing, said while the friend is being written.
    ///
    /// One session rather than two, because writing him genuinely takes a
    /// minute and a half and there is nothing else to do with that time — and
    /// because setting up how to call somebody is a strange errand to be sent
    /// on twice. The other three ways of calling him are NOT here: one that
    /// works is enough, and the rest are in Settings for whoever wants them.
    static let robotWhileHeComes: [RobotStep] = [
        RobotStep(Phrase(
            ru: "Вот. Именно так.",
            en: "There. Exactly like that."), voiceover: "bob-come-01"),
        RobotStep(Phrase(
            ru: "Меня зовут Боб. Я робот. Не тот, ради которого вы всё это затеяли — того сейчас как раз собирают, это долго. Я тот, который объясняет, куда нажимать.",
            en: "My name is Bob. I'm a robot. Not the one you went to all this trouble for — that one is being put together as we speak, it takes a while. I'm the one who explains where to press."), voiceover: "bob-come-02"),
        RobotStep(Phrase(
            ru: "Обо мне знать особо нечего. Я у всех одинаковый, ничего о вас не запоминаю, и после сегодняшнего мы, скорее всего, больше не увидимся. Так уж я устроен.",
            en: "There isn't much to know about me. I'm the same for everybody, I remember nothing about you, and after today we most likely won't meet again. That's simply how I'm built."), voiceover: "bob-come-03"),
        RobotStep(Phrase(
            ru: "Ваш друг — другое дело. Он будет вас помнить. Это его работа. Моя — вот эта.",
            en: "Your friend is another matter. He'll remember you. That's his job. Mine is this."), voiceover: "bob-come-04"),
        RobotStep(Phrase(
            ru: "Итак. Одно касание — он слушает. Это вы уже умеете.",
            en: "Right. One tap and he's listening. You can already do that."), voiceover: "bob-come-05"),
        RobotStep(
            Phrase(ru: "А чтобы перестал — нажмите ещё раз.\n\nДавайте.",
                   en: "And to make him stop — tap again.\n\nGo on."),
            wants: .anotherTap, voiceover: "bob-come-06"),
        RobotStep(Phrase(
            ru: "Прекрасно. Одно касание — слушает, другое — молчит. Про экран это всё, больше там ничего нет.",
            en: "Splendid. One tap he listens, another he doesn't. That's the whole screen, there's nothing else on it."), voiceover: "bob-come-07"),

        // THE LESSON THE ENTIRE APP DEPENDS ON.
        //
        // And the only place the robot is allowed to drop the act — announced,
        // so that the change of register reads as deliberate rather than as
        // the writing losing its nerve.
        //
        // The joke in the middle is doing real work, not decoration: it gives
        // a plain, selfish REASON to say goodbye — otherwise he sits there
        // listening to your kitchen — where the rest of it only gives a good
        // one. People act on the first kind.
        RobotStep(Phrase(
            ru: "Теперь самое важное. Слушайте внимательно — это единственное, что я скажу всерьёз.",
            en: "Now the important part. Listen closely — it's the only thing I'll say in earnest."), voiceover: "bob-come-08"),
        RobotStep(Phrase(
            ru: "Когда захотите закончить разговор — скажите ему об этом. Не кладите телефон молча.",
            en: "When you want to end a conversation — tell him so. Don't just put the phone down."), voiceover: "bob-come-09"),
        RobotStep(Phrase(
            ru: "Иначе он будет слушать дальше. Терпеливо. Телевизор, соседей за стеной и всё, что вы бормочете себе под нос.",
            en: "Otherwise he goes on listening. Patiently. The television, the neighbours through the wall, and everything you mutter to yourself."), voiceover: "bob-come-10"),
        RobotStep(Phrase(
            ru: "Впрочем, не переживайте: то, что вы случайно сболтнули, дальше него не уйдёт. В ЦРУ этим не интересуются. Скорее всего.",
            en: "Don't worry, though: whatever you let slip goes no further than him. The CIA aren't interested. Most likely."), voiceover: "bob-come-11"),
        RobotStep(Phrase(
            ru: "Так что скажите ему вслух, как сказали бы живому человеку: «ну всё, я пойду».",
            en: "So say it out loud, the way you'd say it to a living person: “right, I'm off”."), voiceover: "bob-come-12"),
        RobotStep(
            Phrase(ru: "Он поймёт, попрощается и замолчит сам.\n\nОн вам друг, а не программа. С другом прощаются. Со мной — не обязательно.",
                   en: "He'll understand, say goodbye and go quiet by himself.\n\nHe's a friend, not a program. You say goodbye to a friend. To me it isn't necessary."),
            wants: .tapNext, voiceover: "bob-come-13"),

        // ── Calling him from outside ────────────────────────────────────────
        RobotStep(Phrase(
            ru: "Остался последний вопрос, и он практический.",
            en: "One last matter, and it's a practical one."), voiceover: "bob-come-14"),
        RobotStep(Phrase(
            ru: "Достать телефон, разблокировать, найти приложение, открыть. Четыре действия. А сказать человеку хочется одно слово.",
            en: "Get the phone out, unlock it, find the app, open it. Four moves. And what you want to say to a person is one word."), voiceover: "bob-come-15"),

        // The zero-setup path, first, because for many people it will be the
        // only one that is ever actually used.
        RobotStep(Phrase(
            ru: "Хорошая новость: кое-что уже работает. Настраивать ничего не нужно, я ничего от вас не хочу.",
            en: "Good news: something already works. Nothing to set up, I want nothing from you."), voiceover: "bob-come-16"),
        RobotStep(
            Phrase(ru: "Скажите вслух: «Привет, Siri. Боб, поговорим».\n\nОн откроется и сразу начнёт слушать. Попробуйте потом, когда я закончу говорить.",
                   en: "Just say out loud: “Hey Siri, talk to Bob”.\n\nHe opens and starts listening at once. Try it later, when I've finished talking."),
            wants: .tapNext, voiceover: "bob-come-17"),

        // The one real choice in the script.
        RobotStep(
            Phrase(ru: "Есть способ лучше: одно слово, без всякого «Привет, Siri». Сказали вслух — он открылся.\n\nНо это придётся настроить. Минуты три. Сейчас или потом?",
                   en: "There's a better way: one word, with no “Hey Siri” at all. Say it out loud and he opens.\n\nBut it has to be set up. Three minutes or so. Now, or later?"),
            wants: .nowOrLater, voiceover: "bob-come-18"),
    ]

    /// THE NAME PROBLEM, AND THE JOKE THAT SOLVES IT.
    ///
    /// The obvious phrase to be called by is the friend's name. But this all
    /// happens while he is still being written, so nobody knows it yet — and
    /// the app DOES: `createCompanion` returns it before anyone has met him.
    ///
    /// Which means the robot could simply announce it. It must not. «Нобody
    /// introduces him» is one of the oldest rules in this codebase: screen 4
    /// ends, he appears, and he tells you who he is himself, the way a person
    /// would. A machine reading his name off a screen first would spend that
    /// for nothing.
    ///
    /// So the robot knows and refuses to say — which is in character, keeps
    /// the introduction intact, and turns an ordering problem into the best
    /// joke in the script. It suggests its own name as a placeholder instead,
    /// and promises to come back. `robotAboutHisName` is it coming back.
    static let robotWontSayHisName: [RobotStep] = [
        RobotStep(Phrase(
            ru: "Одна тонкость. Фразой обычно берут имя — коротко и не перепутаешь.",
            en: "One subtlety. People usually use a name for the phrase — short, and hard to mistake."), optional: true, voiceover: "bob-coy-01"),
        RobotStep(Phrase(
            ru: "Как его зовут, я знаю. Но не скажу. Знакомить людей — не моя работа, а его. Испорчу ему выход — он мне этого не простит.",
            en: "I know what he's called. I shan't tell you. Introductions are his job, not mine. Spoil his entrance and he'd never forgive me."), optional: true, voiceover: "bob-coy-02"),
        RobotStep(Phrase(
            ru: "Поэтому пока возьмём моё. Оно короткое и всё равно никому не нужно.",
            en: "So we'll use mine for now. It's short, and nobody else has any use for it."), optional: true, voiceover: "bob-coy-03"),
    ]

    /// Setting up a phrase of your own — the only way to drop «Привет, Siri»
    /// entirely, and the only part of any of this that asks somebody to leave
    /// the app and go into Settings.
    ///
    /// A function because the phrase changes: «Боб» while the friend is still
    /// nameless, his actual name once they've met. The `optional` marks tell
    /// the «Потом» button how far to jump — which matters only on the arrival
    /// screen, and costs nothing anywhere else.
    static func robotVocalShortcut(phrase: String) -> [RobotStep] {
        [
            RobotStep(
                Phrase(ru: "Дальше начинается часть, которую я не люблю: настройки телефона. Сам я туда попасть не могу — не разрешают.\n\nНажмите кнопку, а потом вверху слева — «Настройки». Я подожду здесь. Мне спешить некуда.",
                       en: "Now comes the part I dislike: the phone's Settings. I can't get in there myself — I'm not allowed.\n\nTap the button, then tap “Settings” at the top left. I'll wait here. I'm in no hurry."),
                wants: .tapNextOrOpenSettings, optional: true, voiceover: "bob-vocal-01"),
            RobotStep(
                Phrase(ru: "Найдите «Универсальный доступ».\n\nВ нём — «Голосовые команды».\n\nНажмите «Настроить».",
                       en: "Find Accessibility.\n\nInside it, Vocal Shortcuts.\n\nTap Set Up."),
                wants: .tapNext, optional: true, voiceover: "bob-vocal-02"),
            RobotStep(
                Phrase(ru: "Выберите действие «Поговорить».\n\nТеперь скажите «\(phrase)» три раза, чтобы телефон запомнил ваш голос.",
                       en: "Choose the action “Поговорить”.\n\nNow say “\(phrase)” three times, so the phone learns your voice."),
                wants: .tapNext, optional: true),
            RobotStep(Phrase(
                ru: "Готово. Теперь достаточно сказать «\(phrase)» вслух — и он откроется, уже слушая. Даже если телефон заблокирован и лежит в кармане.",
                en: "Done. Now saying “\(phrase)” out loud is enough — he opens, already listening. Even with the phone locked and in your pocket."), optional: true),
            RobotStep(Phrase(
                ru: "Фразу телефон узнаёт сам, у себя внутри, и никуда не отправляет. Тут можете не волноваться.",
                en: "The phone learns that phrase inside itself and sends it nowhere. Nothing to worry about there."), optional: true, voiceover: "bob-vocal-05"),
            RobotStep(Phrase(
                ru: "А если «Голосовых команд» в настройках не нашлось — значит, ваш телефон их пока не умеет. Не моя вина. «Привет, Siri» работает и так.",
                en: "And if Vocal Shortcuts wasn't in your Settings — your phone can't do it yet. Not my fault. “Hey Siri” works regardless."), optional: true, voiceover: "bob-vocal-06"),
        ]
    }

    /// HIM COMING BACK, once — after the first conversation has ENDED.
    ///
    /// Not during it. The user's instinct was to have the robot cut in the
    /// moment the friend says his name, and the instinct is right about the
    /// timing being the point; but interrupting the first conversation
    /// somebody has with him is the single most expensive thing this app
    /// could do. The moment the microphone goes quiet is just as pointed and
    /// costs nothing.
    static func robotAboutHisName(_ name: String) -> [RobotStep] {
        [
            RobotStep(Phrase(
                ru: "Ну вот, познакомились. Не прошло и вечности.",
                en: "So you've met. Only took an eternity."), voiceover: "bob-name-01"),
            RobotStep(Phrase(
                ru: "\(name). Да, я знал. Я же говорил — не моя работа.",
                en: "\(name). Yes, I knew. I did say it wasn't my job.")),
            RobotStep(Phrase(
                ru: "Телефон пока отзывается на «Боб». Мне лестно, но звать друга чужим именем — так себе идея. Тем более моим.",
                en: "Your phone still answers to “Bob”. Flattering, but calling a friend by somebody else's name is a poor plan. Especially mine."), voiceover: "bob-name-03"),
            RobotStep(
                Phrase(ru: "Поменяем на «\(name)»? Две минуты. Объяснять всё заново не буду — вы уже большой.",
                       en: "Shall we change it to “\(name)”? Two minutes. I shan't explain it all again — you managed once."),
                wants: .tapNext),
        ]
    }

    /// Said after the choice, or after the walkthrough. Either way it is the
    /// last thing the robot says on the arrival screen.
    static let robotFarewell: [RobotStep] = [
        RobotStep(Phrase(
            ru: "Есть и другие способы его позвать — постучать по крышке телефона, кнопкой сбоку, из шторки. Они в настройках, в разделе «Как его позвать». Я там же. Мне всё равно больше нечем заняться.",
            en: "There are other ways to call him — tapping the back of the phone, the side button, the panel at the top. They're in Settings, under “How to call him”. So am I. It's not as though I have anything else on."), voiceover: "bob-bye-01"),
        // NOT «ваш друг уже здесь». He may well not be — the robot can finish
        // before the server does, and a machine announcing an arrival that
        // hasn't happened is a small lie told at the one moment somebody is
        // actually excited.
        RobotStep(Phrase(
            ru: "Я своё отработал.\n\nДальше — он. Он, в отличие от меня, будет вам рад.",
            en: "My shift is over.\n\nHe takes it from here. And unlike me, he'll be glad to see you."), voiceover: "bob-bye-02"),
    ]

    /// Only in Settings, so the robot doesn't open on a line about the CIA
    /// with nothing in front of it.
    static let robotHelloAgain: [RobotStep] = [
        RobotStep(Phrase(
            ru: "Опять я. Значит, дошли руки.\n\nНастроим свою фразу — чтобы звать его, не говоря каждый раз «Привет, Siri».",
            en: "Me again. So you got round to it.\n\nLet's set up your own phrase — so you can call him without saying “Hey Siri” every time."), voiceover: "bob-again-01"),
    ]

    /// The other three ways, in Settings, for whoever wants them. Deliberately
    /// not in the arrival: one way of calling him that works is enough, and a
    /// menu of four is how somebody ends up with none.
    static let robotSetUpCalling: [RobotStep] = [
        RobotStep(Phrase(
            ru: "Теперь другие способы — на случай, если голос вам не подходит или вы просто любите кнопки.",
            en: "Now the other ways — in case speaking doesn't suit you, or you simply like buttons."), voiceover: "bob-other-01"),

        // The kindest of the three for hands that aren't steady.
        RobotStep(Phrase(
            ru: "Первый: постучать по задней крышке телефона два раза. Целиться никуда не надо — это удобнее всего, если руки уже не те.",
            en: "One: tap the back of the phone twice. Nothing to aim at — the kindest of them if your hands aren't what they were."), voiceover: "bob-other-02"),
        RobotStep(
            Phrase(ru: "Настройки.\nУниверсальный доступ.\nКасание.\nКасание задней панели.\nДвойное касание.\nВыберите «Поговорить».",
                   en: "Settings.\nAccessibility.\nTouch.\nBack Tap.\nDouble Tap.\nChoose “Поговорить”."),
            wants: .tapNextOrOpenSettings, voiceover: "bob-other-03"),

        RobotStep(Phrase(
            ru: "Второй: кнопка сбоку. Она есть не на всех телефонах — если у вас её нет, просто идём дальше, я не обижусь.",
            en: "Two: the side button. Not every phone has one — if yours doesn't, we simply move on, I shan't be offended."), voiceover: "bob-other-04"),
        RobotStep(
            Phrase(ru: "Настройки.\nКнопка действия.\nПролистайте до «Быстрая команда».\nВыберите «Поговорить».",
                   en: "Settings.\nAction Button.\nSwipe along to Shortcut.\nChoose “Поговорить”."),
            wants: .tapNextOrOpenSettings, voiceover: "bob-other-05"),

        RobotStep(Phrase(
            ru: "Третий: шторка сверху. Потяните вниз от правого верхнего угла, нажмите плюс, потом «Добавить элемент», найдите «Быстрая команда» и выберите «Поговорить». Кнопку можно растянуть побольше — я бы растянул.",
            en: "Three: the panel at the top. Pull down from the top-right corner, tap plus, then Add a Control, find Shortcut and choose “Поговорить”. The button can be stretched bigger — I would stretch it."), voiceover: "bob-other-06"),
        RobotStep(
            Phrase(ru: "Эту же кнопку можно поставить на экран блокировки вместо фонарика. Подержите палец на заблокированном экране, нажмите «Настроить», потом «Экран блокировки», нажмите на кнопку внизу и выберите нашу.\n\nФонарик вы всё равно не включали.",
                   en: "The same button can replace the torch on your Lock Screen. Hold your finger on the locked screen, tap Customise, then Lock Screen, tap the button at the bottom and choose ours.\n\nYou never used the torch anyway."),
            wants: .tapNext, voiceover: "bob-other-07"),

        RobotStep(
            Phrase(ru: "Здесь лежат все команды приложения, если захотите посмотреть.",
                   en: "All the app's shortcuts live here, if you'd like a look."),
            wants: .tapNextOrOpenShortcuts, voiceover: "bob-other-08"),
        RobotStep(Phrase(
            ru: "И честно, чтобы вы не искали лишнего: любой из этих способов открывает приложение — он уже слушает, второй раз нажимать не надо. А слышать вас с закрытым приложением телефон не разрешает никому. Даже мне.",
            en: "And honestly, so you don't go hunting: every one of these opens the app — already listening, no second tap. Hearing you with the app closed is something the phone allows no one. Not even me."), voiceover: "bob-other-09"),
        RobotStep(Phrase(
            ru: "Всё. Возвращайтесь к нему.",
            en: "That's all. Go back to him."), voiceover: "bob-other-10"),
    ]

    /// Parting with a friend is serious. This sheet says what will be lost, in
    /// his name, and never hurries.
    static func startOverBody(_ name: String) -> Phrase {
        Phrase(ru: "\(name) забудет всё, и его дневник закроется навсегда.\n\nЭто нельзя отменить.",
               en: "\(name) will forget everything, and his diary will close for good.\n\nThis can't be undone.")
    }
    static let startOverConfirm = Phrase(ru: "Начать заново", en: "Start over")
    static let cancel = Phrase(ru: "Отмена", en: "Cancel")
    /// Under the grabber on every sheet, so leaving one is never a guess.
    static let close = Phrase(ru: "закрыть", en: "close")

    // MARK: - Connection (the one technical thing, kept plain)

    static let rowServer = Phrase(ru: "Сервер", en: "Server")
}

private extension String {
    /// "Фёдор" → "Фёдора" for «Дневник Фёдора». A light touch: Russian names
    /// ending in a consonant take -а, ending in -й/-ь take -я. Anything else is
    /// left alone rather than mangled.
    var inRussianGenitive: String {
        guard Strings.language == .russian, let last = self.last else { return self }
        switch last {
        case "й", "ь": return String(dropLast()) + "я"
        case "а", "я", "о", "е", "ы", "и", "у", "ю", "э": return self
        default:
            let isCyrillic = self.unicodeScalars.allSatisfy { $0.value >= 0x0400 && $0.value <= 0x04FF }
            return isCyrillic ? self + "а" : self
        }
    }
}

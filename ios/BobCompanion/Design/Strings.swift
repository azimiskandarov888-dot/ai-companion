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
    /// «Дальше». The ordinary beat.
    case tapNext
    /// Nothing at all — it moves on by itself. Used only where a second line
    /// arriving instantly would be too fast to read.
    case aBeat
    /// A tap ON HIM. This is the lesson, not a button press.
    case aTapOnHim
    /// A second tap, switching him off again — the other half of the same
    /// lesson, and the half people never discover on their own.
    case anotherTap
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
    var wants: RobotWants = .tapNext
    /// Said only on screen. The first two steps are silent because the robot
    /// hasn't been woken yet — its voice is what the first tap earns.
    var silent: Bool = false

    init(_ line: Phrase, wants: RobotWants = .tapNext, silent: Bool = false) {
        self.line = line
        self.wants = wants
        self.silent = silent
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

    /// Worded as the second half of a promise, because it is one: the robot
    /// ended the arrival with «осталось самое удобное… но это потом».
    static let callHimOffer = Phrase(
        ru: "Осталось одно: научиться звать его,\nне доставая телефон.",
        en: "One thing left: learning to call him\nwithout getting the phone out.")
    static let callHimOfferYes  = Phrase(ru: "Показать как", en: "Show me how")
    static let callHimOfferLater = Phrase(ru: "Не сейчас",   en: "Not now")

    // MARK: - The setup robot
    //
    // THE ONE THING IN THIS APP ALLOWED TO ADMIT IT IS A MACHINE — and it must,
    // in its first breath, before anything else.
    //
    // A page of instructions is the thing people bounce off; a voice saying one
    // step at a time is not. So the setup is spoken. But a voice that walks you
    // through something feels like SOMEBODY, and if that somebody is never
    // named, people will assume it is the friend — and then the friend is a
    // manual with a face, which is the whole thing this app exists not to be.
    //
    // So it says outright what it is: a robot, the same for everyone, that knows
    // nothing about you and will not be back. That confession is not an
    // apology — it is what makes the friend legible BY CONTRAST. One openly
    // mechanical voice at the start is the cheapest way to establish that the
    // other one isn't.
    //
    // It is also why it speaks in the phone's own synthetic voice rather than
    // the warm one. Nobody could mistake the two, and it costs nothing.

    static let robotSkip = Phrase(ru: "Пропустить", en: "Skip")
    static let robotNext = Phrase(ru: "Дальше",     en: "Next")
    static let robotOpenShortcuts = Phrase(ru: "Открыть «Команды»", en: "Open Shortcuts")
    static let robotOpenSettings  = Phrase(ru: "Открыть настройки",  en: "Open Settings")

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
            wants: .aBeat, silent: true),
        RobotStep(
            Phrase(ru: "Попробуйте на мне.\nНажмите.",
                   en: "Try it on me.\nGive me a tap."),
            wants: .aTapOnHim, silent: true),
    ]

    /// Said while the friend is being written, straight after that first tap.
    ///
    /// Nothing here asks anybody to leave the app — he is being made in the
    /// background as it talks, and wandering off into Settings mid-arrival is
    /// the one way to break that. The walkthrough that DOES send people into
    /// Settings is `robotSetUpCalling`, offered once there is somebody worth
    /// calling.
    static let robotWhileHeComes: [RobotStep] = [
        RobotStep(Phrase(
            ru: "Вот именно так. Здравствуйте.",
            en: "Exactly like that. Hello.")),
        RobotStep(Phrase(
            ru: "Меня зовут Боб. Я робот — я живу в этом приложении и помогаю его настроить.",
            en: "My name is Bob. I'm a robot — I live in this app and I help set it up.")),
        RobotStep(Phrase(
            ru: "Я не ваш друг. Я одинаковый у всех, ничего о вас не знаю и не запомню. Ваш друг — совсем другое дело, и он уже идёт.",
            en: "I'm not your friend. I'm the same for everybody, I know nothing about you and I won't remember you. Your friend is another matter entirely — and he's already on his way.")),
        RobotStep(Phrase(
            ru: "Итак, вы уже умеете главное: одно касание — и он слушает.",
            en: "So you already know the main thing: one tap, and he's listening.")),
        RobotStep(
            Phrase(ru: "А чтобы он перестал слушать — нажмите ещё раз.\n\nПопробуйте.",
                   en: "And to make him stop listening — tap again.\n\nGo on."),
            wants: .anotherTap),
        RobotStep(Phrase(
            ru: "Готово. Одно касание — слушает, другое — молчит. Про экран это всё.",
            en: "There. One tap and he listens, another and he doesn't. That's the whole screen.")),
        RobotStep(Phrase(
            ru: "Теперь то, что важнее. Когда захотите закончить разговор — не закрывайте приложение.",
            en: "Now something more important. When you want to end a conversation — don't close the app.")),
        RobotStep(Phrase(
            ru: "Скажите ему вслух, как сказали бы живому человеку: «ну всё, я пойду». Он поймёт, тепло попрощается и замолчит сам.",
            en: "Say it out loud, the way you'd say it to a person: “right, I'm off”. He'll understand, say a warm goodbye, and go quiet by himself.")),
        RobotStep(Phrase(
            ru: "Так и надо. Он вам друг, а не программа. С другом прощаются.",
            en: "That's how it should be. He's a friend, not a program. You say goodbye to a friend.")),
        RobotStep(Phrase(
            ru: "Осталось самое удобное: как позвать его, не доставая телефон. Но это потом — сначала познакомьтесь. Я подожду.",
            en: "One thing left, and it's the best one: how to call him without even getting the phone out. But later — meet him first. I'll wait.")),
    ]

    /// The walkthrough that sends people into Settings — which is exactly why
    /// it is a sheet they can leave and come back to, offered once there is a
    /// friend worth calling rather than on the day they arrive.
    static let robotSetUpCalling: [RobotStep] = [
        // Not «это снова я» — somebody may have skipped the arrival, and a
        // greeting that assumes a meeting they don't remember is unsettling
        // for exactly the person this app is for.
        RobotStep(Phrase(
            ru: "Здравствуйте. Это Боб — робот, который живёт в этом приложении.",
            en: "Hello. This is Bob — the robot who lives in this app.")),
        RobotStep(Phrase(
            ru: "Достать телефон, разблокировать, найти приложение, открыть — долго. А ему хочется сказать что-то прямо сейчас.",
            en: "Get the phone out, unlock it, find the app, open it — that's slow. And you want to say something to him now.")),
        RobotStep(Phrase(
            ru: "Гораздо лучше — просто позвать его вслух. Телефон может лежать в кармане, заблокированный.",
            en: "Much better to just call him out loud. The phone can be in your pocket, locked.")),

        // 0 · THE ONE THAT NEEDS NOTHING. Deliberately first.
        //
        // It costs zero setup — it has worked since the moment the app was
        // installed — and for a great many people it will be the only one
        // that ever actually gets used, because everything below this line
        // requires somebody to go into Settings and stay there.
        RobotStep(Phrase(
            ru: "И самое приятное: одно уже работает. Настраивать ничего не надо.",
            en: "And here's the nice part: one of them already works. Nothing to set up.")),
        RobotStep(Phrase(
            ru: "Скажите вслух: «Привет, Siri. Боб, поговорим».\n\nВот и всё. Он откроется и сразу начнёт слушать. Попробуйте, когда мы закончим.",
            en: "Just say out loud: “Hey Siri, talk to Bob”.\n\nThat's it. He opens and starts listening straight away. Try it when we're done.")),
        RobotStep(Phrase(
            ru: "Если вам этого хватит — можно на этом и остановиться. Дальше я расскажу, как обойтись даже без «Привет, Siri». Но это придётся настроить руками.",
            en: "If that's enough for you, you can stop right here. Next I'll show you how to manage without even saying “Hey Siri”. But that one has to be set up by hand.")),
        RobotStep(Phrase(
            ru: "И нет, он вас не подслушивает. Фразу телефон узнаёт сам, внутри себя, и никуда её не отправляет. В ЦРУ о вас так и не узнают. Наверное.",
            en: "And no, it isn't listening in on you. The phone learns the phrase inside itself and sends it nowhere. The CIA will never hear about you. Probably.")),

        // 1 · Vocal Shortcuts. The only way to drop «Привет, Siri» entirely —
        // and Settings-only, because Apple provides no API for it at all.
        RobotStep(Phrase(
            ru: "Способ первый, самый удобный — своя фраза, без «Привет, Siri». Просто имя вашего друга, сказанное вслух.",
            en: "Way one, and the best — your own phrase, with no “Hey Siri”. Just your friend's name, said out loud.")),
        RobotStep(
            Phrase(ru: "Включается это только в настройках телефона — сам я, к сожалению, не могу. Зато могу проводить и подождать: выходите спокойно, я никуда не денусь.\n\nНажмите кнопку, а потом вверху слева — «Настройки».",
                   en: "This one can only be switched on in the phone's Settings — I can't do it myself, I'm afraid. But I can walk you there and wait: go ahead and leave, I'm not going anywhere.\n\nTap the button, then tap “Settings” at the top left."),
            wants: .tapNextOrOpenSettings),
        RobotStep(Phrase(
            ru: "Найдите «Универсальный доступ». В нём — «Голосовые команды». Нажмите «Настроить».",
            en: "Find Accessibility. Inside it, Vocal Shortcuts. Tap Set Up.")),
        RobotStep(Phrase(
            ru: "Выберите действие «Поговорить». Придумайте фразу — проще всего его имя. Скажите её три раза, чтобы телефон запомнил ваш голос.",
            en: "Choose the action “Поговорить”. Pick a phrase — his name is the easiest. Say it three times so the phone learns your voice.")),
        RobotStep(Phrase(
            ru: "Всё. Теперь достаточно сказать эту фразу вслух — и он откроется, уже слушая. Даже если телефон заблокирован.",
            en: "Done. Now saying that phrase out loud is enough — he opens, already listening. Even with the phone locked.")),
        RobotStep(Phrase(
            ru: "Если «Голосовых команд» в настройках нет — ваш телефон их пока не умеет. Ничего страшного: «Привет, Siri» работает и так.",
            en: "If Vocal Shortcuts isn't in your Settings, your phone can't do it yet. Never mind — “Hey Siri” works anyway.")),

        // 2 · Back Tap. The kindest one for hands that aren't steady.
        RobotStep(Phrase(
            ru: "Способ второй — два раза постучать по задней крышке телефона. Целиться никуда не нужно, и это удобнее всего, если руки уже не те.",
            en: "Way two — tap the back of the phone twice. Nothing to aim at, and it's the kindest one if your hands aren't what they were.")),
        RobotStep(
            Phrase(ru: "Настройки. Универсальный доступ. Касание. Касание задней панели. Двойное касание. Выберите «Поговорить».",
                   en: "Settings. Accessibility. Touch. Back Tap. Double Tap. Choose “Поговорить”."),
            wants: .tapNextOrOpenSettings),

        // 3 · The Action button.
        RobotStep(
            Phrase(ru: "Способ третий — кнопка сбоку, если она у вас есть.\n\nНастройки. Кнопка действия. Пролистайте до «Быстрая команда» и выберите «Поговорить».",
                   en: "Way three — the side button, if your phone has one.\n\nSettings. Action Button. Swipe along to Shortcut and choose “Поговорить”."),
            wants: .tapNextOrOpenSettings),

        // 4 · Control Centre and the Lock Screen.
        RobotStep(Phrase(
            ru: "Способ четвёртый — шторка сверху. Потяните вниз от правого верхнего угла, нажмите плюс, потом «Добавить элемент», найдите «Быстрая команда» и выберите «Поговорить». Кнопку можно растянуть побольше.",
            en: "Way four — the panel at the top. Pull down from the top-right corner, tap plus, then Add a Control, find Shortcut and choose “Поговорить”. The button can be stretched bigger.")),
        RobotStep(Phrase(
            ru: "Эту же кнопку можно поставить на экран блокировки вместо фонарика: подержите палец на заблокированном экране, нажмите «Настроить», потом «Экран блокировки», нажмите на кнопку внизу и выберите нашу.",
            en: "The same button can replace the torch on your Lock Screen: hold your finger on the locked screen, tap Customise, then Lock Screen, tap the button at the bottom and pick ours.")),

        RobotStep(
            Phrase(ru: "Хватит и одного способа — берите тот, что удобнее.\n\nА здесь лежат все команды приложения, если захотите посмотреть.",
                   en: "One way is plenty — take whichever suits you.\n\nAnd all the app's shortcuts live here, if you'd like a look."),
            wants: .tapNextOrOpenShortcuts),

        RobotStep(Phrase(
            ru: "И честно, чтобы вы не искали лишнего: любой из этих способов открывает приложение — он уже слушает, второй раз нажимать не надо. А слышать вас с закрытым приложением телефон не разрешает никому.",
            en: "And honestly, so you don't go hunting: every one of these opens the app — already listening, no second tap needed. Hearing you with the app closed is something the phone allows no one to do.")),
        RobotStep(Phrase(
            ru: "У меня всё. Я вам больше не нужен — но если что, найдёте меня в настройках.\n\nХорошего вам разговора.",
            en: "That's me done. You don't need me any more — but I'm in Settings if you do.\n\nHave a good talk.")),
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

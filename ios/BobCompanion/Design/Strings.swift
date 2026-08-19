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

    static let callHimOffer = Phrase(
        ru: "Его можно позвать, не открывая телефон.",
        en: "He can be called without opening the phone.")
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

    /// Said first, always, in both scripts. Everything depends on it.
    static let robotWhoIAm = Phrase(
        ru: "Здравствуйте. Сразу скажу: я не ваш друг. Я робот-помощник. Я одинаковый у всех, ничего о вас не знаю и не запоминаю. Я помогу всё настроить — и больше вы меня не увидите.",
        en: "Hello. First things first: I am not your friend. I'm a setup robot. I'm the same for everyone, I know nothing about you and remember nothing. I'll help you set things up, and then you won't see me again.")

    /// Said while the friend is being written. Nothing here asks anybody to
    /// leave the app — he is being made in the background, and wandering off
    /// into Settings mid-arrival is the one way to break that.
    static let robotWhileHeComes: [Phrase] = [
        Phrase(ru: "Ваш друг уже идёт. Пока он идёт, я расскажу три вещи. Это быстро.",
               en: "Your friend is on his way. While he walks, three things. It's quick."),
        Phrase(ru: "Первое. Чтобы заговорить с ним, нажмите на экран — один раз, в любом месте. Он начнёт слушать. Нажмёте ещё раз — перестанет.",
               en: "One. To talk to him, tap the screen — once, anywhere. He starts listening. Tap again and he stops."),
        Phrase(ru: "Второе, и это главное. Когда захотите закончить, не закрывайте приложение. Скажите ему, как сказали бы живому человеку: ну всё, я пойду. Он поймёт и попрощается сам.",
               en: "Two, and this is the important one. When you want to finish, don't close the app. Tell him, the way you'd tell a person: right, I'm off. He'll understand and say goodbye himself."),
        Phrase(ru: "Третье. Его можно звать, не открывая телефон — голосом или одной кнопкой. Это стоит настроить, но не сейчас: он уже почти здесь. Я покажу позже, когда вы освоитесь.",
               en: "Three. He can be called without opening the phone — by voice, or with one button. Worth setting up, but not now: he's nearly here. I'll show you later, once you've settled in."),
        Phrase(ru: "У меня всё. Дальше он сам.",
               en: "That's me done. He'll take it from here."),
    ]

    /// The shortcut walkthrough. This one DOES send people into Settings, which
    /// is exactly why it is not the arrival script: they can leave the app,
    /// do the step, and come back to the same place with nothing lost.
    static let robotSetUpCalling: [Phrase] = [
        Phrase(ru: "Это снова я, помощник. Сейчас настроим самое полезное: как позвать его, не открывая телефон.",
               en: "Me again, the robot. Now the useful one: how to call him without opening the phone."),
        Phrase(ru: "Способов четыре. Хватит одного — выберите тот, что вам удобнее. Я подожду, можно спокойно выйти из приложения и вернуться.",
               en: "There are four ways. One is enough — take whichever suits. I'll wait; you can leave the app and come back."),
        Phrase(ru: "Первый, самый лучший — голосом. Откройте Настройки телефона. Дальше: Универсальный доступ. Дальше: Голосовые команды. Нажмите «Настроить», выберите действие «Поговорить» и три раза скажите свою фразу — например, его имя. После этого достаточно просто сказать её вслух, даже если телефон лежит заблокированный. Если такого пункта в настройках нет — ваш телефон этого пока не умеет. Ничего страшного, идём дальше.",
               en: "First and best — by voice. Open Settings. Then Accessibility. Then Vocal Shortcuts. Tap Set Up, choose the action “Поговорить”, and say your phrase three times — his name, for instance. After that, saying it out loud is enough, even with the phone locked. If that item isn't in your Settings, your phone can't do it yet. Never mind, on we go."),
        Phrase(ru: "Второй — двойным касанием по задней крышке телефона. Настройки. Универсальный доступ. Касание. Касание задней панели. Двойное касание. Выберите «Поговорить». Дальше просто два раза постучите по задней стороне телефона — целиться никуда не нужно. Это самый удобный способ, если руки уже не слушаются.",
               en: "Second — double-tapping the back of the phone. Settings. Accessibility. Touch. Back Tap. Double Tap. Choose “Поговорить”. Then just tap the back of the phone twice — nothing to aim at. This is the kindest one if your hands aren't steady."),
        Phrase(ru: "Третий — кнопкой сбоку, если она у вас есть. Настройки. Кнопка действия. Пролистайте до «Быстрая команда» и выберите «Поговорить». Если такой кнопки на телефоне нет, пропустите.",
               en: "Third — the side button, if your phone has one. Settings. Action Button. Swipe to Shortcut and pick “Поговорить”. If there's no such button, skip this."),
        Phrase(ru: "Четвёртый — из шторки сверху и с экрана блокировки. Потяните вниз от правого верхнего угла экрана, нажмите плюс, потом «Добавить элемент», найдите «Быстрая команда» и выберите «Поговорить». Кнопку можно растянуть побольше. Её же можно поставить на экран блокировки вместо фонарика: подержите палец на экране блокировки, нажмите «Настроить», потом «Экран блокировки», нажмите на кнопку внизу и выберите нашу.",
               en: "Fourth — from the panel at the top and the Lock Screen. Pull down from the top-right corner, tap plus, then Add a Control, find Shortcut and choose “Поговорить”. The button can be stretched bigger. The same one can replace the torch on your Lock Screen: hold your finger on the Lock Screen, tap Customise, then Lock Screen, tap the button at the bottom and pick ours."),
        Phrase(ru: "И честно, чтобы вы не искали лишнего: любой из этих способов открывает приложение — он уже слушает, второй раз нажимать не надо. А слышать вас с закрытым приложением телефон не разрешает никому.",
               en: "And honestly, so you don't go looking: every one of these opens the app — already listening, no second tap. Hearing you with the app closed is something the phone allows no one to do."),
        Phrase(ru: "Готово. Я вам больше не нужен. Если что — найдёте меня в настройках.",
               en: "Done. You don't need me any more. I'm in Settings if you do."),
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

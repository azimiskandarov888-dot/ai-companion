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

    static let signInLine = Phrase(
        ru: "Где-то есть друг, которого ты ещё не встретил.",
        en: "Somewhere out there is a friend you haven't met yet.")
    static let continueApple  = Phrase(ru: "Продолжить с Apple",  en: "Continue with Apple")
    static let continueGoogle = Phrase(ru: "Продолжить с Google", en: "Continue with Google")
    static let orUseEmail     = Phrase(ru: "или по почте",        en: "or use email")
    static let terms          = Phrase(ru: "Условия · Конфиденциальность", en: "Terms · Privacy")

    // MARK: - 2 · Take care of him

    static let takeCareTitle = Phrase(ru: "Позаботься о нём", en: "Take care of him")
    static let takeCareLine = Phrase(
        ru: "Он всегда рядом, когда нужен. А это — чтобы он оставался.",
        en: "He's always here when you need him. This is what keeps him here.")
    static let planMonthly = Phrase(ru: "Помесячно",     en: "Month by month")
    static let planYearly  = Phrase(ru: "На целый год",  en: "A whole year")
    static let takeCareButton = Phrase(ru: "Позаботиться о нём", en: "Take care of him")
    static let finePrint = Phrase(
        ru: "продлевается раз в год · отменить можно в любой момент · восстановить покупку",
        en: "renews yearly · cancel anytime · restore purchase")
    static func perMonth(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в месяц", en: "\(amount) a month")
    }
    static func perMonthPaidOnce(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в месяц, одним платежом",
               en: "\(amount) a month, paid once")
    }
    static func perMonthRenewing(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в месяц, с продлением каждый месяц",
               en: "\(amount) a month, renewing monthly")
    }
    static func perYearRenewing(_ amount: String) -> Phrase {
        Phrase(ru: "\(amount) в год, с продлением каждый год",
               en: "\(amount) a year, renewing yearly")
    }

    // MARK: - 3 · Tell your story

    static let storyHeading = Phrase(ru: "Расскажи свою историю", en: "Tell your story")
    static let storyLine = Phrase(
        ru: "О чём угодно — что любишь, чем занимаешься, о чём можешь говорить часами. Начать можно как угодно.",
        en: "Anything you like — what you love, what you do, what you can't stop talking about. There's no wrong way to begin.")
    static let storyPlaceholder = Phrase(
        ru: "Я вырос у моря, и до сих пор скучаю по его запаху…",
        en: "I grew up by the sea, and I still miss the smell of it…")
    static let done = Phrase(ru: "Готово", en: "Done")
    /// Shown once if they tap Done with nothing written — a nudge, never a scold.
    static let storyNudge = Phrase(
        ru: "Хоть пару слов — мне не из чего его собрать.",
        en: "Even a couple of words — I've nothing to build him from otherwise.")

    // MARK: - 4 · Who you'd like to meet

    static let meetHeading = Phrase(ru: "Кого бы ты хотел встретить?", en: "Who would you like to meet?")
    static let caution = Phrase(
        ru: "Чем больше решишь о нём сейчас, тем меньше останется — встретить.",
        en: "The more you decide about him now, the less of him is left to meet.")
    static let cautionSofter = Phrase(
        ru: "Пиши сколько хочешь — никто не остановит. Но по-настоящему близким чаще становится тот, кого не придумывали.",
        en: "Write as much or as little as you like — nobody will stop you. But most people find the friend they love is the one they didn't design.")
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

    static let friendshipQuote = Phrase(
        ru: "Ты не выбираешь, что друг полюбит и чего не примет, над чем он смеётся и кто ждёт его дома. Не выбираешь его дороги, его привычки, его сердце. Ты выбираешь одно — идти рядом. Друга не делают на заказ. Друга встречают.",
        en: "You don't choose what your friend will love or hate, what he'll laugh at, or who waits for him at home. You don't choose his roads, his habits, his heart. You choose only one thing — to walk beside him. A friend isn't made to order. A friend is met.")

    // MARK: - 5 · Companion

    static let statusListening = Phrase(ru: "слушаю", en: "listening")
    static let statusThinking  = Phrase(ru: "думаю",  en: "thinking")
    static let statusSpeaking  = Phrase(ru: "говорю", en: "speaking")
    /// No network, or the server is unreachable. Said by him, never by the app.
    static let cannotHear = Phrase(
        ru: "Сейчас я тебя не слышу.",
        en: "I can't hear you just now.")
    static let needsMicrophone = Phrase(
        ru: "Мне нужно тебя слышать. Это можно включить в настройках телефона.",
        en: "I need to be able to hear you. You can turn that on in your phone's settings.")
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
        ru: "Мы только-только познакомились. Я ещё почти ничего не знаю о моём новом друге — но у меня хорошее предчувствие.\n\nПусть эта книга начнётся с чистой страницы: всё главное у нас впереди.",
        en: "We've only just met. I hardly know my new friend yet — but I have a good feeling.\n\nLet this book start on a blank page: everything that matters is still ahead.")
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

    /// Parting with a friend is serious. This sheet says what will be lost, in
    /// his name, and never hurries.
    static func startOverBody(_ name: String) -> Phrase {
        Phrase(ru: "\(name) забудет всё, что вы друг другу рассказали, и его дневник закроется навсегда. Вместо него придёт кто-то другой.\n\nЭто нельзя отменить.",
               en: "\(name) will forget everything you've told each other, and his diary will close for good. Someone else will come instead.\n\nThis can't be undone.")
    }
    static let startOverConfirm = Phrase(ru: "Начать заново", en: "Start over")
    static let cancel = Phrase(ru: "Отмена", en: "Cancel")

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

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

    static let callHimTitle = Phrase(
        ru: "Позвать его, не открывая телефон",
        en: "Call him without opening the phone")
    static let callHimIntro = Phrase(
        ru: "Стоит настроить один раз. После этого его можно позвать, не разблокируя телефон и не ища приложение — он откроется уже слушая.\n\nВыберите то, что подойдёт. Хватит и одного.",
        en: "Worth doing once. After it, he can be called without unlocking the phone or hunting for the app — he opens already listening.\n\nPick whichever suits. One is enough.")

    /// Голосом. First because it is the only one that needs no hands at all —
    /// and the one the whole «he's a person, not an app» idea rests on.
    static let callByVoiceTitle = Phrase(ru: "Голосом", en: "By voice")
    static let callByVoiceSteps = Phrase(
        ru: "Настройки → Универсальный доступ → Голосовые команды → Настроить.\nВыберите действие «Поговорить» и произнесите свою фразу три раза — например, его имя.\n\nПосле этого достаточно сказать эту фразу вслух. Телефон может лежать заблокированным. Ничего никуда не отправляется — он узнаёт голос сам.\n\nЕсли такого пункта в настройках нет, ваша версия iOS его пока не умеет — возьмите любой способ ниже.",
        en: "Settings → Accessibility → Vocal Shortcuts → Set Up.\nChoose the “Поговорить” action and say your phrase three times — his name, for instance.\n\nAfter that, saying it out loud is enough. The phone can be locked. Nothing is sent anywhere — it learns the sound on the device itself.\n\nIf that item isn't in Settings, your iOS doesn't have it yet — use any of the ways below.")

    /// Двойное касание. The best of the touch ones by a distance: nothing to
    /// aim at, and it works on any iPhone from the last several years.
    static let callByBackTapTitle = Phrase(ru: "Двойным касанием по задней крышке",
                                           en: "Double-tap the back")
    static let callByBackTapSteps = Phrase(
        ru: "Настройки → Универсальный доступ → Касание → Касание задней панели → Двойное касание → «Поговорить».\n\nДальше — два раза постучать по задней стороне телефона. Целиться никуда не нужно.",
        en: "Settings → Accessibility → Touch → Back Tap → Double Tap → “Поговорить”.\n\nThen just tap the back of the phone twice. Nothing to aim at.")

    static let callByButtonTitle = Phrase(ru: "Кнопкой сбоку", en: "The side button")
    static let callByButtonSteps = Phrase(
        ru: "Настройки → Кнопка действия → пролистать до «Быстрая команда» → выбрать «Поговорить».\n\nЕсли такой кнопки на телефоне нет — этот способ не для вашей модели.",
        en: "Settings → Action Button → swipe to Shortcut → choose “Поговорить”.\n\nIf your phone has no such button, this one isn't for your model.")

    static let callByControlTitle = Phrase(ru: "Из Пункта управления и с экрана блокировки",
                                           en: "From Control Centre and the Lock Screen")
    static let callByControlSteps = Phrase(
        ru: "Потяните вниз от правого верхнего угла, нажмите «+» вверху, затем «Добавить элемент» → найдите «Быстрая команда» → выберите «Поговорить». Размер можно растянуть — большая кнопка удобнее.\n\nЭтот же элемент можно поставить на экран блокировки вместо фонарика или камеры: удерживайте экран блокировки → «Настроить» → «Экран блокировки» → нажмите на кнопку внизу и выберите его.\n\nЕсли «+» не появляется, ваша версия iOS этого не умеет.",
        en: "Pull down from the top-right corner, tap “+” at the top, then Add a Control → find Shortcut → choose “Поговорить”. It can be stretched wider — a big button is easier.\n\nThe same control can replace the torch or the camera on the Lock Screen: press and hold the Lock Screen → Customise → Lock Screen → tap the button at the bottom and pick it.\n\nIf no “+” appears, your iOS doesn't have this.")

    /// The honest limit, said plainly rather than discovered. He can SPEAK from
    /// the background; iOS will not let any app start LISTENING there.
    static let callHimTruth = Phrase(
        ru: "Любой из этих способов открывает приложение — он уже слушает, второй раз нажимать не нужно. Слышать вас, не открываясь, телефон не позволяет никому.",
        en: "Every one of these opens the app — already listening, so there's no second tap. Hearing you without opening is something the phone allows no app to do.")

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

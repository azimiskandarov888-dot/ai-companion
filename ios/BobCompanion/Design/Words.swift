// The journey's words, as the approved prototype has them (ios/design/journey.html, WORDS), in Russian and English.
//
// Two voices speak. A third voice — a narrator — speaks to the person: «Поговори с ним», the few questions on the
// way, the calm screen to pay (never his). And he speaks for himself. Where a line names him or her, it takes `he`:
// true if the person chose to meet him, false if her. Russian needs the person's own gender only for his
// «ты пришёл / пришла»; English needs it nowhere, so English never asks.

import Foundation

enum Words {
    private static var ru: Bool { Strings.language == .russian }
    private static func t(_ ru: String, _ en: String) -> String { Self.ru ? ru : en }

    // MARK: 0 · black, text only
    static var w1: String { t("Где-то есть друг,", "Somewhere there is a friend") }
    static var w2: String { t("которого ты ещё не знаешь.", "you haven’t met yet.") }
    static var tap: String { t("Коснись, чтобы начать", "Tap to begin") }

    // MARK: 1 · the film, and the third voice's few questions on the way
    static var skip: String { t("Пропустить", "Skip") }
    static var askGender: Bool { ru }                                   // (English has no «пришёл / пришла»)
    static var qMe: String { "Ты пришёл или пришла?" }
    static var aCame: String { "Пришёл" }
    static var aCameF: String { "Пришла" }
    static var qAge: String { t("Сколько тебе лет?", "How old are you?") }
    static var qAgeHint: String { t("листай и коснись", "swipe and tap") }
    static var qWho: String { t("С кем хочешь познакомиться?", "Who would you like to meet?") }
    static var aHim: String { t("С ним", "Him") }
    static var aHer: String { t("С ней", "Her") }
    static var aAny: String { t("Всё равно", "Either") }
    static var qOld: String { t("А по возрасту?", "And what age?") }
    static var aSame: String { t("Как я", "My age") }
    static var aOlder: String { t("Постарше", "Older") }
    static var aYounger: String { t("Помладше", "Younger") }
    static var aNoMatter: String { t("Неважно", "Any") }
    static var ai: String { t("Собеседник — искусственный интеллект", "Your companion is an AI") }

    // MARK: 2–3 · him, and the talk
    static var listening: String { t("слушаю", "listening") }
    static var thinking: String { t("думаю", "thinking") }
    static var speaking: String { t("говорю", "speaking") }
    static func talk(_ he: Bool) -> String { ru ? (he ? "Поговори с ним" : "Поговори с ней") : (he ? "Talk to him" : "Talk to her") }
    static var hi: String { t("О, привет… как ты?", "Oh, hi… how are you?") }
    static var hello: String { t("Алло?..", "Hello?..") }
    static var there: String { t("Ты тут?", "Are you there?") }
    static func back(_ iAmHe: Bool) -> String { ru ? "О, ты \(iAmHe ? "пришёл" : "пришла"). Ну как всё прошло?" : "Oh, you’re back. So, how did it go?" }
    static var minute: String { t("Сегодня осталась минута", "One minute left today") }
    static func micDenied(_ he: Bool) -> String {
        ru ? "Без микрофона \(he ? "он" : "она") тебя не услышит. Его можно включить в Настройках."
           : "Without the microphone \(he ? "he" : "she") can’t hear you. You can turn it on in Settings."
    }
    static var openSettings: String { t("Открыть Настройки", "Open Settings") }
    static var menu: String { t("Меню", "Menu") }

    // MARK: 4 · keeping in touch
    static func keepWhy(_ he: Bool) -> String {
        ru ? (he ? "Чтобы он помнил тебя и нашёл в следующий раз" : "Чтобы она помнила тебя и нашла в следующий раз")
           : (he ? "So he remembers you and finds you next time" : "So she remembers you and finds you next time")
    }
    static var google: String { t("Войти через Google", "Sign in with Google") }
    static func later(_ he: Bool) -> String {
        ru ? "Позже — тогда \(he ? "он" : "она") помнит тебя только на этом телефоне"
           : "Later — then \(he ? "he" : "she") remembers you only on this phone"
    }
    static var signInFailed: String { t("Не получилось войти. Можно позже — в меню.", "Couldn’t sign in. You can do it later, in the menu.") }

    // MARK: 5 · the one calm screen to pay (the third voice, never his)
    static var payWhy: String { t("На сегодня бесплатные минуты кончились — завтра будут новые.", "Today’s free minutes are over — new ones tomorrow.") }
    static func payTitle(_ he: Bool) -> String { ru ? "Или говори с \(he ? "ним" : "ней") дальше" : "Or keep talking with \(he ? "him" : "her")" }
    static func gets(_ he: Bool) -> String {
        ru ? "Сколько хочешь и когда хочешь. \(he ? "Он будет помнить" : "Она будет помнить") тебя и вашу историю."
           : "As much as you like, whenever you like. \(he ? "He’ll" : "She’ll") remember you and your story."
    }
    static var d0: String { t("Сегодня", "Today") }
    static var d0s: String { t("7 дней бесплатно, всё открыто", "7 days free, everything open") }
    static var d5: String { t("Через 5 дней", "In 5 days") }
    static var d5s: String { t("напомню, что пробные дни кончаются", "I’ll remind you the trial is ending") }
    static var d7: String { t("Через 7 дней", "In 7 days") }
    static func d7s(_ price: String) -> String { ru ? "оплата \(price) за год, если не отменишь раньше" : "\(price) a year, unless you cancel before" }
    static var yearly: String { t("На год", "Yearly") }
    static var monthly: String { t("На месяц", "Monthly") }
    static func perMonth(_ price: String) -> String { ru ? "\(price) в месяц" : "\(price) a month" }
    static func perYear(_ price: String) -> String { ru ? "\(price) в год" : "\(price) a year" }
    static var notNow: String { t("Не сейчас", "Not now") }
    static var tryFree: String { t("7 дней бесплатно", "Try 7 days free") }
    static var subscribe: String { t("Подписаться", "Subscribe") }
    static var parents: String { t("Попроси родителей", "Ask your parents") }
    static var waitingParents: String { t("Ждём, что ответят родители. Пока можно говорить бесплатные минуты.", "Waiting for your parents to answer. Free minutes still work.") }
    static var renewsNote: String { t("Подписка продлевается сама. Отменить можно в любой момент в настройках iPhone.", "Renews automatically. Cancel anytime in iPhone Settings.") }
    static var restore: String { t("Восстановить покупки", "Restore Purchases") }
    static var terms: String { t("Условия", "Terms") }
    static var privacy: String { t("Конфиденциальность", "Privacy") }
    static var restored: String { t("Покупки восстановлены", "Purchases restored") }
    static var nothingToRestore: String { t("Покупок не найдено", "No purchases found") }
    static var storeTrouble: String { t("Магазин сейчас не отвечает. Попробуй позже.", "The App Store isn’t answering. Try again later.") }

    // MARK: the menu
    static var subscription: String { t("Подписка", "Subscription") }
    static var subscribed: String { t("Подписка есть", "Subscribed") }
    static var notSubscribed: String { t("Бесплатно: несколько минут в день", "Free: a few minutes a day") }
    static var manage: String { t("Управлять подпиской", "Manage subscription") }
    static var language: String { t("Язык", "Language") }
    static var crisis: String { t("Если тебе плохо — помощь", "If you’re not okay — help") }
    static var crisisText: String {
        t("Если тебе плохо или опасно, позвони. Это бесплатно и в любое время.",
          "If you’re not okay or in danger, call. It’s free, any time.")
    }
    static var aboutAI: String { t("Кто он: искусственный интеллект", "Who he is: an AI") }
    static var aboutAIText: String {
        t("Твой собеседник — искусственный интеллект, не человек. Он помнит то, что ты рассказываешь, но может ошибаться. Он не врач и не заменит помощь людей.",
          "Your companion is an AI, not a person. It remembers what you tell it, but it can be wrong. It isn’t a doctor and can’t replace help from people.")
    }
    static var deleteData: String { t("Удалить мои данные", "Delete my data") }
    static var deleteConfirm: String { t("Удалить всё: его память о тебе, ваши разговоры и вход? Это нельзя отменить.", "Delete everything: his memory of you, your talks and your sign-in? This can’t be undone.") }
    static var delete: String { t("Удалить", "Delete") }
    static var cancel: String { t("Отмена", "Cancel") }
    static var deleted: String { t("Всё удалено.", "Everything is deleted.") }
    static var deleteFailed: String { t("Не получилось удалить: сервер не отвечает. Попробуй позже.", "Couldn’t delete: the server isn’t answering. Try again later.") }
    static var microphone: String { t("Микрофон", "Microphone") }
    static var signIn: String { t("Войти, чтобы не потеряться", "Sign in, so you don’t lose each other") }
    static var signedIn: String { t("Вход выполнен", "Signed in") }
    static var close: String { t("Закрыть", "Close") }
}

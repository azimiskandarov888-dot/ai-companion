// The three things the app remembers about itself: who you are, whether he's
// being looked after, and whether he has arrived yet.
//
// ▸ Accounts and billing are NOT built on the server yet, so both are stubbed
//   here behind small protocols. Screens 1 and 2 are fully real — every pixel,
//   every state, every animation — and only the last inch is a stand-in:
//   signing in stores a local account, and paying just advances.
//
//   When the real ones land, swap the two `Stub…` types for `AppleSignIn…` and
//   `StoreKit…`. No screen changes.

import Foundation
import SwiftUI

// MARK: - Who you are

struct Account: Codable, Equatable {
    var name: String
    /// "Apple", "Google", or "email" — shown on the Account screen.
    var provider: String
    var joined: Date

    var initial: String { String(name.prefix(1)).uppercased() }
}

protocol AccountProviding {
    func signIn(with provider: String) async throws -> Account
}

/// Stand-in: creates a local account with no network and no Apple Developer
/// account required. Real Sign in with Apple replaces this file's body only.
struct StubAccountProvider: AccountProviding {
    func signIn(with provider: String) async throws -> Account {
        try? await Task.sleep(nanoseconds: 450_000_000)   // a beat, so it feels real
        return Account(name: Strings.language == .russian ? "Друг" : "Friend",
                       provider: provider,
                       joined: Date())
    }
}

// MARK: - Whether he's being looked after

enum Plan: String, Codable, CaseIterable {
    case monthly, yearly

    var title: String { self == .monthly ? Strings.planMonthly() : Strings.planYearly() }

    /// ▸ PLACEHOLDER PRICES, straight from the design.
    ///   At ship these come from StoreKit — a price is never hard-coded, because
    ///   the App Store shows it in the buyer's own currency and store.
    var price: String { self == .monthly ? "349 ₽" : "2 690 ₽" }

    /// The small line inside the card.
    var detail: String {
        self == .monthly ? Strings.perMonth("349 ₽")()
                         : Strings.perMonthPaidOnce("224 ₽")()
    }

    /// The honest line directly above the button — what will actually be
    /// charged, and how often. Never buried in fine print.
    var summary: String {
        self == .monthly ? Strings.perMonthRenewing("349 ₽")()
                         : Strings.perYearRenewing("2 690 ₽")()
    }
}

protocol SubscriptionProviding {
    func purchase(_ plan: Plan) async throws -> Bool
}

/// Stand-in: no StoreKit, no products, no receipts. The real one opens Apple's
/// own payment sheet — which is why the button never opens a website.
struct StubSubscriptionProvider: SubscriptionProviding {
    func purchase(_ plan: Plan) async throws -> Bool {
        try? await Task.sleep(nanoseconds: 700_000_000)
        return true
    }
}

// MARK: - The one place the app's own state lives

@MainActor
final class AppState: ObservableObject {

    @Published private(set) var account: Account?
    @Published private(set) var isSubscribed: Bool
    /// What they wrote about themselves on screen 3. Kept so «My story» can
    /// reopen it, and so he can be rebuilt if they ever start over.
    @Published var story: String
    /// What they asked for on screen 4. May be empty — that's a fine answer.
    @Published var wishes: String
    /// Where they said they live, in their own words («в Израиле», «Канада»).
    /// Sent once, when he is created, and it decides which emergency number he
    /// is told to dial. A fact about the PERSON, not about the friend, so
    /// «Начать заново» leaves it alone.
    @Published var country: String
    /// How old they said they are, in their own words. Sent once, and the
    /// server keeps only a BAND from it and only when it is not an adult's —
    /// see young.py. There is no age screen anywhere in this app: the warm-up
    /// asks the way a friend asks, and that is the whole mechanism.
    @Published var age: String
    /// A teenager's own answer about being remembered. Mirrored here only so
    /// Settings can show it; the SERVER is where it actually decides anything.
    @Published private(set) var remembersMe: Bool
    /// His name, once he has arrived. Empty until the server creates him.
    @Published private(set) var companionName: String
    /// Whether onboarding is FINISHED. Kept separately from his name on
    /// purpose: if the backend was unreachable when he was created he arrives
    /// without one, and keying off the name alone sent the app back to screen 4
    /// on every launch. Onboarding is done when it's done.
    @Published private(set) var hasArrived: Bool

    private let accounts: AccountProviding
    private let subscriptions: SubscriptionProviding
    private let defaults = UserDefaults.standard

    private enum Keys {
        static let account = "account"
        static let subscribed = "isSubscribed"
        static let story = "story"
        static let wishes = "wishes"
        static let country = "country"
        static let age = "age"
        static let remembersMe = "remembersMe"
        static let companionName = "companionName"
        static let hasArrived = "hasArrived"
    }

    init(accounts: AccountProviding = StubAccountProvider(),
         subscriptions: SubscriptionProviding = StubSubscriptionProvider()) {
        self.accounts = accounts
        self.subscriptions = subscriptions
        self.isSubscribed   = defaults.bool(forKey: Keys.subscribed)
        self.story          = defaults.string(forKey: Keys.story) ?? ""
        self.wishes         = defaults.string(forKey: Keys.wishes) ?? ""
        self.country        = defaults.string(forKey: Keys.country) ?? ""
        self.age            = defaults.string(forKey: Keys.age) ?? ""
        self.remembersMe    = defaults.bool(forKey: Keys.remembersMe)
        self.companionName  = defaults.string(forKey: Keys.companionName) ?? ""
        self.hasArrived     = defaults.bool(forKey: Keys.hasArrived)
        if let data = defaults.data(forKey: Keys.account) {
            self.account = try? JSONDecoder().decode(Account.self, from: data)
        }
    }

    /// Where the app should open. After onboarding this is always `.companion` —
    /// the app never shows sign-in again, and never introduces him.
    var startingScreen: AppScreen {
        if account == nil          { return .signIn }
        if !isSubscribed           { return .takeCare }
        if story.isEmpty           { return .story }
        if !hasArrived             { return .meet }
        return .companion
    }

    // MARK: actions

    func signIn(with provider: String) async throws {
        let account = try await accounts.signIn(with: provider)
        self.account = account
        defaults.set(try? JSONEncoder().encode(account), forKey: Keys.account)
    }

    func purchase(_ plan: Plan) async throws {
        guard try await subscriptions.purchase(plan) else { return }
        isSubscribed = true
        defaults.set(true, forKey: Keys.subscribed)
    }

    func saveStory(_ text: String) {
        story = text
        defaults.set(text, forKey: Keys.story)
    }

    func saveWishes(_ text: String) {
        wishes = text
        defaults.set(text, forKey: Keys.wishes)
    }

    func saveCountry(_ text: String) {
        country = text
        defaults.set(text, forKey: Keys.country)
    }

    func saveAge(_ text: String) {
        age = text
        defaults.set(text, forKey: Keys.age)
    }

    /// WHETHER TO ASK THIS PERSON ABOUT MEMORY AT ALL.
    ///
    /// A deliberate second copy of young.band, and it is allowed to be one:
    /// the SERVER decides what is kept, always, and both ways of drifting fail
    /// safe. Drift low and the question goes unasked, so memory stays off.
    /// Drift high and it is asked of somebody whose answer the server simply
    /// refuses — young.allow takes a teenager's and nobody else's.
    var isTeenager: Bool {
        guard let digits = age.split(whereSeparator: { !$0.isNumber }).first,
              let years = Int(digits)
        else { return false }
        return (13...17).contains(years)
    }

    /// Their answer. The server first; the phone only if it took.
    func setRemembersMe(_ yes: Bool) async {
        do {
            try await BackendClient(baseURL: AppConfig.shared.backendURL)
                .keepMemory(yes)
        } catch {
            Trouble.shared.record(error, url: AppConfig.shared.backendURL)
            return
        }
        remembersMe = yes
        defaults.set(yes, forKey: Keys.remembersMe)
    }

    func remember(companionName name: String) {
        companionName = name
        defaults.set(name, forKey: Keys.companionName)
    }

    /// He is here. From now on the app opens to him and nothing else — whether
    /// or not the server managed to give him a name.
    func markArrived() {
        hasArrived = true
        defaults.set(true, forKey: Keys.hasArrived)
    }

    func signOut() {
        account = nil
        defaults.removeObject(forKey: Keys.account)
    }

    /// PARTING WITH A FRIEND. He is now deleted on the SERVER too.
    ///
    /// That is the whole change here. This used to clear three keys in
    /// UserDefaults while the sheet told the person, in writing, that he would
    /// forget everything and his diary would close forever — and he forgot
    /// nothing. One phone had forgotten his name; that was all that happened.
    ///
    /// What he knew about HIS OWN life goes with him, along with his diary,
    /// his week and everything the two of them had been through. What they
    /// told him about THEMSELVES stays true whoever they are talking to, which
    /// is what makes starting over «choose who to meet next» rather than
    /// «tell it all again». backend/app/erase.py draws the line.
    ///
    /// The phone is cleared even when the server could not be reached. The
    /// alternative traps somebody with a friend they have decided to leave —
    /// and it self-heals anyway, because writing the next one erases the last
    /// one (matchmaker.create_companion → erase.the_companion).
    func startOver() async {
        try? await BackendClient(baseURL: AppConfig.shared.backendURL).startOver()
        forgetCompanionLocally()
    }

    /// Only this phone's memory of him, with nothing said to the server.
    ///
    /// For `reconcileWithServer`, which is reacting to a server that has
    /// ALREADY said there is nobody. Asking it to delete him again would be
    /// asking it to delete a stranger, and on a phone pointed at the wrong
    /// address that stranger is somebody real.
    func forgetCompanionLocally() {
        for key in [Keys.wishes, Keys.companionName, Keys.hasArrived] {
            defaults.removeObject(forKey: key)
        }
        wishes = ""; companionName = ""; hasArrived = false
    }

    /// LEAVING. Everything, everywhere, with no way back.
    ///
    /// The server goes FIRST and the phone only if the server actually did it,
    /// which is the opposite of `startOver` above and deliberately so. An app
    /// that empties itself and says «удалено» while the server still holds a
    /// person's inner life is a worse falsehood than the one this replaces,
    /// because it looks like it worked. So it returns false and changes
    /// nothing, and the sheet says plainly that nothing was deleted.
    ///
    /// The Keychain token is deliberately kept. There is nothing to invalidate
    /// — the server has only ever stored sha256 of it — so after this it
    /// addresses an empty room, and keeping it is what lets somebody sign up
    /// again on this phone instead of stranding a second bucket on the server.
    func deleteEverything() async -> Bool {
        do {
            try await BackendClient(baseURL: AppConfig.shared.backendURL).deleteEverything()
        } catch {
            Trouble.shared.record(error, url: AppConfig.shared.backendURL)
            return false
        }
        for key in [Keys.account, Keys.subscribed, Keys.story, Keys.wishes,
                    Keys.country, Keys.age, Keys.remembersMe,
                    Keys.companionName, Keys.hasArrived] {
            defaults.removeObject(forKey: key)
        }
        account = nil
        isSubscribed = false
        story = ""; wishes = ""; country = ""; age = ""; companionName = ""
        remembersMe = false
        hasArrived = false
        return true
    }

    /// The server is the one that actually holds the friend, so it is the one
    /// that knows whether there is one. This phone only remembers that
    /// onboarding FINISHED — which stops being the same question the moment
    /// the two can disagree, and they now can:
    ///
    ///   · this build sends a token, so the server looks this person up
    ///     properly instead of handing everyone the one persona it had;
    ///   · a phone that finished onboarding before tokens existed has no
    ///     friend under its new id;
    ///   · someone could point the app at a different server entirely.
    ///
    /// In all three the phone would open straight to a companion screen and
    /// talk to the built-in template character — the 87-year-old by the sea
    /// with the cat Мурзик — which is precisely the "borrowed life" this whole
    /// design exists to prevent. So when the server says there is nobody, the
    /// app goes back to «кого бы вы хотели встретить», the same place «Начать
    /// заново» leads, and they meet someone who is actually theirs.
    ///
    /// It ONLY ever acts on a clear "no". An unreachable server, a timeout, a
    /// wrong address — anything short of the server plainly saying it has no
    /// companion for this person — changes nothing. Losing your friend to a
    /// dropped Wi-Fi packet would be far worse than the problem this solves.
    func reconcileWithServer() async {
        guard hasArrived else { return }
        guard
            var request = try? BackendClient.authorized(
                AppConfig.shared.backendURL.appendingPathComponent("api/health")
            )
        else { return }
        request.timeoutInterval = 10
        request.cachePolicy = .reloadIgnoringLocalCacheData

        guard
            let (data, response) = try? await URLSession.shared.data(for: request),
            let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode),
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let hasCompanion = json["has_companion"] as? Bool,
            hasCompanion == false
        else { return }

        forgetCompanionLocally()
    }

    /// A fallback so a screen never has to say "his name" out loud before he
    /// has arrived.
    var displayName: String {
        companionName.isEmpty ? (Strings.language == .russian ? "Друг" : "Your friend")
                              : companionName
    }
}

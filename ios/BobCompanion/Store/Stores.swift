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

    /// Parting with a friend. Everything HE knew goes with him — but your own
    /// story stays yours, so starting over means choosing who to meet next
    /// rather than retelling your whole life to a stranger.
    func startOver() {
        for key in [Keys.wishes, Keys.companionName, Keys.hasArrived] {
            defaults.removeObject(forKey: key)
        }
        wishes = ""; companionName = ""; hasArrived = false
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

        startOver()
    }

    /// A fallback so a screen never has to say "his name" out loud before he
    /// has arrived.
    var displayName: String {
        companionName.isEmpty ? (Strings.language == .russian ? "Друг" : "Your friend")
                              : companionName
    }
}

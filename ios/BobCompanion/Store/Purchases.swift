// Paying, with StoreKit 2 (report «Экраны защита и скорость фронтенда», stage 3; Apple 3.1.1, 3.1.2).
//
// Two plans in one subscription group, a year with 7 free days and a month. Prices always come from the App Store,
// in the person's own currency, never typed in here. Restore is AppStore.sync(); managing and cancelling is Apple's own
// sheet. A purchase that waits for a parent (Ask to Buy) unlocks nothing until it is approved.
//
// NOT YET (stage 4, the server): the server must check every transaction itself (its signed JWS, through the App Store
// Server API, and App Store Server Notifications V2) before it gives more than the free minutes. The phone's own word
// that it paid must never be enough there.
// For the simulator: BobCompanion/Products.storekit (the scheme uses it), so the paywall works without App Store Connect.

import StoreKit
import SwiftUI

@MainActor
final class Purchases: ObservableObject {
    static let yearID = "bob.year", monthID = "bob.month"

    @Published private(set) var year: Product?
    @Published private(set) var month: Product?
    /// The 7 free days are offered only to someone who has not had them.
    @Published private(set) var trialEligible = false
    /// Paid and current (verified on the phone; the server checks again).
    @Published private(set) var active = false
    /// Bought, but a parent has to approve it first.
    @Published private(set) var waitingForParent = false
    @Published private(set) var busy = false
    @Published var notice: Notice?

    /// What the store last said — kept as what happened, so its words follow a language changed afterwards.
    enum Notice {
        case restored, nothingToRestore, trouble
        var text: String {
            switch self { case .restored: Words.restored; case .nothingToRestore: Words.nothingToRestore; case .trouble: Words.storeTrouble }
        }
    }

    private var updates: Task<Void, Never>?

    init() {
        updates = Task { [weak self] in                                    // renewals, refunds, a parent's yes
            for await result in Transaction.updates {
                if case .verified(let t) = result { await t.finish() }
                await self?.refresh()
            }
        }
        Task { await load() }
    }

    deinit { updates?.cancel() }

    func load() async {
        do {
            let products = try await Product.products(for: [Self.yearID, Self.monthID])
            year = products.first { $0.id == Self.yearID }
            month = products.first { $0.id == Self.monthID }
            trialEligible = await year?.subscription?.isEligibleForIntroOffer ?? false
            if products.isEmpty { notice = .trouble }                       // (no prices came: the buttons cannot work, say why)
        } catch {
            notice = .trouble
        }
        await refresh()
    }

    func buy(_ product: Product) async {
        guard !busy else { return }
        busy = true
        defer { busy = false }
        do {
            switch try await product.purchase() {
            case .success(let result):
                guard case .verified(let transaction) = result else { notice = .trouble; return }
                await transaction.finish()
                await refresh()
            case .pending:
                waitingForParent = true                                    // (Ask to Buy: nothing unlocks yet)
            case .userCancelled:
                break
            @unknown default:
                break
            }
        } catch {
            notice = .trouble
        }
    }

    func restore() async {
        guard !busy else { return }
        busy = true
        defer { busy = false }
        do {
            try await AppStore.sync()
            await refresh()
            notice = active ? .restored : .nothingToRestore
        } catch StoreKitError.userCancelled {
            notice = nil                                                   // (the person closed Apple's sign-in: nothing went wrong)
        } catch {
            notice = .trouble
        }
    }

    func refresh() async {
        var paid = false
        for await result in Transaction.currentEntitlements {
            if case .verified(let t) = result, [Self.yearID, Self.monthID].contains(t.productID), t.revocationDate == nil {
                paid = true
            }
        }
        active = paid
        if paid { waitingForParent = false }
    }
}

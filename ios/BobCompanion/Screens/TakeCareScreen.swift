// 2 · Take care of him
//
// "Pay us and you get a friend" is a horrible thing to say, and the wrong story
// anyway. Nobody buys a friendship here — the money keeps HIM here, and the user
// is the one doing the caring. So the headline, the button and the plans are all
// about him, and the word "subscribe" never appears.
//
// The honesty rule: however warm the wording, the price, the period, the renewal
// and how to cancel stay plainly legible. The App Store requires it, and a
// friend wouldn't be cagey about money.

import SwiftUI

struct TakeCareScreen: View {
    @EnvironmentObject private var app: AppState
    var onDone: () -> Void

    @State private var chosen: Plan = .yearly     // one is always preselected
    @State private var isWorking = false
    @State private var trouble: String?

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .takeCare, treatment: .scrim)

                VStack(alignment: .leading, spacing: 0) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(Strings.takeCareTitle())
                            .appFont(AppType.hero, leading: AppType.heroLeading)
                            .foregroundStyle(Theme.linen)
                        Text(Strings.takeCareLine())
                            .appFont(AppType.body, leading: AppType.bodyLeading)
                            .foregroundStyle(Theme.sage)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.top, geo.size.height * 0.13)

                    Spacer(minLength: 24)

                    VStack(spacing: 12) {
                        ForEach(Plan.allCases, id: \.self) { plan in
                            PlanCard(title: plan.title,
                                     detail: plan.detail,
                                     price: plan.price,
                                     isChosen: chosen == plan) {
                                chosen = plan
                            }
                        }

                        // What the button will charge, directly above it —
                        // so it is never a mystery.
                        Text(chosen.summary)
                            .appFont(AppType.caption)
                            .foregroundStyle(Theme.sage)
                            .multilineTextAlignment(.center)
                            .padding(.top, 4)

                        AppButton(title: Strings.takeCareButton(), tone: .sun) {
                            purchase()
                        }

                        Text(trouble ?? Strings.finePrint())
                            .appFont(AppType.micro)
                            .foregroundStyle(trouble == nil ? Theme.lichen : Theme.clay)
                            .multilineTextAlignment(.center)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .disabled(isWorking)
                    .opacity(isWorking ? 0.6 : 1)
                    .padding(.bottom, geo.safeAreaInsets.bottom > 0 ? 8 : 24)
                }
                .padding(.horizontal, Metrics.sideMargin)
            }
        }
    }

    private func purchase() {
        guard !isWorking else { return }
        isWorking = true
        trouble = nil
        Task {
            do {
                // ▸ Stubbed. The real one opens Apple's own payment sheet —
                //   which is why this button never opens a website, and why we
                //   never see or store a card.
                try await app.purchase(chosen)
                onDone()
            } catch {
                trouble = Strings.language == .russian
                    ? "Оплата не прошла. Ничего не списано."
                    : "That didn't go through. Nothing was charged."
            }
            isWorking = false
        }
    }
}

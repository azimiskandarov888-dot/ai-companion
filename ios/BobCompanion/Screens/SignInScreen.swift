// 1 · Sign in
//
// You open the app and you are standing in a meadow at first light.
//
// The upper two thirds stay untouched sky and hill — that emptiness IS the
// design. One warm line, then the two ways in, all of it in the lower third
// where the thumb reaches. No feature list, no carousel, no "skip".
//
// Returning users never see this screen again; the app opens straight to him.

import SwiftUI

struct SignInScreen: View {
    @EnvironmentObject private var app: AppState
    var onDone: () -> Void

    @State private var isWorking = false
    @State private var trouble: String?

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .signIn, treatment: .scrim)

                VStack(spacing: 0) {
                    // The line sits HIGH — up in the open sky above the tree,
                    // so the tree standing alone on the hill below reads as the
                    // friend the sentence is talking about. It is said in two
                    // breaths, the second arriving after the first has landed.
                    VStack(alignment: .leading, spacing: 2) {
                        Text(Strings.signInLineA())
                            .appFont(AppType.hero, leading: AppType.heroLeading)
                            .foregroundStyle(Theme.linen)
                            .fixedSize(horizontal: false, vertical: true)
                            .legible()
                            .arrive(.first)
                        Text(Strings.signInLineB())
                            .appFont(AppType.hero, leading: AppType.heroLeading)
                            .foregroundStyle(Theme.linen)
                            .fixedSize(horizontal: false, vertical: true)
                            .legible()
                            .arrive(.second)
                    }
                    .frame(maxWidth: 366, alignment: .leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, geo.size.height * 0.13)

                    Spacer()

                    VStack(spacing: 12) {
                        AppButton(title: Strings.continueApple(),
                                  tone: .sun,
                                  icon: Image(systemName: "apple.logo")) {
                            signIn(with: "Apple")
                        }
                        AppButton(title: Strings.continueGoogle(),
                                  tone: .quiet,
                                  icon: Image(systemName: "g.circle")) {
                            signIn(with: "Google")
                        }

                        Button(action: { signIn(with: "email") }) {
                            Text(Strings.orUseEmail())
                                .appFont(AppType.secondary)
                                .foregroundStyle(Theme.onLand)
                                .legible(0.7)
                                .frame(minHeight: Metrics.minTouch)
                        }
                        .buttonStyle(SoftPress())
                    }
                    .arrive(.object, rise: 18)
                    .disabled(isWorking)
                    .opacity(isWorking ? 0.6 : 1)

                    Text(trouble ?? Strings.terms())
                        .appFont(AppType.micro)
                        .foregroundStyle(trouble == nil ? Theme.lichen : Theme.clay)
                        .multilineTextAlignment(.center)
                        .legible(0.7)
                        .padding(.top, 10)
                        .arrive(.footnote)
                        .padding(.bottom, geo.safeAreaInsets.bottom > 0 ? 8 : 24)
                }
                .padding(.horizontal, Metrics.sideMargin)
            }
        }
    }

    private func signIn(with provider: String) {
        guard !isWorking else { return }
        isWorking = true
        trouble = nil
        Task {
            do {
                try await app.signIn(with: provider)
                onDone()
            } catch {
                // Even here, no error codes — just a plain sentence.
                trouble = Strings.language == .russian
                    ? "Не получилось войти. Попробуй ещё раз."
                    : "That didn't work. Try once more."
            }
            isWorking = false
        }
    }
}

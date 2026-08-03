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
                    Spacer()

                    // The warm line sits at y 398 of 932 — above the controls,
                    // below the empty sky. Left-set, not centred: it reads as
                    // something said rather than a headline.
                    Text(Strings.signInLine())
                        .appFont(AppType.hero, leading: AppType.heroLeading)
                        .foregroundStyle(Theme.linen)
                        .frame(maxWidth: 366, alignment: .leading)
                        .fixedSize(horizontal: false, vertical: true)
                        .background(Theme.heroPlate.blur(radius: 24))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.bottom, 40)

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
                                .foregroundStyle(Theme.sage)
                                .frame(minHeight: Metrics.minTouch)
                        }
                        .buttonStyle(SoftPress())

                        Text(trouble ?? Strings.terms())
                            .appFont(AppType.micro)
                            .foregroundStyle(trouble == nil ? Theme.lichen : Theme.clay)
                            .multilineTextAlignment(.center)
                            .padding(.top, 2)
                    }
                    .disabled(isWorking)
                    .opacity(isWorking ? 0.6 : 1)
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

// The journey's three sheets, every button real (report «Экраны защита и скорость фронтенда», stage 3):
//   · keeping in touch — Sign in with Apple (Apple 4.8: offered with Google), Google, and «Позже» (5.1.1: the app works
//     without an account);
//   · the one calm screen to pay — prices from the App Store, the trial only for whom it is eligible, «Не сейчас» as
//     large as the purchase, Restore, Terms and Privacy as real buttons (3.1.2), «Попроси родителей» for a teenager
//     (Ask to Buy);
//   · the menu — subscription (Apple's own sheet to manage or cancel), restore, sign-in, language, help when it is bad,
//     who he is (an AI), the microphone, privacy, terms, and deleting everything (5.1.1(v)).
// NOT YET (stage 4, the server): Sign in with Apple's token checked by the server (with a nonce) and revoked when an
// account is deleted; Google's own SDK; the privacy policy as a page of ours online (an adult writes it with a lawyer);
// crisis lines checked for each country by an adult.

import SwiftUI
import AuthenticationServices
import StoreKit

enum Legal {
    /// Apple's standard licence (EULA), which an app may use as its Terms of Use.
    static let terms = URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!
}

/// Help when it is bad: the number that always works where the person is. (US: 988, the crisis line, and 911; else
/// 112. Each country's own crisis lines are to be checked by an adult before they are added here.)
enum Crisis {
    static var numbers: [String] { Locale.current.region?.identifier == "US" ? ["988", "911"] : ["112"] }
}

private func sheetTitle(_ text: String) -> some View {
    Text(text).font(.system(.title2, design: .serif)).foregroundStyle(Ghost.ink).multilineTextAlignment(.center)
}

// MARK: - 4 · keeping in touch

struct KeepSheet: View {
    @EnvironmentObject private var app: AppState
    let he: Bool
    let done: () -> Void
    @State private var trouble: String?

    var body: some View {
        VStack(spacing: 14) {
            Text(Words.keepWhy(he)).font(.subheadline).foregroundStyle(Ghost.soft).multilineTextAlignment(.center)
            SignInWithAppleButton(.signIn) { request in
                request.requestedScopes = [.fullName]
            } onCompletion: { result in
                switch result {
                case .success:
                    Task { try? await app.signIn(with: "Apple"); done() }
                case .failure(let error):
                    if (error as? ASAuthorizationError)?.code != .canceled { trouble = Words.signInFailed }
                }
            }
            .signInWithAppleButtonStyle(.white)
            .frame(maxWidth: 360, minHeight: 50, maxHeight: 50)
            #if DEBUG
            // (Google's own SDK is not in yet: in a build for people this button would only pretend, so it is shown
            // only while looking — stage 4)
            Button {
                Task { do { try await app.signIn(with: "Google"); done() } catch { trouble = Words.signInFailed } }
            } label: {
                Text(Words.google).font(.body.weight(.medium)).frame(maxWidth: 360, minHeight: 50)
                    .background(Ghost.ink.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
                    .foregroundStyle(Ghost.ink)
            }
            #endif
            Button(Words.later(he), action: done)
                .font(.footnote).foregroundStyle(Ghost.faint).multilineTextAlignment(.center).frame(minHeight: 44)
            if let trouble { Text(trouble).font(.footnote).foregroundStyle(Ghost.soft).multilineTextAlignment(.center) }
        }
        .padding(24)
        .presentationDetents([.height(340), .large])
        .presentationDragIndicator(.visible)
        .presentationBackground(Ghost.shade.opacity(0.92))
    }
}

// MARK: - 5 · the one calm screen to pay

struct PaySheet: View {
    @ObservedObject var store: Purchases
    let he: Bool
    let teen: Bool
    /// Today's free minutes are over (it came by itself); else it was opened from the menu, and says nothing of minutes.
    let rested: Bool
    let done: () -> Void
    @Environment(\.openURL) private var openURL
    @State private var plan = Purchases.yearID
    @State private var privacy = false

    private var chosen: Product? { plan == Purchases.yearID ? store.year : store.month }

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                if rested { Text(Words.payWhy).font(.subheadline).foregroundStyle(Ghost.soft).multilineTextAlignment(.center) }
                sheetTitle(rested ? Words.payTitle(he) : Words.payTitleOpen(he))
                Text(Words.gets(he)).font(.subheadline).foregroundStyle(Ghost.soft).multilineTextAlignment(.center)
                if store.trialEligible && !teen, let year = store.year { timeline(year) }
                HStack(spacing: 10) {
                    planCard(Purchases.yearID, Words.yearly, store.year.map { Words.perYear($0.displayPrice) },
                             store.year.map { Words.perMonth(($0.price/12).formatted($0.priceFormatStyle)) })
                    planCard(Purchases.monthID, Words.monthly, store.month.map { Words.perMonth($0.displayPrice) }, nil)
                }
                // «Не сейчас» exactly as large as the purchase: the person decides, the screen does not push
                HStack(spacing: 10) {
                    Button(Words.notNow, action: done).buttonStyle(PayButton(primary: false))
                    Button(teen ? Words.parents : (store.trialEligible && plan == Purchases.yearID ? Words.tryFree : Words.subscribe)) {
                        if let chosen { Task { await store.buy(chosen) } }
                    }
                    .buttonStyle(PayButton(primary: true))
                    .disabled(chosen == nil || store.busy)
                }
                if store.waitingForParent { Text(Words.waitingParents).font(.footnote).foregroundStyle(Ghost.soft).multilineTextAlignment(.center) }
                Text(Words.renewsNote).font(.caption).foregroundStyle(Ghost.faint).multilineTextAlignment(.center)
                HStack(spacing: 4) {
                    Button(Words.restore) { Task { await store.restore() } }.frame(minHeight: 44)
                    Text("·").foregroundStyle(Ghost.faint)
                    Button(Words.terms) { openURL(Legal.terms) }.frame(minHeight: 44)
                    Text("·").foregroundStyle(Ghost.faint)
                    Button(Words.privacy) { privacy = true }.frame(minHeight: 44)
                }
                .font(.footnote).tint(Ghost.soft)
                Text(Words.ai).font(.caption).foregroundStyle(Ghost.faint)
                if let notice = store.notice { Text(notice.text).font(.footnote).foregroundStyle(Ghost.soft).multilineTextAlignment(.center) }
            }
            .padding(24)
            .frame(maxWidth: 560)
            .frame(maxWidth: .infinity)
        }
        .presentationDetents([.large])
        .presentationBackground(Ghost.shade.opacity(0.94))
        .sheet(isPresented: $privacy) { PrivacyText() }
        .onChange(of: store.active) { _, paid in if paid { done() } }
        .onAppear { store.notice = nil }                                   // (no word left over from another time)
        .task { await store.load() }
    }

    private func timeline(_ year: Product) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            step(Words.d0, Words.d0s, filled: true)
            step(Words.d5, Words.d5s, filled: false)
            step(Words.d7, Words.d7s(year.displayPrice), filled: false)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func step(_ when: String, _ what: String, filled: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Circle().strokeBorder(Ghost.gold, lineWidth: 1.5).background(Circle().fill(filled ? Ghost.gold : .clear)).frame(width: 10, height: 10).padding(.top, 4)
            VStack(alignment: .leading, spacing: 2) {
                Text(when).font(.subheadline.weight(.semibold)).foregroundStyle(Ghost.ink)
                Text(what).font(.subheadline).foregroundStyle(Ghost.faint)
            }
        }
        .accessibilityElement(children: .combine)
    }

    /// The price that is billed is the large one; a per-month figure is smaller (Apple 3.1.2).
    private func planCard(_ id: String, _ title: String, _ price: String?, _ each: String?) -> some View {
        Button { plan = id } label: {
            VStack(spacing: 4) {
                Text(title).font(.subheadline.weight(.medium)).foregroundStyle(Ghost.ink)
                Text(price ?? "—").font(.subheadline).foregroundStyle(Ghost.ink)
                if let each { Text(each).font(.caption).foregroundStyle(Ghost.faint) }
            }
            .frame(maxWidth: .infinity, minHeight: 72)
            .background(plan == id ? Ghost.gold.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(plan == id ? Ghost.gold : Ghost.line))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(plan == id ? .isSelected : [])
    }
}

private struct PayButton: ButtonStyle {
    let primary: Bool
    @Environment(\.isEnabled) private var enabled                       // (no prices from the store: it looks as dead as it is)
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.semibold))
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(primary ? Color(red: 0.16, green: 0.11, blue: 0.06) : Ghost.ink)
            .background(primary ? Ghost.ink : .clear, in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(primary ? Ghost.ink : Ghost.line))
            .opacity(configuration.isPressed ? 0.7 : enabled ? 1 : 0.4)
    }
}

// MARK: - the menu

struct MenuSheet: View {
    @EnvironmentObject private var app: AppState
    @ObservedObject var store: Purchases
    let he: Bool
    let signIn: () -> Void
    let subscribe: () -> Void
    let done: () -> Void
    @Environment(\.openURL) private var openURL
    @AppStorage("appLanguage") private var language = Language.russian.rawValue
    @State private var manage = false
    @State private var confirmDelete = false
    @State private var page: Page?
    @State private var result: String?

    enum Page: String, Identifiable { case privacy, ai, crisis; var id: String { rawValue } }

    var body: some View {
        NavigationStack {
            List {
                Section(Words.subscription) {
                    Text(store.active ? Words.subscribed : Words.notSubscribed).foregroundStyle(.secondary)
                    if store.active { Button(Words.manage) { manage = true } } else { Button(Words.subscribeRow, action: subscribe) }
                    Button(Words.restore) { Task { await store.restore() } }
                    if let notice = store.notice { Text(notice.text).font(.footnote).foregroundStyle(.secondary) }
                }
                Section {
                    if app.account == nil { Button(Words.signIn, action: signIn) } else { Text(Words.signedIn).foregroundStyle(.secondary) }
                }
                Section(Words.language) {
                    Picker(Words.language, selection: $language) {
                        Text("Русский").tag(Language.russian.rawValue)
                        Text("English").tag(Language.english.rawValue)
                    }
                    .pickerStyle(.segmented)
                }
                Section {
                    Button(Words.crisis) { page = .crisis }
                    Button(Words.aboutAI(he)) { page = .ai }
                    Button(Words.microphone) { if let u = URL(string: UIApplication.openSettingsURLString) { openURL(u) } }
                }
                Section {
                    Button(Words.privacy) { page = .privacy }
                    Button(Words.terms) { openURL(Legal.terms) }
                }
                Section {
                    Button(Words.deleteData, role: .destructive) { confirmDelete = true }
                    if let result { Text(result).font(.footnote).foregroundStyle(.secondary) }
                }
            }
            .navigationTitle(Words.menu)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button(Words.close, action: done) } }
        }
        .manageSubscriptionsSheet(isPresented: $manage)
        // (an alert, not a confirmation dialog: on iOS 26 that one comes as a bubble with no «Отмена» in it — and this
        // cannot be undone, so the way back is a button anyone can see)
        .alert(Words.deleteConfirm(he), isPresented: $confirmDelete) {
            Button(Words.cancel, role: .cancel) {}
            Button(Words.delete, role: .destructive) {
                Task {
                    let ok = await app.deleteEverything()
                    result = ok ? Words.deleted : Words.deleteFailed
                    if ok { done() }
                }
            }
        }
        .sheet(item: $page) { which in
            switch which {
            case .privacy: PrivacyText()
            case .ai: TextPage(title: Words.aboutAITitle(he), text: Words.aboutAIText(he))
            case .crisis: CrisisPage()
            }
        }
        .onAppear { store.notice = nil }
        .presentationDetents([.large])
    }
}

/// Help when it is bad: a few words and the numbers, dialled by the person.
struct CrisisPage: View {
    @Environment(\.openURL) private var openURL
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 18) {
                Text(Words.crisisText).font(.body).multilineTextAlignment(.center)
                ForEach(Crisis.numbers, id: \.self) { number in
                    Button { if let u = URL(string: "tel://\(number)") { openURL(u) } } label: {
                        Text(Strings.helpNowCall(number)()).font(.headline).frame(maxWidth: 360, minHeight: 50)
                            .foregroundStyle(Color(red: 0.16, green: 0.11, blue: 0.06))   // (dark on the gold: white on it was hard to read)
                    }
                    .buttonStyle(.borderedProminent)
                }
                Spacer()
            }
            .padding(24)
            .navigationTitle(Words.crisis)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button(Words.close) { dismiss() } } }
        }
    }
}

struct TextPage: View {
    let title: String
    let text: String
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView { Text(text).font(.body).frame(maxWidth: 640, alignment: .leading).padding(24) }
                .navigationTitle(title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button(Words.close) { dismiss() } } }
        }
    }
}

/// The privacy policy, in the app. A DRAFT that says only what the app really does; an adult and a lawyer finish it
/// (152-FZ, GDPR-like rights) and put the same text online for the App Store.
struct PrivacyText: View {
    var body: some View {
        TextPage(title: Words.privacy, text: Strings.language == .russian ? """
        Черновик. Окончательный текст готовит взрослый вместе с юристом.

        Что мы получаем. Твой голос, когда ты говоришь с собеседником: запись уходит на наш сервер, там превращается в \
        текст и не хранится как звук. Текст ваших разговоров и то, что собеседник о тебе помнит. Твой возраст и ответы \
        на вопросы в начале — чтобы подобрать собеседника и беречь подростков. Случайный номер этого телефона, чтобы \
        сервер узнавал тебя. При входе через Apple — имя, которое Apple нам передаст.

        Чего мы не делаем. Не продаём данные, не показываем рекламу, не передаём разговоры другим людям. Модели \
        искусственного интеллекта, которые помогают собеседнику говорить, получают текст разговора только для ответа.

        Что ты можешь. Удалить всё в любой момент: Меню → «Удалить мои данные».
        """ : """
        Draft. The final text is prepared by an adult with a lawyer.

        What we receive. Your voice when you talk with your companion: the recording goes to our server, becomes text \
        there and is not kept as sound. The text of your talks and what your companion remembers about you. Your age and \
        answers to the opening questions, to choose your companion and protect teenagers. A random number for this phone, \
        so the server knows you. If you sign in with Apple, the name Apple gives us.

        What we don't do. We don't sell data, show ads or share your talks with other people. The AI models that help \
        your companion speak receive the text of a talk only to answer.

        What you can do. Delete everything at any time: Menu → “Delete my data”.
        """)
    }
}

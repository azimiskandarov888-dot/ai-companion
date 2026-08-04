// 8 · Settings
//
// Deliberately ordinary, and still standing in the same place. Three small
// groups with air between them instead of one long block; nothing square,
// nothing edge-to-edge. It may be plain, but it is not a flat black screen.
//
// «Start over» is clay, never red, and it opens a slow plain sheet that says
// what will be lost — in his name. Parting with a friend is serious.

import SwiftUI

struct SettingsScreen: View {
    @EnvironmentObject private var app: AppState
    var onClose: () -> Void

    @State private var showStartOver = false
    @State private var showServer = false
    @State private var language = Strings.language

    var body: some View {
        GeometryReader { geo in
            ZStack {
                PhotoBackground(place: .settings, treatment: .blurred(radius: 20, dim: 0.44))

                ScrollView {
                    VStack(alignment: .leading, spacing: Metrics.groupSpacing) {
                        SheetGrabber(onClose: onClose)
                            .padding(.top, 8)

                        Text(Strings.settingsTitle())
                            .appFont(AppType.title)
                            .foregroundStyle(Theme.linen)
                            .padding(.top, geo.size.height * 0.045)

                        // Only what actually does something. His voice,
                        // notifications and the data export were rows that
                        // looked live and did nothing when tapped — which is
                        // worse than not offering them. They come back when
                        // they work.
                        ListGroup {
                            ListRow(label: Strings.rowLanguage(),
                                    value: language.displayName) { toggleLanguage() }
                            ListRow(label: Strings.rowServer(),
                                    value: AppConfig.shared.backendURLString,
                                    showsDivider: false) { showServer = true }
                        }

                        // Parting, and the version
                        ListGroup {
                            ListRow(label: Strings.rowStartOver(),
                                    value: "›",
                                    tone: Theme.clay) { showStartOver = true }
                            ListRow(label: Strings.rowAbout(),
                                    value: AppInfo.version,
                                    showsDivider: false)
                        }
                    }
                    .padding(.horizontal, Metrics.sideMargin)
                    .padding(.bottom, 40)
                }
            }
        }
        .gesture(
            DragGesture(minimumDistance: 60)
                .onEnded { if $0.translation.height > 80 { onClose() } }
        )
        .sheet(isPresented: $showServer) { ServerSheet() }
        .sheet(isPresented: $showStartOver) {
            StartOverSheet(name: app.displayName) {
                app.startOver()
                showStartOver = false
                onClose()
            }
        }
    }

    private func toggleLanguage() {
        language = language == .russian ? .english : .russian
        Strings.language = language
    }
}

// MARK: - Parting with a friend

private struct StartOverSheet: View {
    let name: String
    var onConfirm: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Theme.night.ignoresSafeArea()
            VStack(alignment: .leading, spacing: 22) {
                Spacer()
                Text(Strings.rowStartOver())
                    .appFont(AppType.title)
                    .foregroundStyle(Theme.linen)
                Text(Strings.startOverBody(name)())
                    .appFont(AppType.body, leading: AppType.bodyLeading)
                    .foregroundStyle(Theme.sage)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer()
                VStack(spacing: 12) {
                    // The destructive action is the QUIET one here. Nothing
                    // gold, nothing red — you shouldn't be nudged into it.
                    AppButton(title: Strings.startOverConfirm(),
                              tone: .quiet,
                              labelColour: Theme.clay) { onConfirm() }
                    AppButton(title: Strings.cancel(), tone: .leaf) { dismiss() }
                }
            }
            .padding(.horizontal, Metrics.sideMargin)
            .padding(.bottom, 28)
        }
        .presentationDetents([.medium])
        .presentationCornerRadius(Metrics.sheetRadius)
    }
}

// MARK: - Where the backend lives

private struct ServerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var address = AppConfig.shared.backendURLString

    var body: some View {
        ZStack {
            Theme.night.ignoresSafeArea()
            VStack(alignment: .leading, spacing: 18) {
                Text(Strings.rowServer())
                    .appFont(AppType.title)
                    .foregroundStyle(Theme.linen)
                    .padding(.top, 28)

                TextField("http://192.168.1.50:8000", text: $address)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .appFont(AppType.body)
                    .foregroundStyle(Theme.linen)
                    .padding(.horizontal, 16)
                    .frame(minHeight: Metrics.rowHeight)
                    .panel()

                Text(Strings.language == .russian
                     ? "Пока вы тестируете — это адрес вашего Mac в той же сети Wi-Fi."
                     : "While you're testing, this is your Mac's address on the same Wi-Fi.")
                    .appFont(AppType.caption)
                    .foregroundStyle(Theme.lichen)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer()
                AppButton(title: Strings.done(), tone: .leaf) {
                    AppConfig.shared.backendURLString =
                        address.trimmingCharacters(in: .whitespacesAndNewlines)
                    dismiss()
                }
                .padding(.bottom, 24)
            }
            .padding(.horizontal, Metrics.sideMargin)
        }
        .presentationDetents([.medium])
        .presentationCornerRadius(Metrics.sheetRadius)
    }
}

enum AppInfo {
    /// The app's own name lives here and nowhere else — renaming is one line.
    static let displayName = "Bob"
    static var version: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        return "v\(v)"
    }
}

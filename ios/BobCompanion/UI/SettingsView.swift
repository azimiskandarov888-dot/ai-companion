// A setup screen for YOU (the family), not for him. Reached by long-pressing the
// face. The only thing to set is the backend address — where the app sends his
// voice. No secrets here; the API keys live on the backend.

import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var backendURL = AppConfig.shared.backendURLString
    @State private var sessionID = AppConfig.shared.sessionID

    var body: some View {
        NavigationStack {
            Form {
                Section("Адрес сервера") {
                    TextField("http://192.168.1.50:8000", text: $backendURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    Text("Пока тестируете — это адрес вашего Mac в той же сети Wi-Fi. "
                         + "Для постоянной работы — адрес вашего сервера.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("Память") {
                    TextField("default", text: $sessionID)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Text("Одно имя = одна общая память. Обычно менять не нужно.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            // Settings is deliberately the one ordinary screen — a native grouped
            // list. It just wears the same forest colors as everything else.
            .scrollContentBackground(.hidden)
            .background(Theme.night)
            .navigationTitle("Настройки")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Готово") {
                        AppConfig.shared.backendURLString =
                            backendURL.trimmingCharacters(in: .whitespacesAndNewlines)
                        AppConfig.shared.sessionID =
                            sessionID.trimmingCharacters(in: .whitespacesAndNewlines)
                        dismiss()
                    }
                }
            }
            .tint(Theme.sun400)
        }
        .preferredColorScheme(.dark)
    }
}

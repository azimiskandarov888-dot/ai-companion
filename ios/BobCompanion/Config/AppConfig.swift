// Where the app finds the backend, plus the tunable "feel" of the conversation.
//
// Nothing secret lives here — no API keys. The keys all live on the backend
// server (see backend/app/config.py). This app only needs to know the backend's
// address on the network.

import Foundation

final class AppConfig {
    static let shared = AppConfig()
    private let defaults = UserDefaults.standard

    private enum Keys {
        static let backendURL = "backendURL"
        static let sessionID = "sessionID"
    }

    /// The backend address. During testing this is your Mac's IP on the same
    /// Wi-Fi (e.g. http://192.168.1.50:8000). For 24/7 use, a hosted server.
    /// Editable from the hidden Settings screen (long-press the face).
    var backendURLString: String {
        get { defaults.string(forKey: Keys.backendURL) ?? "http://192.168.1.50:8000" }
        set { defaults.set(newValue, forKey: Keys.backendURL) }
    }

    var backendURL: URL {
        URL(string: backendURLString) ?? URL(string: "http://localhost:8000")!
    }

    /// One elder, one ongoing memory. Kept stable so the backend threads his
    /// whole history together.
    var sessionID: String {
        get { defaults.string(forKey: Keys.sessionID) ?? "default" }
        set { defaults.set(newValue, forKey: Keys.sessionID) }
    }

    // --- Conversation feel (see docs/ALWAYS-ON.md "Conversation flow") ----------

    /// A pause longer than this (seconds) ends his utterance and sends it.
    /// He is old and slow — keep this generous so he isn't cut off mid-sentence.
    var silenceHang: TimeInterval = 1.4

    /// Loudness (dBFS) above which we count audio as speech, not room noise.
    /// Less negative = stricter. Tune on his real device and room.
    var speechThreshold: Float = -35

    /// Hard cap on a single utterance, so a cough or long silence can't record
    /// forever.
    var maxUtterance: TimeInterval = 25
}

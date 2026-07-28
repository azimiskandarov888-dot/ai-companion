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
    //
    // Two kinds of pause in a hands-free chat:
    //
    //   Bob speaks ─▶│◀── BEFORE ──▶│ he speaks │◀── AFTER ──▶│ Bob speaks
    //                 (long: give      (he talks)   (short: reply
    //                  him time to                   promptly)
    //                  start)
    //
    // BEFORE is LONG — he's old and needs time to gather his thoughts, so never
    // rush him into speaking. AFTER is SHORT — once he's clearly finished, Bob
    // answers promptly without an awkward wait.

    /// BEFORE — after Bob finishes, how long to keep waiting patiently for him to
    /// begin. Long on purpose. (The loop keeps re-listening past this, so he is
    /// never cut off for taking his time; this just paces each listen cycle.)
    var beginSpeakingPatience: TimeInterval = 60

    /// AFTER — once he has started talking and then goes quiet, how little
    /// silence means "he's finished" so Bob can answer. Short — but not so short
    /// it clips him between words. Tune on his real voice.
    var endOfSpeechSilence: TimeInterval = 1.2

    /// Loudness (dBFS) above which we count audio as speech, not room noise.
    /// Less negative = stricter. Tune on his real device and room.
    var speechThreshold: Float = -35

    /// Hard cap on a single utterance, so a cough or long silence can't record
    /// forever.
    var maxUtterance: TimeInterval = 25
}

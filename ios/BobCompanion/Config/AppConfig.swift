// Where the app finds the backend, who this phone is, and the tunable "feel"
// of the conversation.
//
// No API keys live here. They are all on the backend server (see
// backend/app/config.py). The one secret this app holds is the token below —
// which is not a key to anything shared, only to this person's own friend.

import Foundation
import Security

final class AppConfig {
    static let shared = AppConfig()
    private let defaults = UserDefaults.standard

    private enum Keys {
        static let backendURL = "backendURL"
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

    // ═══════════════════════════════════════════════════════════════════════
    // WHO THIS PHONE IS
    //
    // 32 random bytes, made once, kept in the Keychain, sent on every request
    // as `Authorization: Bearer <token>`. The server hashes it and that hash
    // is the person (see backend/app/identity.py). No login, no password, no
    // account to remember — because the people this is for cannot be asked to
    // remember one, and every account screen is a place to give up at.
    //
    // It replaces `sessionID`, which was the literal string "default" on every
    // device ever built. Two phones on one server were therefore one person:
    // the second phone met the first phone's friend and picked up their
    // conversation mid-thread.
    // ═══════════════════════════════════════════════════════════════════════

    /// This person's identity, or nil if the Keychain could not be read.
    ///
    /// Nil is deliberately distinct from "make a new one". A transient
    /// Keychain failure that minted a fresh token would quietly lose the
    /// friend and everything he remembers; sending no token at all would drop
    /// this person into the pre-multi-user data, i.e. somebody else's life. A
    /// turn that fails is recoverable — the app already knows how to say he
    /// couldn't come. A wrong identity is not recoverable.
    ///
    /// Resolved once, in `init`, rather than lazily: `shared` is reached from
    /// several tasks at once, and a racing `lazy var` can run its initialiser
    /// twice — where the second run's SecItemAdd fails as a duplicate and
    /// hands somebody a nil identity for the rest of the launch.
    let userToken: String?

    private init() {
        userToken = Self.loadOrCreateToken()
    }

    /// Keychain coordinates. `service` is what the item is FOR; `account` is
    /// which one — there is only ever one.
    private static let tokenService = "com.bob.companion.identity"
    private static let tokenAccount = "friend-token"

    private static func loadOrCreateToken() -> String? {
        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: tokenService,
            kSecAttrAccount as String: tokenAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        if status == errSecSuccess {
            guard
                let data = item as? Data,
                let token = String(data: data, encoding: .utf8),
                !token.isEmpty
            else { return nil }
            return token
        }

        // ONLY "there is nothing stored" may create a new identity. Any other
        // error (the device hasn't been unlocked since boot, the Keychain is
        // busy) means we don't KNOW whether this person already has a friend,
        // and guessing wrong costs them one.
        guard status == errSecItemNotFound else { return nil }

        let token = randomToken()
        query.removeValue(forKey: kSecReturnData as String)
        query.removeValue(forKey: kSecMatchLimit as String)
        query[kSecValueData as String] = Data(token.utf8)
        // AfterFirstUnlock, not WhenUnlocked: the App Intent that lets him
        // speak from a locked phone runs in the background and must be able to
        // read this. Not a ...ThisDeviceOnly variant either — those are left
        // out of encrypted backups, and someone restoring a new iPhone from a
        // backup should find their friend still there.
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        // Deliberately NOT synchronizable (iCloud Keychain). It would be a
        // lovely way to carry the friend to a new phone — but among the people
        // this app is for, a son setting up both parents' phones with HIS
        // Apple ID is ordinary, and syncing would hand those two phones one
        // shared friend. That is the exact bug this token exists to end.

        guard SecItemAdd(query as CFDictionary, nil) == errSecSuccess else { return nil }
        return token
    }

    /// 256 bits from the OS CSPRNG, in base64url so it is safe in an HTTP
    /// header with nothing to escape.
    private static func randomToken() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        if SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) != errSecSuccess {
            // SecRandomCopyBytes does not fail in practice; if it ever did,
            // UUIDs are still 122 bits of OS randomness and a great deal
            // better than a predictable fallback.
            return (UUID().uuidString + UUID().uuidString).replacingOccurrences(of: "-", with: "")
        }
        return Data(bytes).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
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

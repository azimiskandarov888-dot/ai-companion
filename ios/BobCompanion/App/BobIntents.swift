// THE TEST THAT GATES EVERYTHING HANDS-FREE.
//
// The question: when the app is CLOSED and someone says his name, can he answer
// out loud IN HIS OWN VOICE — or does only Siri's voice come out?
//
// It matters more than it sounds. Siri's Russian voice would work reliably and
// would destroy the entire premise: the app's one law is that he must never feel
// like AI, and nothing announces "this is a machine" faster than a friend who
// speaks in the system assistant's voice. If his own voice can't come out of the
// background, then hands-free-anywhere is a lesser feature and the docked-at-home
// mode becomes the main experience — a different product shape, decided by this
// one answer.
//
// WHY IT MIGHT NOT WORK. Two Apple rules are in tension. Background audio is a
// permitted task, so an app is *allowed* to speak while backgrounded. But an
// intent launched with `openAppWhenRun = false` runs in a short-lived process
// that iOS may suspend the moment `perform()` returns — and audio started from
// that process has documented reliability quirks. Nothing here is guaranteed by
// the documentation, which is exactly why it has to be run on real hardware.
//
// THE SIMULATOR CANNOT ANSWER THIS. It has a different audio stack and different
// process lifecycle rules. Only a real iPhone counts.
//
// HOW TO READ THE RESULT
//   · his warm voice, app never opens  → build everything around this
//   · Siri's voice reading his words   → the words work, the voice doesn't
//   · silence, or the app opens        → hands-free anywhere is off the table
//
// See docs/BACKGROUND-VOICE-TEST.md for how to run it.

import AppIntents
import AVFoundation
import Foundation

// MARK: - 1 · The decisive test: one fixed line, in his voice

/// Says one known sentence and nothing else. Deliberately the simplest possible
/// version — no network round trip for the brain, no speech recognition, no
/// conversation. If this doesn't produce his voice, nothing more elaborate will.
struct SpeakInHisVoiceIntent: AppIntent {
    static var title: LocalizedStringResource = "Проверка голоса"
    static var description = IntentDescription(
        "Говорит одну фразу его голосом, не открывая приложение."
    )

    /// The whole point. `true` here would open the app and prove nothing.
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let line = "Я здесь. Слышишь меня?"

        do {
            let spoken = try await BackgroundVoice.speak(line)
            // The dialog is what Siri shows/says. When his own audio played we
            // keep it silent-ish and short, so his voice is the thing heard.
            //
            // `line` is a String VARIABLE here, not a literal token in this
            // call — Swift's string-literal sugar for IntentDialog only kicks
            // in for an actual literal written at the call site, so passing a
            // variable needs the explicit stringLiteral: label.
            return .result(dialog: IntentDialog(stringLiteral: spoken ? "" : line))
        } catch {
            // Falling back to the dialog means SIRI speaks the line. That is a
            // meaningful result, not a failure — write it down.
            return .result(dialog: IntentDialog(stringLiteral: line))
        }
    }
}

// MARK: - 2 · The real thing: say something, he answers

/// The shape the product actually needs: they speak, the backend thinks, he
/// replies in his own voice — with the app never appearing.
struct TalkToBobIntent: AppIntent {
    static var title: LocalizedStringResource = "Поговорить"
    static var description = IntentDescription(
        "Скажи что-нибудь — он ответит своим голосом, не открывая приложение."
    )
    static var openAppWhenRun: Bool = false

    @Parameter(title: "Что сказать", requestValueDialog: "Что ты хочешь сказать?")
    var said: String

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let reply = try await BackgroundVoice.ask(said)

        guard !reply.text.isEmpty else {
            return .result(dialog: IntentDialog("Сейчас я тебя не слышу."))
        }

        if let audio = reply.audio, await BackgroundVoice.play(audio) {
            return .result(dialog: IntentDialog(""))   // his voice already said it
        }

        // No audio came back, or it wouldn't play from the background: Siri
        // reads the words instead. The conversation works; the voice doesn't.
        return .result(dialog: IntentDialog(stringLiteral: reply.text))
    }
}

// MARK: - The phrases

/// What can be said to start these. An App Shortcut phrase MUST contain the app
/// name, so with the app called «Боб» the phrase is simply his name.
///
/// For truly hands-free use — no "Привет, Siri" at all — record a **Vocal
/// Shortcut** (Настройки → Универсальный доступ → Голосовые команды) pointing at
/// one of these. That works with the phone locked and runs entirely on-device.
struct BobShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: SpeakInHisVoiceIntent(),
            phrases: [
                "Проверка голоса \(.applicationName)",
                "\(.applicationName) ты здесь",
            ],
            shortTitle: "Проверка голоса",
            systemImageName: "waveform"
        )
        AppShortcut(
            intent: TalkToBobIntent(),
            phrases: [
                "Поговорить с \(.applicationName)",
                "Сказать \(.applicationName)",
            ],
            shortTitle: "Поговорить",
            systemImageName: "bubble.left.and.bubble.right"
        )
    }
}

// MARK: - Speaking from a background process

enum BackgroundVoice {

    struct Reply {
        let text: String
        let audio: Data?
    }

    /// Ask the backend to say a line, and play whatever audio comes back.
    /// Returns true only if his own audio actually played.
    static func speak(_ line: String) async throws -> Bool {
        let reply = try await ask(line, asRawText: true)
        guard let audio = reply.audio else { return false }
        return await play(audio)
    }

    /// One turn through the backend. `asRawText` sends the line to be spoken
    /// verbatim rather than answered — used by the fixed-line test.
    static func ask(_ text: String, asRawText: Bool = false) async throws -> Reply {
        var request = try BackendClient.authorized(
            AppConfig.shared.backendURL.appendingPathComponent("api/say")
        )
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "text": text,
            "verbatim": asRawText,
        ])
        // Short: a background intent does not get long to live, and a hang here
        // is indistinguishable from a failure anyway.
        request.timeoutInterval = 12

        let (data, _) = try await URLSession.shared.data(for: request)
        let decoded = try JSONDecoder().decode(SayResponse.self, from: data)

        return Reply(
            text: decoded.reply,
            audio: decoded.audioBase64.flatMap { Data(base64Encoded: $0) }
        )
    }

    /// Play audio from a background process, and WAIT for it to finish.
    ///
    /// The waiting is the important part. If `perform()` returns while audio is
    /// still playing, iOS is free to suspend the process and the sound stops
    /// mid-word — which looks exactly like "background audio doesn't work" but
    /// isn't. Returns false if it never started.
    @MainActor
    static func play(_ data: Data) async -> Bool {
        let session = AVAudioSession.sharedInstance()
        do {
            // .playback, NOT .playAndRecord — this process only speaks, and
            // .playback is the category iOS permits in the background.
            // .duckOthers so a film or music quietens rather than stopping.
            try session.setCategory(.playback, mode: .spokenAudio, options: [.duckOthers])
            try session.setActive(true, options: [])
        } catch {
            return false
        }

        defer { try? session.setActive(false, options: [.notifyOthersOnDeactivation]) }

        let player = AudioPlayer()
        guard (try? AVAudioPlayer(data: data)) != nil else { return false }
        await player.play(data: data)
        return true
    }
}

private struct SayResponse: Decodable {
    let reply: String
    let audioBase64: String?

    enum CodingKeys: String, CodingKey {
        case reply
        case audioBase64 = "audio_base64"
    }
}

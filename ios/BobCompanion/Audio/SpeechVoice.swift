// The iPhone's own built-in voice, used when the backend sends no audio (the
// MVP path: no voice key → the client speaks for free). This mirrors what
// the browser test page does with the browser's free voice, so Bob is never
// silent. Configure the backend voice (Fish Audio) and it sends real warm audio
// instead, and this isn't used.

import AVFoundation

@MainActor
final class SpeechVoice: NSObject, AVSpeechSynthesizerDelegate {

    private let synthesizer = AVSpeechSynthesizer()
    private var continuation: CheckedContinuation<Void, Never>?

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    /// How something sounds. Two of them, and the difference is the point.
    enum Character {
        /// Standing in for HIM when the server sent no audio. As human as this
        /// synthesiser gets: the best voice installed, ordinary pitch.
        case standingInForHim
        /// The setup robot, and it must never be mistaken for him. Lower than
        /// a person speaks, and deliberately the COMPACT voice rather than the
        /// enhanced one — the compact voices are the older, flatter, more
        /// obviously synthesised ones, which everywhere else would be a defect
        /// and here is the entire brief.
        case machine

        var pitch: Float { self == .machine ? 0.72 : 1.0 }
        var rate: Float { self == .machine ? 0.43 : 0.45 }
    }

    /// Speak the text aloud (Russian) and return only when it finishes.
    func speak(_ text: String, as character: Character = .standingInForHim) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            self.continuation = continuation
            let utterance = AVSpeechUtterance(string: trimmed)
            utterance.voice = Self.voice(for: character)
            // Both are slower than default (0.5) — kinder for an elderly
            // listener, and on the robot it also reads as unbothered.
            utterance.rate = character.rate
            utterance.pitchMultiplier = character.pitch
            synthesizer.speak(utterance)
        }
    }

    /// Pick a voice of the right kind IN THE APP'S LANGUAGE, falling back the
    /// moment the wanted one isn't installed — which happens often, because
    /// the enhanced voices are a download most people never make.
    ///
    /// The language used to be hard-coded to Russian, which meant switching
    /// the app to English left every spoken word coming out in a Russian
    /// accent reading English spelling. Nobody would have found that by
    /// reading the code; it only shows up the first time somebody tests in
    /// the other language.
    private static func voice(for character: Character) -> AVSpeechSynthesisVoice? {
        let code = Strings.language == .russian ? "ru" : "en"
        let fallback = AVSpeechSynthesisVoice(
            language: Strings.language == .russian ? "ru-RU" : "en-US")

        let candidates = AVSpeechSynthesisVoice.speechVoices()
            .filter { $0.language.hasPrefix(code) }
        guard !candidates.isEmpty else { return fallback }

        let wanted: AVSpeechSynthesisVoiceQuality =
            character == .machine ? .default : .enhanced
        return candidates.first { $0.quality == wanted }
            ?? candidates.first
            ?? fallback
    }

    /// Stop immediately (e.g. the app leaving the screen).
    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        finish()
    }

    private func finish() {
        continuation?.resume()
        continuation = nil
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                       didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in self.finish() }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                       didCancel utterance: AVSpeechUtterance) {
        Task { @MainActor in self.finish() }
    }
}

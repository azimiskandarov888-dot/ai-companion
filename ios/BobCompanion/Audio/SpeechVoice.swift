// The iPhone's own built-in voice, used when the backend sends no audio (the
// MVP path: no ElevenLabs key → the client speaks for free). This mirrors what
// the browser test page does with the browser's free voice, so Bob is never
// silent. Add an ElevenLabs key on the backend and it sends real warm audio
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

    /// Speak the text aloud (Russian) and return only when it finishes.
    func speak(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            self.continuation = continuation
            let utterance = AVSpeechUtterance(string: trimmed)
            utterance.voice = AVSpeechSynthesisVoice(language: "ru-RU")
            // A touch slower than default (0.5) — kinder for an elderly listener.
            utterance.rate = 0.45
            synthesizer.speak(utterance)
        }
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

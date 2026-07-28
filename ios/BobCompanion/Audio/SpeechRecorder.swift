// Records one thing he says, and knows when he's finished.
//
// It watches the microphone loudness. When he starts talking it records; when he
// goes quiet for a moment (AppConfig.endOfSpeechSilence) it stops and hands back the
// audio file. If nobody speaks for a while it reports a quiet timeout so the
// conversation loop can keep waiting patiently.
//
// This is simple voice-activity detection by loudness — no wake word yet. The
// "Боб" wake word (so Bob only answers when called, and ignores the rest of the
// room) is the next layer: see ios/docs/WAKE-WORD.md.

import AVFoundation

@MainActor
final class SpeechRecorder {

    enum Outcome {
        case utterance(URL)     // he said something — here's the recording
        case quietTimeout       // nobody spoke within `beginSpeakingPatience`
        case failed(String)     // couldn't record
    }

    private var recorder: AVAudioRecorder?

    /// Listen until he finishes an utterance, or until the "before" patience
    /// (AppConfig.beginSpeakingPatience) of silence passes with no speech. The
    /// conversation loop just calls this again on a quiet timeout, so he is never
    /// rushed into speaking.
    func captureUtterance() async -> Outcome {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("utterance-\(UUID().uuidString).m4a")

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16_000,          // plenty for speech; small files
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.medium.rawValue,
        ]

        do {
            let recorder = try AVAudioRecorder(url: url, settings: settings)
            recorder.isMeteringEnabled = true
            guard recorder.record() else {
                return .failed("Не удалось начать запись")
            }
            self.recorder = recorder
        } catch {
            return .failed(error.localizedDescription)
        }

        let config = AppConfig.shared
        let tick: TimeInterval = 0.1
        var elapsed: TimeInterval = 0
        var speechElapsed: TimeInterval = 0
        var silenceElapsed: TimeInterval = 0
        var heardSpeech = false

        while true {
            try? await Task.sleep(nanoseconds: UInt64(tick * 1_000_000_000))

            if Task.isCancelled {
                cancel()
                try? FileManager.default.removeItem(at: url)
                return .quietTimeout
            }
            guard let recorder = self.recorder else {
                return .failed("Запись прервана")
            }

            recorder.updateMeters()
            let power = recorder.averagePower(forChannel: 0)
            elapsed += tick

            if power > config.speechThreshold {
                heardSpeech = true
                silenceElapsed = 0
            } else {
                silenceElapsed += tick
            }

            if heardSpeech {
                speechElapsed += tick
                // AFTER (short): he paused long enough → utterance done. Or the
                // safety cap on a very long utterance.
                if silenceElapsed >= config.endOfSpeechSilence || speechElapsed >= config.maxUtterance {
                    finishRecorder()
                    return .utterance(url)
                }
            } else if elapsed >= config.beginSpeakingPatience {
                // BEFORE (long): he hasn't started yet. Give up this cycle; the
                // loop calls us again, so he still has all the time he needs.
                finishRecorder()
                try? FileManager.default.removeItem(at: url)
                return .quietTimeout
            }
        }
    }

    /// Stop and discard the current recording (e.g. when the app leaves screen).
    func cancel() {
        finishRecorder()
    }

    private func finishRecorder() {
        recorder?.stop()
        recorder = nil
    }
}

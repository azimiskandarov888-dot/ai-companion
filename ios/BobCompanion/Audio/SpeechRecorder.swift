// Records one thing he says, and knows when he's finished.
//
// It watches the microphone loudness. When he starts talking it records; when he
// goes quiet for a moment (AppConfig.silenceHang) it stops and hands back the
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
        case quietTimeout       // nobody spoke within `idleTimeout`
        case failed(String)     // couldn't record
    }

    private var recorder: AVAudioRecorder?

    /// Listen until he finishes an utterance, or until `idleTimeout` of silence.
    /// - Parameter idleTimeout: how long to wait in silence before giving up this
    ///   round (the loop just calls again, so this only controls responsiveness).
    func captureUtterance(idleTimeout: TimeInterval = 30) async -> Outcome {
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
                // He paused long enough, or hit the safety cap → utterance done.
                if silenceElapsed >= config.silenceHang || speechElapsed >= config.maxUtterance {
                    finishRecorder()
                    return .utterance(url)
                }
            } else if elapsed >= idleTimeout {
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

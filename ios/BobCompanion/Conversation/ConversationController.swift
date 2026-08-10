// The heart of the app: the listen → think → speak loop.
//
//   👂 record what he says  →  ☁️ send to backend  →  🗣️ play Bob's reply  →  repeat
//
// He always speaks first; Bob only ever responds. The loop is turn-based on
// purpose (Bob doesn't listen while he's talking), which keeps it simple and
// stops Bob answering his own voice.

import Foundation
import SwiftUI

@MainActor
final class ConversationController: ObservableObject {

    enum Status: Equatable {
        case idle            // not running (off screen)
        case listening       // waiting for / hearing him
        case thinking        // backend is working
        case speaking        // playing Bob's reply
        case problem(String) // something went wrong; loop keeps trying
        /// He dozed off — nothing has sounded like a conversation for a while,
        /// which is what a room with a television sounds like. A tap wakes him.
        case asleep
        /// He's talked out for today. Not an error, and not a paywall: he says
        /// it himself and means it. Tomorrow he's fine.
        case restedForToday
    }

    @Published private(set) var status: Status = .idle
    /// The last thing Bob said. He can't read it — it's for you, to watch the
    /// conversation while testing.
    @Published private(set) var lastReply: String = ""
    @Published private(set) var lastHeard: String = ""

    private let recorder = SpeechRecorder()
    private let player = AudioPlayer()      // plays real audio from the backend (Fish Audio)
    private let voice = SpeechVoice()        // free on-device voice when no backend audio
    private var loop: Task<Void, Never>?

    private var client: BackendClient {
        BackendClient(baseURL: AppConfig.shared.backendURL)
    }

    // MARK: lifecycle

    func start() {
        guard loop == nil else { return }
        loop = Task { await run() }
    }

    func stop() {
        loop?.cancel()
        loop = nil
        recorder.cancel()
        player.stop()
        voice.stop()
        AudioSessionManager.deactivate()
        status = .idle
    }

    // MARK: the loop

    private func run() async {
        guard await AudioSessionManager.requestMicPermission() else {
            status = .problem("Нужен доступ к микрофону")
            return
        }
        do {
            try AudioSessionManager.configureForConversation()
        } catch {
            status = .problem("Аудио недоступно")
            return
        }

        while !Task.isCancelled {
            status = .listening
            let outcome = await recorder.captureUtterance()
            if Task.isCancelled { break }

            switch outcome {
            case .quietTimeout:
                continue  // keep waiting patiently — this is fine

            case .failed(let message):
                status = .problem(message)
                try? await Task.sleep(nanoseconds: 2_000_000_000)

            case .utterance(let fileURL):
                await handle(fileURL)
            }
        }

        status = .idle
    }

    /// Someone tapped him. He opens his eyes and the loop starts again.
    /// Waking never gives back time that's been spent — the server decides.
    func wake() {
        guard status == .asleep else { return }
        Task {
            try? await client.wake()
            start()
        }
    }

    private func handle(_ fileURL: URL) async {
        defer { try? FileManager.default.removeItem(at: fileURL) }

        status = .thinking
        do {
            let response = try await client.talk(
                audioFileURL: fileURL,
                sessionID: AppConfig.shared.sessionID
            )
            Trouble.shared.clear()   // a turn got through; whatever it was, it's past

            // The server decides whether he answers, and it has already
            // decided. It says so in his own words — we just stop listening
            // and show it.
            switch response.state {
            case "asleep":
                lastReply = response.reply
                status = .asleep
                stop()
                return
            case "daily_limit":
                lastReply = response.reply
                status = .restedForToday
                stop()
                return
            default:
                break
            }

            // Whisper heard nothing usable — just go back to listening.
            guard !response.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                return
            }
            lastHeard = response.transcript
            lastReply = response.reply

            // Speak Bob's reply. If the backend sent real audio (Fish Audio),
            // play it; otherwise (MVP, no voice key) speak it with the free
            // on-device voice — exactly like the browser does. Never stay silent.
            if let audio = decodedAudio(from: response) {
                status = .speaking
                await player.play(data: audio)
            } else if !response.reply.isEmpty {
                status = .speaking
                await voice.speak(response.reply)
            }
        } catch {
            // He still only ever says «не слышит» — the screen shows nothing
            // else and never will. But the real reason is written down, once,
            // where a tester can find it: Настройки → Сервер. Without this,
            // three unrelated problems with three unrelated fixes all present
            // as the same two words.
            Trouble.shared.record(error, url: client.baseURL.appendingPathComponent("api/talk"))
            status = .problem(error.localizedDescription)
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
    }

    /// Real audio from the backend, or nil if it sent none (an empty string is
    /// the MVP path with no voice key → we speak with the on-device voice).
    private func decodedAudio(from response: TalkResponse) -> Data? {
        guard let base64 = response.audioBase64,
              !base64.isEmpty,
              let data = Data(base64Encoded: base64),
              !data.isEmpty else { return nil }
        return data
    }
}

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
    }

    @Published private(set) var status: Status = .idle
    /// The last thing Bob said. He can't read it — it's for you, to watch the
    /// conversation while testing.
    @Published private(set) var lastReply: String = ""
    @Published private(set) var lastHeard: String = ""

    private let recorder = SpeechRecorder()
    private let player = AudioPlayer()
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

    private func handle(_ fileURL: URL) async {
        defer { try? FileManager.default.removeItem(at: fileURL) }

        status = .thinking
        do {
            let response = try await client.talk(
                audioFileURL: fileURL,
                sessionID: AppConfig.shared.sessionID
            )

            // Whisper heard nothing usable — just go back to listening.
            guard !response.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                return
            }
            lastHeard = response.transcript
            lastReply = response.reply

            if let base64 = response.audioBase64,
               let audio = Data(base64Encoded: base64) {
                status = .speaking
                await player.play(data: audio)
            }
        } catch {
            status = .problem(error.localizedDescription)
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
    }
}

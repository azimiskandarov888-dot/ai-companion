// Sets up the phone's audio so Bob can both listen and speak, and asks once for
// microphone permission.

import AVFoundation

enum AudioSessionManager {

    /// Configure for a hands-free conversation on a docked device:
    /// - `.playAndRecord` so we can record him and play Bob in the same session.
    /// - `.spokenAudio` — tuned for voice, not music.
    /// - `.defaultToSpeaker` so Bob comes out of the loudspeaker (he's across the
    ///   room, not holding the phone to his ear).
    /// - `.duckOthers` so anything else playing quiets down when Bob speaks.
    static func configureForConversation() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(
            .playAndRecord,
            mode: .spokenAudio,
            options: [.defaultToSpeaker, .duckOthers, .allowBluetoothHFP, .allowBluetoothA2DP]
        )
        try session.setActive(true, options: [])
    }

    /// Release the audio session (when the app leaves the screen).
    static func deactivate() {
        try? AVAudioSession.sharedInstance().setActive(false, options: [.notifyOthersOnDeactivation])
    }

    /// Ask for microphone access. iOS shows the system prompt the first time;
    /// after that this returns the stored answer immediately.
    ///
    /// ── WHY THIS IS MORE THAN ONE LINE ──────────────────────────────────
    ///
    /// TWO things ask, at the same moment, every time the companion screen
    /// appears: the conversation loop (which cannot start without it) and the
    /// screen itself (which shows the "he needs to hear you" help sheet if
    /// it's refused). The naive version wrapped `requestRecordPermission` in a
    /// continuation per caller — and iOS answers a *concurrent* second request
    /// by simply never calling its completion handler.
    ///
    /// So one continuation resumed and the other was orphaned forever. The
    /// conversation loop lost that race about half the time and hung on its
    /// very first line, before it had set any status at all — which the
    /// companion screen renders as `.resting`: the orb sitting there,
    /// breathing, with no word beneath it and no error anywhere, indefinitely.
    /// He looked completely fine and could not hear a thing.
    ///
    /// A hang is the worst possible shape for this bug, because every visible
    /// symptom (no text, no error, no reaction) is identical to "working, just
    /// quiet". Two fixes, both needed:
    ///
    ///   1. If the answer is already known, return it WITHOUT asking. This is
    ///      the common path after the first launch, and it removes the race
    ///      entirely for everyone who has already granted it once.
    ///   2. If it genuinely must be asked, every concurrent caller waits on
    ///      ONE shared request rather than starting a second one iOS will
    ///      ignore.
    @MainActor
    static func requestMicPermission() async -> Bool {
        if let settled = settledPermission { return settled }
        if let inFlight = pendingAsk { return await inFlight.value }

        let ask = Task<Bool, Never> {
            await withCheckedContinuation { continuation in
                AVAudioApplication.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        }
        pendingAsk = ask
        let granted = await ask.value
        pendingAsk = nil
        return granted
    }

    /// The answer iOS already holds, or nil if it has never been asked.
    @MainActor
    private static var settledPermission: Bool? {
        switch AVAudioApplication.shared.recordPermission {
        case .granted: return true
        case .denied: return false
        case .undetermined: return nil
        @unknown default: return nil
        }
    }

    /// The single in-flight system prompt, shared by every caller waiting on it.
    @MainActor
    private static var pendingAsk: Task<Bool, Never>?
}

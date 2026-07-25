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
            options: [.defaultToSpeaker, .duckOthers, .allowBluetooth, .allowBluetoothA2DP]
        )
        try session.setActive(true, options: [])
    }

    /// Release the audio session (when the app leaves the screen).
    static func deactivate() {
        try? AVAudioSession.sharedInstance().setActive(false, options: [.notifyOthersOnDeactivation])
    }

    /// Ask for microphone access. iOS shows the system prompt the first time;
    /// after that this returns the stored answer immediately.
    static func requestMicPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }
}

// Plays Bob's voice (the MP3 the backend sends back) and waits until it's done.
//
// The conversation loop is deliberately turn-based: it stops listening while Bob
// speaks, then listens again. That keeps Bob from hearing his own voice and
// answering himself. (Proper echo cancellation is a device-tuning item later.)

import AVFoundation

@MainActor
final class AudioPlayer: NSObject, AVAudioPlayerDelegate {

    private var player: AVAudioPlayer?
    private var continuation: CheckedContinuation<Void, Never>?

    /// Play audio data and return only when playback finishes.
    func play(data: Data) async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            self.continuation = continuation
            do {
                let player = try AVAudioPlayer(data: data)
                player.delegate = self
                self.player = player
                if !player.play() {
                    finish()
                }
            } catch {
                finish()
            }
        }
    }

    /// Stop immediately (e.g. app leaving screen).
    func stop() {
        player?.stop()
        finish()
    }

    private func finish() {
        player = nil
        continuation?.resume()
        continuation = nil
    }

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor in self.finish() }
    }

    nonisolated func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        Task { @MainActor in self.finish() }
    }
}

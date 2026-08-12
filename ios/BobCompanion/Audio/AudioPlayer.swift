// Plays his voice — one piece, or a queue of pieces arriving while he speaks.
//
// The conversation loop is deliberately turn-based: it stops listening while he
// speaks, then listens again. That keeps him from hearing his own voice and
// answering himself. (Proper echo cancellation is a device-tuning item later.)
//
// ── WHY A QUEUE ────────────────────────────────────────────────────────────
//
// His reply no longer arrives as one file at the end. The server cuts it at
// sentence boundaries and sends each piece the moment it exists, so the first
// sentence is already being spoken while the second is still being written —
// several seconds out of every silence.
//
// That only works if something plays the pieces back to back, in order,
// without waiting for the whole reply. This is that something.
//
// It plays ordinary MP3 files one after another rather than feeding a single
// gapless audio graph, and it can do that because of WHERE the cuts are: at
// full stops, where a person draws breath anyway. A seam between two sentences
// is not a glitch — it is a pause. Chasing sample-accurate gaplessness here
// would mean AVAudioEngine, buffer scheduling and format conversion, to remove
// something nobody can hear.

import AVFoundation

@MainActor
final class AudioPlayer: NSObject, AVAudioPlayerDelegate {

    private var player: AVAudioPlayer?
    private var queue: [Data] = []
    private var waiters: [CheckedContinuation<Void, Never>] = []

    /// Nothing playing and nothing waiting to play.
    var isQuiet: Bool { player == nil && queue.isEmpty }

    /// Add a piece to the end of the queue. Starts playing if nothing is.
    func enqueue(_ data: Data) {
        guard !data.isEmpty else { return }
        queue.append(data)
        pump()
    }

    /// Returns once everything queued SO FAR has finished playing.
    ///
    /// Only meaningful after the last piece has been enqueued — call it when
    /// the stream has ended, never during it, or it returns the first time the
    /// queue happens to run dry between two sentences.
    func waitUntilQuiet() async {
        if isQuiet { return }
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            waiters.append(continuation)
        }
    }

    /// Play one piece and return when it has finished (the single-shot path:
    /// no voice provider, the background-voice intent, older servers).
    func play(data: Data) async {
        enqueue(data)
        await waitUntilQuiet()
    }

    /// Stop immediately and drop anything still queued (leaving the screen).
    func stop() {
        queue.removeAll()
        player?.stop()
        player = nil
        wake()
    }

    // MARK: - the pump

    private func pump() {
        while player == nil, !queue.isEmpty {
            let data = queue.removeFirst()
            // A piece that won't decode is skipped rather than allowed to stall
            // the rest of the sentence behind it. Losing one fragment of a
            // reply is bad; losing the remainder of it is worse.
            guard let next = try? AVAudioPlayer(data: data) else { continue }
            next.delegate = self
            if next.play() { player = next }
        }
        if isQuiet { wake() }
    }

    private func wake() {
        let waiting = waiters
        waiters.removeAll()
        for continuation in waiting { continuation.resume() }
    }

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor in
            self.player = nil
            self.pump()
        }
    }

    nonisolated func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        Task { @MainActor in
            self.player = nil
            self.pump()
        }
    }
}

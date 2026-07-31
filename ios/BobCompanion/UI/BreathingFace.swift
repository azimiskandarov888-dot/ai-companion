// A calm, living "presence" — a soft circle that breathes, and gently reacts to
// what's happening (listening, thinking, speaking). No words to read; just a warm
// thing that feels awake and with him.

import SwiftUI

struct BreathingFace: View {
    let status: ConversationController.Status

    @State private var breathe = false

    /// Sunlight rises as he wakes up and speaks: deep moss at rest → grass while
    /// he listens → a low gold shimmer while he thinks → full sun as he talks.
    private var color: Color {
        switch status {
        case .idle:       return Theme.leaf600   // resting — deep moss
        case .listening:  return Theme.leaf400   // grass brightening
        case .thinking:   return Theme.sun500    // low gold shimmer
        case .speaking:   return Theme.sun400    // full sunlight
        case .problem:    return Theme.clay      // clay, never an alarm red
        }
    }

    /// Speaking pulses a little quicker; the rest breathe slow and calm.
    private var period: Double {
        switch status {
        case .speaking:  return 1.1
        case .thinking:  return 1.6
        default:         return 3.2
        }
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(color.opacity(0.18))
                .frame(width: 320, height: 320)
                .scaleEffect(breathe ? 1.08 : 0.92)

            Circle()
                .fill(color.opacity(0.35))
                .frame(width: 220, height: 220)
                .scaleEffect(breathe ? 1.05 : 0.95)

            Circle()
                .fill(color)
                .frame(width: 130, height: 130)
                .scaleEffect(breathe ? 1.03 : 0.97)
                .shadow(color: color.opacity(0.6), radius: 30)
        }
        .animation(.easeInOut(duration: period).repeatForever(autoreverses: true), value: breathe)
        .animation(.easeInOut(duration: 0.6), value: status)
        .onAppear { breathe = true }
    }
}

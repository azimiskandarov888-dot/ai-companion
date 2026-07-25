// A calm, living "presence" — a soft circle that breathes, and gently reacts to
// what's happening (listening, thinking, speaking). No words to read; just a warm
// thing that feels awake and with him.

import SwiftUI

struct BreathingFace: View {
    let status: ConversationController.Status

    @State private var breathe = false

    private var color: Color {
        switch status {
        case .idle:       return Color(red: 0.55, green: 0.60, blue: 0.70)
        case .listening:  return Color(red: 0.40, green: 0.70, blue: 0.55) // warm green
        case .thinking:   return Color(red: 0.85, green: 0.70, blue: 0.35) // amber
        case .speaking:   return Color(red: 0.45, green: 0.62, blue: 0.85) // soft blue
        case .problem:    return Color(red: 0.80, green: 0.45, blue: 0.40) // muted red
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

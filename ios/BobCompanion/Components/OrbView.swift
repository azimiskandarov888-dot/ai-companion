// Him.
//
// The circle itself is a PLACEHOLDER — the owner is painting the real orb, and
// it drops in here by replacing `OrbShape` with an image. Everything around it
// is the design: the scene pools warm light where he sits, and that light rises
// as he wakes and speaks. The glow is the world answering him, not the orb.
//
// State is never carried by colour alone — size, light and the status word all
// move together, so it reads for colour-blind users and at a glance from across
// a room.

import SwiftUI

enum OrbState: Equatable {
    case resting
    case listening
    case thinking
    case speaking
    /// He can't hear you — no network, or the server is away. He dims and
    /// stops breathing, and says so in his own words. Never an error banner.
    case unreachable

    var diameter: CGFloat {
        switch self {
        case .resting, .unreachable: return Metrics.orbResting
        case .listening:             return Metrics.orbListening
        case .thinking:              return Metrics.orbThinking
        case .speaking:              return Metrics.orbSpeaking
        }
    }

    /// The tint the placeholder circle carries — from the palette's orb tints.
    var tint: Color {
        switch self {
        case .resting:     return Color(hex: 0x43532F)   // deep moss
        case .listening:   return Color(hex: 0x6E8A4C)   // grass brightening
        case .thinking:    return Color(hex: 0xB0862C)   // low gold shimmer
        case .speaking:    return Color(hex: 0xDEB65E)   // full sunlight
        case .unreachable: return Color(hex: 0x2E3828)   // dulled right down
        }
    }

    /// How much warm light the scene pools around him.
    var pooledLight: Double {
        switch self {
        case .resting:     return 0.08
        case .listening:   return 0.13
        case .thinking:    return 0.20
        case .speaking:    return 0.28
        case .unreachable: return 0.03
        }
    }

    /// One breath, in seconds. Slow at rest; quicker as he thinks and speaks.
    var breathPeriod: Double {
        switch self {
        case .resting:     return 3.2
        case .listening:   return 3.2
        case .thinking:    return 1.6
        case .speaking:    return 1.1
        case .unreachable: return 0        // he isn't breathing
        }
    }

    var statusWord: String? {
        switch self {
        case .resting, .unreachable: return nil      // resting shows no word — that's the point
        case .listening: return Strings.statusListening()
        case .thinking:  return Strings.statusThinking()
        case .speaking:  return Strings.statusSpeaking()
        }
    }

    var spokenDescription: String {
        switch self {
        case .resting:     return Strings.language == .russian ? "отдыхает"   : "resting"
        case .listening:   return Strings.language == .russian ? "слушает"    : "listening"
        case .thinking:    return Strings.language == .russian ? "думает"     : "thinking"
        case .speaking:    return Strings.language == .russian ? "говорит"    : "speaking"
        case .unreachable: return Strings.language == .russian ? "не слышит"  : "can't hear you"
        }
    }
}

struct OrbView: View {
    let state: OrbState

    @State private var breathing = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// ±4 % — the scale change is tiny; the light does most of the work.
    private var breathScale: CGFloat {
        guard !reduceMotion, state.breathPeriod > 0 else { return 1 }
        return breathing ? 1.04 : 0.96
    }

    var body: some View {
        ZStack {
            pooledLight
            OrbShape(tint: state.tint)
                .frame(width: state.diameter, height: state.diameter)
                .scaleEffect(breathScale)
                .shadow(color: state.tint.opacity(0.55),
                        radius: state.diameter * 0.34)
        }
        .animation(.easeInOut(duration: 0.6), value: state)   // colour and light drift, never snap
        .animation(
            reduceMotion || state.breathPeriod == 0
                ? nil
                : .easeInOut(duration: state.breathPeriod).repeatForever(autoreverses: true),
            value: breathing
        )
        .onAppear { breathing = true }
        .accessibilityElement()
        .accessibilityLabel(state.spokenDescription)
    }

    /// The scene answering him — a wide, soft pool of sun, not a rim light.
    private var pooledLight: some View {
        RadialGradient(
            colors: [Theme.sun400.opacity(state.pooledLight),
                     Theme.sun400.opacity(state.pooledLight * 0.35),
                     .clear],
            center: .center,
            startRadius: state.diameter * 0.35,
            endRadius: state.diameter * 2.9
        )
        .frame(width: state.diameter * 5.8, height: state.diameter * 5.8)
        .blendMode(.screen)
        .allowsHitTesting(false)
    }
}

/// ▸ PLACEHOLDER ◂
///
/// Replace the body of this view with the owner's painted orb — most simply:
///
///     Image("orb").resizable().scaledToFit()
///         .colorMultiply(tint)          // if the art should take the state tint
///
/// Nothing else in the app needs to change: every screen asks for `OrbView`,
/// and the sizes, light and motion around it stay exactly as designed.
private struct OrbShape: View {
    let tint: Color

    var body: some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: [tint.opacity(0.95), tint.opacity(0.7), tint.opacity(0.25)],
                    center: UnitPoint(x: 0.40, y: 0.34),
                    startRadius: 2, endRadius: 120
                )
            )
            .overlay(
                Circle().strokeBorder(tint.opacity(0.35), lineWidth: 1)
            )
    }
}

// MARK: - The status word

struct StatusWord: View {
    let state: OrbState

    var body: some View {
        Text(state.statusWord ?? " ")
            .appFont(AppType.caption)
            .tracking(AppType.statusTracking)
            .foregroundStyle(state == .speaking ? Theme.sage : Theme.lichen)
            .opacity(state.statusWord == nil ? 0 : 1)
            .animation(.easeInOut(duration: 0.45), value: state)
            .accessibilityHidden(true)     // the orb already announces the state
    }
}

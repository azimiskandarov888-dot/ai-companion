// The controls: buttons, plan cards, chips, list groups.
//
// Softness is a rule, not a mood — nothing here has a hard square edge, and
// nothing is opaque. Gold accents exactly ONE action per screen; if everything
// glows, nothing does.

import SwiftUI

// MARK: - Buttons

enum ButtonTone {
    /// Sun gold. The one true action on a screen — and only one.
    case sun
    /// Leaf green. A calm primary where gold is being saved for later.
    case leaf
    /// A translucent panel. Everything else.
    case quiet
}

struct AppButton: View {
    let title: String
    var tone: ButtonTone = .quiet
    var icon: Image? = nil
    /// Overrides the label colour — used only where the tone is right but the
    /// meaning isn't, e.g. «Start over» on a quiet button.
    var labelColour: Color? = nil
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                if let icon {
                    icon.font(.system(size: 19))
                        .frame(width: 26)          // reserved so labels align
                }
                Text(title)
                    .appFont(AppType.button)
                    .lineLimit(2)                  // Russian runs longer
                    .minimumScaleFactor(0.85)
                    .multilineTextAlignment(.center)
            }
            .foregroundStyle(foreground)
            .frame(maxWidth: .infinity)
            .frame(minHeight: Metrics.buttonHeight)
            .padding(.horizontal, 18)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: Metrics.buttonRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: Metrics.buttonRadius, style: .continuous)
                    .strokeBorder(borderColour, lineWidth: 1)
            )
        }
        .buttonStyle(SoftPress())
    }

    private var foreground: Color {
        if let labelColour { return labelColour }
        switch tone {
        case .sun:   return Theme.onSun
        case .leaf:  return Theme.parchment
        case .quiet: return Theme.linen
        }
    }

    @ViewBuilder private var background: some View {
        switch tone {
        case .sun:   Theme.sun400
        case .leaf:  Theme.leaf500
        case .quiet: PanelBackground(radius: Metrics.buttonRadius)
        }
    }

    private var borderColour: Color {
        tone == .quiet ? Theme.hairline : .clear
    }
}

/// Presses settle rather than bounce — nothing in this app overshoots.
struct SoftPress: ButtonStyle {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(reduceMotion ? 1 : (configuration.isPressed ? 0.985 : 1))
            .opacity(configuration.isPressed ? 0.9 : 1)
            .animation(.spring(response: 0.3, dampingFraction: 0.9), value: configuration.isPressed)
    }
}

// MARK: - Plan cards
//
// Selection is shown by a gold hairline AND a filled tick — never by colour
// alone, so it reads for colour-blind users too.

struct PlanCard: View {
    let title: String
    let detail: String
    let price: String
    let isChosen: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .center, spacing: 14) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .appFont(AppType.body)
                        .foregroundStyle(Theme.linen)
                    Text(detail)
                        .appFont(AppType.caption)
                        .foregroundStyle(Theme.lichen)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 8)
                Text(price)
                    .appFont(AppType.body)
                    .foregroundStyle(isChosen ? Theme.sun300 : Theme.sage)
                Tick(isFilled: isChosen)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 16)
            .frame(minHeight: isChosen ? 88 : 76)
            .frame(maxWidth: .infinity, alignment: .leading)
            .panel()
            .overlay(
                RoundedRectangle(cornerRadius: Metrics.cardRadius, style: .continuous)
                    .strokeBorder(isChosen ? Theme.sun600 : Theme.ringUnchosen,
                                  lineWidth: isChosen ? 1.5 : 1)
            )
        }
        .buttonStyle(SoftPress())
        .accessibilityAddTraits(isChosen ? [.isButton, .isSelected] : .isButton)
    }
}

private struct Tick: View {
    let isFilled: Bool
    var body: some View {
        ZStack {
            Circle()
                .strokeBorder(isFilled ? Theme.sun400 : Theme.ringUnchosen, lineWidth: 1.5)
                .background(Circle().fill(isFilled ? Theme.sun400 : .clear))
                .frame(width: 24, height: 24)
            if isFilled {
                Image(systemName: "checkmark")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Theme.onSun)
            }
        }
        .frame(width: Metrics.minTouch, height: Metrics.minTouch)
    }
}

// MARK: - Soft chips
//
// On screen 4 these live ON the paper, so they're drawn in ink rather than
// linen. They insert a phrase into the user's own writing — they are never a
// field, and never required.

struct SoftChip: View {
    let title: String
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .appFont(AppType.caption)
                .foregroundStyle(Theme.inkSoft)
                .padding(.horizontal, 14)
                .frame(height: 32)
                .overlay(
                    Capsule().strokeBorder(Theme.inkSoft.opacity(0.45), lineWidth: 1)
                )
        }
        .buttonStyle(SoftPress())
        .frame(minHeight: Metrics.minTouch)   // 44 pt hit slop around a 32 pt chip
        .contentShape(Rectangle())
    }
}

// MARK: - List groups
//
// Several small rounded groups with air between them — never one long block.
// Dividers are faint and INSET, never edge to edge.

struct ListGroup<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        VStack(spacing: 0) { content }
            .panel()
    }
}

struct ListRow: View {
    let label: String
    var value: String? = nil
    var tone: Color = Theme.linen
    var showsDivider: Bool = true
    var action: (() -> Void)? = nil

    var body: some View {
        Group {
            if let action {
                Button(action: action) { row }.buttonStyle(SoftPress())
            } else {
                row
            }
        }
    }

    private var row: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Text(label)
                    .appFont(AppType.body)
                    .foregroundStyle(tone)
                Spacer(minLength: 12)
                if let value {
                    Text(value)
                        .appFont(AppType.secondary)
                        .foregroundStyle(Theme.lichen)
                        .multilineTextAlignment(.trailing)
                }
            }
            .padding(.horizontal, Metrics.dividerInset)
            .frame(minHeight: Metrics.rowHeight)

            if showsDivider {
                Rectangle()
                    .fill(Theme.divider)
                    .frame(height: 1)
                    .padding(.leading, Metrics.dividerInset)
                    .padding(.trailing, Metrics.dividerInset)
            }
        }
        .contentShape(Rectangle())
    }
}

// Watches the keyboard so the scroll can rise IN STEP with it.
//
// The spec is strict about this: the scroll must never go under the keyboard,
// and the rise must match the keyboard's own curve rather than being a separate
// animation that races it. So we take both the height and the duration straight
// from the system notification.

import SwiftUI
import Combine

@MainActor
final class KeyboardObserver: ObservableObject {
    @Published private(set) var height: CGFloat = 0
    @Published private(set) var duration: Double = 0.25

    var isShowing: Bool { height > 0 }

    private var bag = Set<AnyCancellable>()

    init() {
        let centre = NotificationCenter.default

        centre.publisher(for: UIResponder.keyboardWillShowNotification)
            .merge(with: centre.publisher(for: UIResponder.keyboardWillChangeFrameNotification))
            .sink { [weak self] note in self?.apply(note, showing: true) }
            .store(in: &bag)

        centre.publisher(for: UIResponder.keyboardWillHideNotification)
            .sink { [weak self] note in self?.apply(note, showing: false) }
            .store(in: &bag)
    }

    private func apply(_ note: Notification, showing: Bool) {
        let info = note.userInfo
        duration = (info?[UIResponder.keyboardAnimationDurationUserInfoKey] as? Double) ?? 0.25
        guard showing,
              let frame = info?[UIResponder.keyboardFrameEndUserInfoKey] as? CGRect else {
            height = 0
            return
        }
        // On an iPad-style floating keyboard the frame can sit off-screen; only
        // count what actually covers the app.
        let screenHeight = UIScreen.main.bounds.height
        height = max(0, screenHeight - frame.origin.y)
    }
}

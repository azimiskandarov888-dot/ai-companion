# Checklist: iOS app (SwiftUI)

Evidence the reviewer needs: a successful build and a simulator screenshot of every changed screen
(`xcrun simctl io booted screenshot <file>.png`).

- [ ] The app builds with no new errors or warnings.
- [ ] A real screenshot exists for each changed screen, and it shows what the brief asked for.
- [ ] No black screen: the world is visible behind the screens (never `.id()` around `WorldView`).
- [ ] Text is readable, not cut off, not under the notch or home bar; Russian text fits.
- [ ] Look is cinematic (Ghost of Tsushima / The Last of Us menus), not cartoon, not a generic "clean" app.
- [ ] Payment is never asked right after sign-in, and never by Bob himself.
- [ ] No keys or secrets in the app code.

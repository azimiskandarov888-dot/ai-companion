// Why he can't hear you — in plain words, and only where you go looking.
//
// On the companion screen he says «не слышит» and nothing else, forever. That
// is deliberate and it is not negotiable: a lonely person must never be shown
// an error code. But it left the person BUILDING the app with the same three
// words for three completely different problems:
//
//   · iOS is blocking the app from the home network   (fix: one toggle)
//   · the address is wrong                            (fix: retype it)
//   · the server isn't running / a key is refused     (fix: the Mac)
//
// They look identical on screen and their fixes have nothing in common. So the
// distinction lives here, and surfaces only inside Settings → Сервер, where a
// user would never wander and a tester goes first.

import Foundation

// MARK: - The last thing that actually went wrong

/// Remembers the most recent failure so Settings can show it later. Nothing
/// here is ever displayed on the companion screen.
@MainActor
final class Trouble: ObservableObject {
    static let shared = Trouble()

    @Published private(set) var lastFailure: String = ""

    func record(_ error: Error, url: URL?) {
        lastFailure = ConnectionCheck.describe(error, url: url)
    }

    func clear() { lastFailure = "" }
}

// MARK: - Asking the server whether it's there

enum ConnectionCheck {

    enum Outcome {
        case reachable(String)     // it answered — and what it said about itself
        case unreachable(String)   // it didn't — and why, in plain words
    }

    /// Ping /api/health and translate whatever happens into something a person
    /// can act on. Short timeout: if the server is there it answers instantly,
    /// and a long wait here teaches nothing.
    static func run() async -> Outcome {
        let url = AppConfig.shared.backendURL.appendingPathComponent("api/health")
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        request.cachePolicy = .reloadIgnoringLocalCacheData

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                return .unreachable(ru("Странный ответ.", "Odd response."))
            }
            guard (200...299).contains(http.statusCode) else {
                let detail = String(data: data, encoding: .utf8) ?? ""
                return .unreachable(ru("Сервер ответил \(http.statusCode). \(detail)",
                                       "Server answered \(http.statusCode). \(detail)"))
            }
            return .reachable(summarise(data))
        } catch {
            return .unreachable(describe(error, url: url))
        }
    }

    /// What the server says it has ready.
    ///
    /// Careful about what this can and cannot prove: /api/health reports whether
    /// each key is PRESENT, not whether the provider will accept it. A key that
    /// is present but out of credit reads as ready here and then fails as a 503
    /// mid-sentence. So the wording below never promises more than "on the air".
    /// The check that actually calls all three is `python check_keys.py`.
    private static func summarise(_ data: Data) -> String {
        guard
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return ru("Сервер на связи.", "Server is up.")
        }

        let named = [
            "brain_claude": ru("мозг", "brain"),
            "ears_whisper": ru("уши", "ears"),
            "mouth": ru("голос", "voice"),
        ]
        let services = json["services"] as? [String: Bool] ?? [:]
        let missing = services
            .filter { !$0.value }
            .keys
            .map { named[$0] ?? $0 }
            .sorted()
        let voice = json["tts_provider"] as? String ?? "—"

        if missing.isEmpty {
            return ru("Сервер на связи, ключи на месте. Голос — \(voice).",
                      "Server is up, keys are in place. Voice — \(voice).")
        }
        let list = missing.joined(separator: ", ")
        return ru("Сервер на связи, но не настроено: \(list).",
                  "Server is up, but not configured: \(list).")
    }

    // MARK: - Translating the failure

    /// The whole point of this file. `localizedDescription` says "The Internet
    /// connection appears to be offline" for a phone that is plainly online —
    /// because iOS reports a BLOCKED LOCAL NETWORK as exactly the same error as
    /// no internet at all. Reading that literally sends you to the Wi-Fi
    /// settings, which is the one place the fix isn't.
    static func describe(_ error: Error, url: URL?) -> String {
        if let backend = error as? BackendError {
            // The backend now names the stage that failed inside the detail —
            // ears, brain, or voice — so this is already the answer.
            return backend.errorDescription ?? "\(backend)"
        }

        let nsError = error as NSError
        guard nsError.domain == NSURLErrorDomain else {
            return error.localizedDescription
        }

        let onHomeNetwork = isPrivate(url?.host)

        switch nsError.code {
        case NSURLErrorNotConnectedToInternet where onHomeNetwork:
            // -1009 on a 192.168.x address is almost never "no internet".
            return ru("iPhone не пускает приложение в домашнюю сеть.\n\n"
                      + "Настройки → Приложения → Боб → «Локальная сеть» — включите.\n"
                      + "Если такого пункта нет: удалите приложение, поставьте заново "
                      + "и разрешите, когда спросит.",
                      "iPhone is blocking the app from the local network.\n\n"
                      + "Settings → Apps → Bob → Local Network — turn it on.\n"
                      + "If it isn't listed: delete the app, install it again, and "
                      + "allow it when asked.")

        case NSURLErrorNotConnectedToInternet:
            return ru("Нет сети.", "No network.")

        case NSURLErrorCannotConnectToHost:
            return ru("По этому адресу никто не отвечает.\n\n"
                      + "Сервер на Mac не запущен, или это другой порт. "
                      + "Проверьте, что в терминале работает ./run.sh.",
                      "Nothing is answering at this address.\n\n"
                      + "The server on the Mac isn't running, or it's a different "
                      + "port. Check that ./run.sh is going in the terminal.")

        case NSURLErrorTimedOut:
            return ru("Адрес принят, но ответа нет — скорее всего адрес чужой.\n\n"
                      + "На Mac выполните:  ipconfig getifaddr en0\n"
                      + "и впишите то, что он покажет.",
                      "The address took the request but nothing came back — most "
                      + "likely it's the wrong address.\n\n"
                      + "On the Mac run:  ipconfig getifaddr en0\n"
                      + "and type in what it prints.")

        case NSURLErrorCannotFindHost:
            return ru("Такого адреса не существует.", "No such address.")

        case NSURLErrorAppTransportSecurityRequiresSecureConnection,
             NSURLErrorSecureConnectionFailed:
            return ru("iOS не пропускает обычный http на этот адрес.",
                      "iOS is refusing plain http to this address.")

        default:
            return "\(error.localizedDescription) (\(nsError.code))"
        }
    }

    /// Is this a home-network address? 192.168.x, 10.x, 172.16–31.x, or a
    /// .local name. Deciding this is what separates "blocked" from "offline".
    private static func isPrivate(_ host: String?) -> Bool {
        guard let host, !host.isEmpty else { return false }
        if host == "localhost" || host.hasSuffix(".local") { return true }

        let parts = host.split(separator: ".").compactMap { Int($0) }
        guard parts.count == 4 else { return false }
        switch (parts[0], parts[1]) {
        case (10, _):                       return true
        case (192, 168):                    return true
        case (172, 16...31):                return true
        case (127, _):                      return true
        default:                            return false
        }
    }

    private static func ru(_ russian: String, _ english: String) -> String {
        Strings.language == .russian ? russian : english
    }
}

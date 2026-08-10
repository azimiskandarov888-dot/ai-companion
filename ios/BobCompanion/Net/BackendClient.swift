// Talks to our backend. Sends his recorded voice to POST /api/talk and gets back
// { transcript, reply, audio }. The backend does the ears (Whisper), the brain
// (Claude, in Bob's persona), and the mouth (Fish Audio). This app never sees an
// API key.

import Combine      // ObservableObject / @Published live here, not in Foundation
import Foundation

/// The shape of the backend's /api/talk reply (see backend/app/main.py).
struct TalkResponse: Decodable {
    let transcript: String
    let reply: String
    let audioBase64: String?
    let audioMime: String?
    let note: String?
    /// Set when the SERVER declined to answer: "asleep" or "daily_limit".
    /// The limit lives there, not here — an app-side limit is defeated by a
    /// modified app and, far more likely, by a bug in this one.
    let state: String?
    /// Seconds of conversation left today, as the server counts them.
    let secondsLeft: Int?

    enum CodingKeys: String, CodingKey {
        case transcript, reply, note, state
        case audioBase64 = "audio_base64"
        case audioMime = "audio_mime"
        case secondsLeft = "seconds_left"
    }
}

enum BackendError: LocalizedError {
    case badStatus(Int, String)
    case notConfigured

    var errorDescription: String? {
        switch self {
        case .badStatus(let code, let detail):
            return "Сервер ответил \(code): \(detail)"
        case .notConfigured:
            return "Не задан адрес сервера"
        }
    }
}

/// POST /api/companion/create — the friend walks in.
struct CreateCompanionResponse: Decodable {
    let name: String
}

/// GET /api/diary — what he has written about his friend so far.
struct DiaryResponse: Decodable {
    let companion: String
    let text: String

    /// The diary arrives as flowing prose. The book needs leaves, so we break
    /// it at paragraphs and pack them until a leaf is comfortably full — the
    /// design asks for 38–46 characters a line, which lands around 420
    /// characters a page at the diary's size.
    func leaves(charactersPerLeaf: Int = 420) -> [String] {
        let paragraphs = text
            .components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        guard !paragraphs.isEmpty else { return [text] }

        var leaves: [String] = []
        var current = ""
        for paragraph in paragraphs {
            let candidate = current.isEmpty ? paragraph : current + "\n\n" + paragraph
            if candidate.count > charactersPerLeaf, !current.isEmpty {
                leaves.append(current)
                current = paragraph
            } else {
                current = candidate
            }
        }
        if !current.isEmpty { leaves.append(current) }
        // A book always opens on a spread, so never leave a lone left-hand leaf.
        if leaves.count % 2 == 1 { leaves.append("") }
        return leaves
    }
}

struct BackendClient {
    let baseURL: URL

    /// He dozed off, and someone has come back and tapped. Waking is free and
    /// never refills the day's allowance.
    func wake() async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/wake"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(
            withJSONObject: ["session_id": AppConfig.shared.sessionID]
        )
        request.timeoutInterval = 10
        _ = try? await URLSession.shared.data(for: request)
    }

    /// Send one recorded utterance, get Bob's spoken reply back.
    func talk(audioFileURL: URL, sessionID: String) async throws -> TalkResponse {
        let endpoint = baseURL.appendingPathComponent("api/talk")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        // One turn is three round trips end to end — ears (Whisper), brain
        // (Claude), voice (Fish) — and on home Wi-Fi that lands at 8–15 s more
        // often than it looks like it should. At 15 s a perfectly healthy turn
        // times out, and a timeout is indistinguishable on screen from him not
        // hearing you. Better a long think than a false «не слышит».
        request.timeoutInterval = 30

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)",
                         forHTTPHeaderField: "Content-Type")

        let audioData = try Data(contentsOf: audioFileURL)
        var body = Data()
        body.appendFormField(named: "session_id", value: sessionID, boundary: boundary)
        body.appendFileField(named: "audio",
                             filename: "utterance.m4a",
                             contentType: "audio/m4a",
                             fileData: audioData,
                             boundary: boundary)
        body.appendClosingBoundary(boundary)

        // upload(for:from:) uses `body` as the request body.
        let (data, response) = try await URLSession.shared.upload(for: request, from: body)

        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            let detail = String(data: data, encoding: .utf8) ?? ""
            throw BackendError.badStatus(http.statusCode, detail)
        }

        return try JSONDecoder().decode(TalkResponse.self, from: data)
    }

    /// Their story, plus whatever they asked for, and he walks in — with his
    /// own name. Wishes may be empty; that's arguably the best case.
    func createCompanion(story: String, wishes: String) async throws -> CreateCompanionResponse {
        try await postJSON(
            "api/companion/create",
            body: ["about": story, "wishes": wishes],
            timeout: 40                       // he is being written; give him time
        )
    }

    /// His diary about his friend. Cheap and instant unless his memory has
    /// grown since last time, in which case he rewrites it.
    func diary() async throws -> DiaryResponse {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/diary"))
        request.timeoutInterval = 15   // he says he can't hear you FAST, not after a minute
        let (data, response) = try await URLSession.shared.data(for: request)
        try Self.check(response, data)
        return try JSONDecoder().decode(DiaryResponse.self, from: data)
    }

    // MARK: - shared

    private func postJSON<T: Decodable>(_ path: String,
                                        body: [String: String],
                                        timeout: TimeInterval) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.timeoutInterval = timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try Self.check(response, data)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private static func check(_ response: URLResponse, _ data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200...299).contains(http.statusCode) else {
            throw BackendError.badStatus(http.statusCode,
                                         String(data: data, encoding: .utf8) ?? "")
        }
    }
}

// MARK: - multipart/form-data helpers

private extension Data {
    mutating func appendString(_ string: String) {
        if let data = string.data(using: .utf8) { append(data) }
    }

    mutating func appendFormField(named name: String, value: String, boundary: String) {
        appendString("--\(boundary)\r\n")
        appendString("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n")
        appendString("\(value)\r\n")
    }

    mutating func appendFileField(named name: String,
                                  filename: String,
                                  contentType: String,
                                  fileData: Data,
                                  boundary: String) {
        appendString("--\(boundary)\r\n")
        appendString("Content-Disposition: form-data; name=\"\(name)\"; filename=\"\(filename)\"\r\n")
        appendString("Content-Type: \(contentType)\r\n\r\n")
        append(fileData)
        appendString("\r\n")
    }

    mutating func appendClosingBoundary(_ boundary: String) {
        appendString("--\(boundary)--\r\n")
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// Why he can't hear you — in plain words, and only where you go looking.
//
// On the companion screen he says «не слышит» and nothing else, forever. That
// is deliberate and it is not negotiable: a lonely person must never be shown
// an error code. But it left the person BUILDING the app with the same two
// words for several unrelated problems:
//
//   · iOS is blocking the app from the home network   (fix: one toggle)
//   · the address is wrong                            (fix: retype it)
//   · the server isn't running / a key is refused     (fix: the Mac)
//
// They look identical on screen and their fixes have nothing in common. So the
// distinction lives here, and surfaces only inside Settings → Сервер, where a
// user would never wander and a tester goes first.
//
// This rides along in BackendClient.swift rather than in a file of its own, on
// purpose: a NEW file is invisible to Xcode until the project is regenerated,
// and regenerating throws away the signing team that has to be set by hand.
// Adding to a file Xcode already compiles costs nothing and breaks nothing.
// ═══════════════════════════════════════════════════════════════════════════

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

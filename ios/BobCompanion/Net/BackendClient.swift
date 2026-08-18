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
    /// True when he was already spoken aloud piece by piece as he thought, so
    /// there is nothing left for the caller to play. Never sent by the server —
    /// it is how the streaming path reports itself back through the same type.
    var spokenAsHeThought: Bool = false

    enum CodingKeys: String, CodingKey {
        case transcript, reply, note, state
        case audioBase64 = "audio_base64"
        case audioMime = "audio_mime"
        case secondsLeft = "seconds_left"
    }
}

/// One line of the streaming reply (`application/x-ndjson`). See the wire
/// format documented in backend/app/main.py.
private struct TalkEvent: Decodable {
    let kind: String
    let transcript: String?
    let text: String?
    let audioBase64: String?
    let reply: String?
    let detail: String?
    let secondsLeft: Int?

    enum CodingKeys: String, CodingKey {
        case kind, transcript, text, reply, detail
        case audioBase64 = "audio_base64"
        case secondsLeft = "seconds_left"
    }
}

enum BackendError: LocalizedError {
    case badStatus(Int, String)
    case notConfigured
    /// The Keychain wouldn't give us this phone's token. We stop rather than
    /// ask anonymously — see AppConfig.userToken for why an unknown identity
    /// is worse than a failed turn.
    case noIdentity

    var errorDescription: String? {
        switch self {
        case .badStatus(let code, let detail):
            return "Сервер ответил \(code): \(detail)"
        case .notConfigured:
            return "Не задан адрес сервера"
        case .noIdentity:
            return "Связка ключей недоступна — не могу узнать, чей это телефон"
        }
    }
}

/// POST /api/companion/create — the friend walks in.
struct CreateCompanionResponse: Decodable {
    let name: String
}

/// One exchange in «пока его нет»: what was asked, what they answered.
struct IntakeTurn: Codable, Equatable {
    var q: String
    var a: String
}

/// POST /api/intake/next — the next question, or the end of the conversation.
struct IntakeQuestion: Decodable {
    let say: String
    let enough: Bool
    /// A short warm line about what they just said, shown above the question.
    /// The entire personality of something with no identity.
    let reaction: String?
    /// "short" for a few words, "open" for the last real question — which
    /// gets a taller box, because the size of the space is itself a hint
    /// about how much is wanted.
    let kind: String?
    /// Only on the very first call: the honest frame that makes the whole
    /// conversation work — he isn't here yet, he'll be made out of this.
    let preamble: String?
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

    // MARK: - Who is asking
    //
    // Every request carries this phone's token, and identity travels ONLY
    // here. It used to ride as a `session_id` form field / JSON key, which
    // meant the caller chose who it was — and an identity the caller chooses
    // is an identity anyone can borrow. A header also stays out of access
    // logs, proxy logs and browser history, which a query string does not.

    /// A request with this person's identity attached, or a throw if we can't
    /// establish who they are. Never falls back to asking anonymously.
    static func authorized(_ url: URL) throws -> URLRequest {
        guard let token = AppConfig.shared.userToken else { throw BackendError.noIdentity }
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        return request
    }

    private func authorized(_ path: String) throws -> URLRequest {
        try Self.authorized(baseURL.appendingPathComponent(path))
    }

    /// He dozed off, and someone has come back and tapped. Waking is free and
    /// never refills the day's allowance.
    func wake() async throws {
        var request = try authorized("api/wake")
        request.httpMethod = "POST"
        request.timeoutInterval = 10
        _ = try? await URLSession.shared.data(for: request)
    }

    /// The wire format that lets him start speaking before he has finished
    /// thinking. One JSON object per line — see backend/app/main.py.
    private static let ndjson = "application/x-ndjson"

    /// Send one recorded utterance and hear him answer.
    ///
    /// `onPiece` is handed each fragment of audio the moment it exists, in
    /// order, WHILE the rest of his reply is still being written. That is the
    /// whole point: the turn used to be three waits laid end to end — hear it
    /// all, think it all, say it all — and the listener sat through the sum.
    ///
    /// The server may decline to stream (out of allowance, dozing, or a
    /// question that needs a web search), in which case this quietly falls
    /// back to reading one whole JSON reply. Both come back as a TalkResponse,
    /// so the caller has one shape to handle either way.
    func talk(
        audioFileURL: URL,
        onPiece: @escaping (Data) async -> Void
    ) async throws -> TalkResponse {
        var request = try authorized("api/talk")
        request.httpMethod = "POST"
        // One turn is three round trips end to end — ears (Whisper), brain
        // (Claude), voice — and on home Wi-Fi that lands at 8–15 s more often
        // than it looks like it should. At 15 s a perfectly healthy turn times
        // out, and a timeout is indistinguishable on screen from him not
        // hearing you. Better a long think than a false «не слышит».
        //
        // On the streaming path this is the gap BETWEEN pieces, not the length
        // of the whole turn, so it is generous even for a long reply.
        request.timeoutInterval = 30
        request.setValue(Self.ndjson, forHTTPHeaderField: "Accept")

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)",
                         forHTTPHeaderField: "Content-Type")

        let audioData = try Data(contentsOf: audioFileURL)
        var body = Data()
        body.appendFileField(named: "audio",
                             filename: "utterance.m4a",
                             contentType: "audio/m4a",
                             fileData: audioData,
                             boundary: boundary)
        body.appendClosingBoundary(boundary)
        request.httpBody = body

        // bytes(for:) — not upload(for:from:) — because only this one hands the
        // response back as it arrives instead of when it is complete.
        let (stream, response) = try await URLSession.shared.bytes(for: request)
        let http = response as? HTTPURLResponse

        if let http, !(200...299).contains(http.statusCode) {
            throw BackendError.badStatus(http.statusCode, try await Self.text(of: stream))
        }

        let contentType = http?.value(forHTTPHeaderField: "Content-Type") ?? ""
        guard contentType.contains(Self.ndjson) else {
            let whole = try await Self.data(of: stream)
            return try JSONDecoder().decode(TalkResponse.self, from: whole)
        }

        var transcript = ""
        var pieces: [String] = []
        var finalReply = ""
        var secondsLeft: Int?
        var trouble: String?
        var spoke = false

        for try await line in stream.lines {
            guard
                let data = line.data(using: .utf8),
                let event = try? JSONDecoder().decode(TalkEvent.self, from: data)
            else { continue }   // a line we don't understand is not a reason to stop

            switch event.kind {
            case "heard":
                transcript = event.transcript ?? ""
            case "say":
                if let text = event.text, !text.isEmpty { pieces.append(text) }
                if let encoded = event.audioBase64, !encoded.isEmpty,
                   let audio = Data(base64Encoded: encoded), !audio.isEmpty {
                    await onPiece(audio)
                    spoke = true
                }
            case "trouble":
                trouble = event.detail
            case "done":
                finalReply = event.reply ?? ""
                secondsLeft = event.secondsLeft
            default:
                break
            }
        }

        // It broke before he managed a single word — that is a failed turn, and
        // the caller should treat it exactly like any other. If he DID get
        // something out, it has already been heard, so the turn stands.
        if let trouble, !spoke, pieces.isEmpty {
            throw BackendError.badStatus(503, trouble)
        }

        return TalkResponse(
            transcript: transcript,
            reply: finalReply.isEmpty ? pieces.joined(separator: " ") : finalReply,
            audioBase64: nil,
            audioMime: nil,
            note: nil,
            state: nil,
            secondsLeft: secondsLeft,
            spokenAsHeThought: spoke
        )
    }

    private static func data(of stream: URLSession.AsyncBytes) async throws -> Data {
        var data = Data()
        for try await byte in stream { data.append(byte) }
        return data
    }

    private static func text(of stream: URLSession.AsyncBytes) async throws -> String {
        String(data: try await data(of: stream), encoding: .utf8) ?? ""
    }

    /// The next question in «пока его нет» — the conversation that replaced
    /// the blank «расскажите о себе» page (backend/app/intake.py).
    ///
    /// A failure here ENDS the conversation rather than surfacing an error:
    /// whatever they've already said is enough to build on, and a person
    /// halfway through telling you about their life should never be shown a
    /// broken screen. The caller treats a thrown error as `enough`.
    func intakeNext(conversation: [IntakeTurn]) async throws -> IntakeQuestion {
        var request = try authorized("api/intake/next")
        request.httpMethod = "POST"
        request.timeoutInterval = 25
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["conversation": conversation])

        let (data, response) = try await URLSession.shared.data(for: request)
        try Self.check(response, data)
        return try JSONDecoder().decode(IntakeQuestion.self, from: data)
    }

    /// Their story, plus whatever they asked for, and he walks in — with his
    /// own name. Wishes may be empty; that's arguably the best case.
    ///
    /// 200s, not 40. The server runs THREE calls in sequence for this — the
    /// psychological reading, the ten strangers, the deep write (which can
    /// itself run twice — see matchmaker's one retry on a malformed reply) —
    /// and the first of those is deliberately the slowest thing the app ever
    /// does (its own comment calls it "worth minutes"). 40s was tight enough
    /// that a real, working — just unhurried — creation hit this exact
    /// timeout on a real phone.
    ///
    /// The number tracks the server's own budget, which grew again when the
    /// deep write moved to the best model with thinking time: reading 90s +
    /// ten strangers 30s + deep write 120s = 240s for a normal run (see
    /// brain._READING_TIMEOUT, matchmaker._STAGE_TIMEOUT / _WRITE_TIMEOUT).
    /// 260 clears that with margin.
    ///
    /// These are stall ceilings, not expected durations — a real creation is
    /// well under a minute. The absolute worst case (every stage maxing out
    /// AND the write retried) deliberately exceeds this, because at that
    /// point the connection is broken and "he couldn't come, try again" is
    /// the right answer. `test_the_creation_budget_actually_fits_under_the_
    /// phones_ceiling` fails the build if the NORMAL path ever loses that
    /// race again.
    func createCompanion(story: String, wishes: String) async throws -> CreateCompanionResponse {
        try await postJSON(
            "api/companion/create",
            body: ["about": story, "wishes": wishes],
            timeout: 260
        )
    }

    /// His diary about his friend. Cheap and instant unless his memory has
    /// grown since last time, in which case he rewrites it.
    func diary() async throws -> DiaryResponse {
        var request = try authorized("api/diary")
        request.timeoutInterval = 15   // he says he can't hear you FAST, not after a minute
        let (data, response) = try await URLSession.shared.data(for: request)
        try Self.check(response, data)
        return try JSONDecoder().decode(DiaryResponse.self, from: data)
    }

    // MARK: - shared

    private func postJSON<T: Decodable>(_ path: String,
                                        body: [String: String],
                                        timeout: TimeInterval) async throws -> T {
        var request = try authorized(path)
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

    /// A failure that isn't the network's fault — the microphone, the audio
    /// session, the recorder.
    ///
    /// «не слышит» on the companion screen covers ALL of them, deliberately:
    /// a lonely person must never be shown a reason. But that means the
    /// person BUILDING this had one sentence for a dead server, a refused
    /// microphone and a broken audio session alike, and only the first of the
    /// three was ever written down anywhere. Settings → Сервер is where a
    /// tester goes first, so all three belong there.
    func note(_ what: String) {
        lastFailure = what
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
        // Signed as this phone, so the summary below describes THIS person's
        // friend rather than whoever the server happens to know about.
        guard var request = try? BackendClient.authorized(url) else {
            return .unreachable(ru("Связка ключей недоступна — не могу узнать, чей это телефон.",
                                   "The Keychain is unavailable — can't tell whose phone this is."))
        }
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

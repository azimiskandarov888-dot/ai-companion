// Talks to our backend. Sends his recorded voice to POST /api/talk and gets back
// { transcript, reply, audio }. The backend does the ears (Whisper), the brain
// (Claude, in Bob's persona), and the mouth (Fish Audio). This app never sees an
// API key.

import Foundation

/// The shape of the backend's /api/talk reply (see backend/app/main.py).
struct TalkResponse: Decodable {
    let transcript: String
    let reply: String
    let audioBase64: String?
    let audioMime: String?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case transcript, reply, note
        case audioBase64 = "audio_base64"
        case audioMime = "audio_mime"
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

    /// Send one recorded utterance, get Bob's spoken reply back.
    func talk(audioFileURL: URL, sessionID: String) async throws -> TalkResponse {
        let endpoint = baseURL.appendingPathComponent("api/talk")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 15   // he says he can't hear you FAST, not after a minute

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

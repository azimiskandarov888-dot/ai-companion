// Talks to our backend. Sends his recorded voice to POST /api/talk and gets back
// { transcript, reply, audio }. The backend does the ears (Whisper), the brain
// (Claude, in Bob's persona), and the mouth (ElevenLabs). This app never sees an
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

struct BackendClient {
    let baseURL: URL

    /// Send one recorded utterance, get Bob's spoken reply back.
    func talk(audioFileURL: URL, sessionID: String) async throws -> TalkResponse {
        let endpoint = baseURL.appendingPathComponent("api/talk")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 60

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

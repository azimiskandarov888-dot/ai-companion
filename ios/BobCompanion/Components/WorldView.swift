// The living world, inside the app (report «Экраны защита и скорость фронтенда», stage 1).
//
// The WebGPU page that ios/world/build.mjs builds from ios/design/world.html into BobCompanion/World, shown in a
// closed web view:
//  · served from the app bundle through our own scheme, bobworld://world/…, never file:// and never the network.
//    Only files inside World/ are served, and the page gets the same strict Content-Security-Policy it carries
//    (scripts only from the app, WebAssembly but no eval, no connections out);
//  · it may not navigate anywhere, open windows, preview links or use the microphone; nothing it stores outlives it;
//  · the app speaks to it only through window.bobWorld (callAsyncJavaScript, values passed as arguments, never pasted
//    into code), and hears it only through one message handler, «bob», whose messages are checked;
//  · if its process dies, a new one is made — with the lighter look after a second fall;
//  · it is told when the phone is warm or in Low Power Mode, and paused while a screen of the app covers it.
// The app's own screens (the questions, the paywall, the menu) are SwiftUI over it.

import SwiftUI
import WebKit

// MARK: - serving the bundle's World folder through our own scheme

final class WorldScheme: NSObject, WKURLSchemeHandler {
    static let scheme = "bobworld", host = "world"
    private let root: URL
    private let policy: String

    init(root: URL) {
        self.root = root.standardizedFileURL
        let csp = try? String(contentsOf: root.appendingPathComponent("CSP.txt"), encoding: .utf8)
        // (without its own policy file the page is served with one that lets nothing run: it fails closed)
        self.policy = csp?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "default-src 'none'"
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, url.scheme == Self.scheme, url.host == Self.host else { return refuse(task, 400) }
        let path = url.path.isEmpty || url.path == "/" ? "index.html" : String(url.path.dropFirst())
        let file = root.appendingPathComponent(path).standardizedFileURL.resolvingSymlinksInPath()
        // only inside World/ — no "..", no link leading out of it
        guard file.path.hasPrefix(root.resolvingSymlinksInPath().path + "/"),
              let data = try? Data(contentsOf: file, options: .mappedIfSafe) else { return refuse(task, 404) }
        var headers = ["Content-Type": Self.type(of: file.pathExtension), "Content-Length": "\(data.count)",
                       "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"]
        if file.pathExtension == "html" { headers["Content-Security-Policy"] = policy }
        guard let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers) else {
            return refuse(task, 500)
        }
        task.didReceive(response)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}

    private func refuse(_ task: WKURLSchemeTask, _ status: Int) {
        guard let url = task.request.url,
              let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: "HTTP/1.1", headerFields: ["Content-Length": "0"])
        else { return task.didFailWithError(URLError(.badURL)) }
        task.didReceive(response)
        task.didFinish()
    }

    private static func type(of ext: String) -> String {
        switch ext.lowercased() {
        case "html": return "text/html; charset=utf-8"
        case "js":   return "text/javascript; charset=utf-8"
        case "css":  return "text/css; charset=utf-8"
        case "json": return "application/json"
        case "wasm": return "application/wasm"
        case "jpg", "jpeg": return "image/jpeg"
        case "png":  return "image/png"
        case "webp": return "image/webp"
        case "txt":  return "text/plain; charset=utf-8"
        default:     return "application/octet-stream"
        }
    }
}

/// The message handler holds the world weakly: WKUserContentController keeps its handlers alive, and a strong one
/// would keep the whole web view alive with it.
private final class WeakHandler: NSObject, WKScriptMessageHandler {
    weak var target: WKScriptMessageHandler?
    init(_ target: WKScriptMessageHandler) { self.target = target }
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) { target?.userContentController(c, didReceive: m) }
}

// MARK: - the world

@MainActor
final class World: NSObject, ObservableObject {
    /// Drawn whole — its sky done, its haze warm. Until then the app keeps its dark over it.
    @Published private(set) var ready = false
    /// Bumped each time a new web view is made (after its process died), so the view hosting it re-attaches.
    @Published private(set) var generation = 0
    private(set) var webView: WKWebView!
    private var falls = 0
    private var paused = false
    private var watchers: [NSObjectProtocol] = []

    override init() {
        super.init()
        build()
        let center = NotificationCenter.default
        for name in [ProcessInfo.thermalStateDidChangeNotification, Notification.Name.NSProcessInfoPowerStateDidChange] {
            watchers.append(center.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                Task { @MainActor in self?.tellPhone() }
            })
        }
    }

    deinit { watchers.forEach(NotificationCenter.default.removeObserver) }

    private func build() {
        guard let root = Bundle.main.url(forResource: "World", withExtension: nil) else {
            assertionFailure("World/ is missing from the app — run ios/world: npm run build"); return
        }
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()                    // nothing it keeps outlives it
        config.setURLSchemeHandler(WorldScheme(root: root), forURLScheme: WorldScheme.scheme)
        config.userContentController.add(WeakHandler(self), contentWorld: .page, name: "bob")
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        config.mediaTypesRequiringUserActionForPlayback = .all
        config.defaultWebpagePreferences.allowsContentJavaScript = true

        let web = WKWebView(frame: .zero, configuration: config)
        web.isOpaque = true
        web.backgroundColor = .black
        web.scrollView.backgroundColor = .black
        web.scrollView.isScrollEnabled = false
        web.scrollView.bounces = false
        web.scrollView.contentInsetAdjustmentBehavior = .never         // the world goes under the island and the home bar
        web.allowsLinkPreview = false
        web.allowsBackForwardNavigationGestures = false
        web.navigationDelegate = self
        web.uiDelegate = self
        #if DEBUG
        if #available(iOS 16.4, *) { web.isInspectable = true }        // Safari's Web Inspector, on this Mac only
        #endif
        webView = web
        ready = false
        generation += 1

        var address = URLComponents()
        address.scheme = WorldScheme.scheme
        address.host = WorldScheme.host
        address.path = "/index.html"
        address.queryItems = [URLQueryItem(name: "clean", value: nil), URLQueryItem(name: "wide", value: String(format: "%.3f", Self.widest))]
            + (falls > 1 ? [URLQueryItem(name: "light", value: nil)] : [])
        if let url = address.url { web.load(URLRequest(url: url)) }
    }

    /// The widest this screen can ever be (width/height): a phone stays upright; a tablet or an unfolded phone turns.
    private static var widest: Double {
        let b = UIScreen.main.bounds, short = min(b.width, b.height), long = max(b.width, b.height)
        return short >= 600 ? Double(long/short) : 0.62
    }

    // MARK: what the app tells him (values are passed as arguments, and the page checks them again)

    func set(way: String? = nil, act: String? = nil, level: Double? = nil, hue: Double? = nil, known: Int? = nil, flare: Int? = nil) {
        var b: [String: Any] = [:]
        if let way { b["way"] = way }
        if let act { b["act"] = act }
        if let level { b["level"] = level }
        if let hue { b["hue"] = hue }
        if let known { b["known"] = known }
        if let flare { b["flare"] = flare }
        call("window.bobWorld?.set(b)", ["b": b])
    }

    func mood(valence: Double, arousal: Double) { call("window.bobWorld?.mood(v, a)", ["v": valence, "a": arousal]) }

    /// A screen of the app covers the world: no need to draw what nobody sees.
    func pause() { guard !paused else { return }; paused = true; call("window.bobWorld?.pause()") }
    func resume() { guard paused else { return }; paused = false; call("window.bobWorld?.resume()") }

    /// Low Power Mode or a serious heat → thirty frames; a critical heat → thirty and fewer pixels (Apple: at serious and
    /// critical, cut the work). A slightly warm phone (.fair) is left to the page's own pace.
    func tellPhone() {
        let info = ProcessInfo.processInfo
        let level: Int
        switch info.thermalState {
        case .critical: level = 2
        case .serious:  level = 1
        default:        level = info.isLowPowerModeEnabled ? 1 : 0
        }
        call("window.bobWorld?.phone(l)", ["l": level])
    }

    private func call(_ code: String, _ args: [String: Any] = [:]) {
        guard ready else { return }
        webView.callAsyncJavaScript(code, arguments: args, in: nil, in: .page) { _ in }
    }
}

// MARK: - what the world may do, and what it may say

extension World: WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    /// Only our own page, in the main frame. Every other address — a link, a redirect, anything — goes nowhere.
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping @MainActor (WKNavigationActionPolicy) -> Void) {
        let url = action.request.url
        let ours = url?.scheme == WorldScheme.scheme && url?.host == WorldScheme.host && action.targetFrame?.isMainFrame == true
        decisionHandler(ours ? .allow : .cancel)
    }

    /// No new windows, ever.
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? { nil }

    /// The world never hears: the microphone is the app's, recorded natively.
    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin, initiatedByFrame frame: WKFrameInfo,
                 type: WKMediaCaptureType, decisionHandler: @escaping @MainActor (WKPermissionDecision) -> Void) {
        decisionHandler(.deny)
    }

    /// Its process died (out of memory, or iOS reclaimed it): a new web view, not a reload — and after a second fall,
    /// the lighter look.
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        falls += 1
        build()
    }

    /// One handler, «bob»: only from our page's main frame, only small dictionaries with a known type.
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        let origin = message.frameInfo.securityOrigin
        guard message.name == "bob", message.frameInfo.isMainFrame,
              origin.protocol == WorldScheme.scheme, origin.host == WorldScheme.host,
              let body = message.body as? [String: Any], body.count <= 8,
              let type = body["type"] as? String, type.count <= 32 else { return }
        switch type {
        case "ready":
            ready = true
            tellPhone()
        default:
            break                                                        // (unknown: dropped)
        }
    }
}

// MARK: - SwiftUI

/// The world, full screen, under everything. Dark until it is drawn whole, then it comes up as the film does.
struct WorldView: View {
    @ObservedObject var world: World

    var body: some View {
        WorldHost(world: world)
            .overlay(Color.black.opacity(world.ready ? 0 : 1).animation(.easeOut(duration: 1.6), value: world.ready))
            .ignoresSafeArea()
            .accessibilityHidden(true)                                   // (scenery: VoiceOver reads the app's screens over it)
    }
}

private struct WorldHost: UIViewRepresentable {
    @ObservedObject var world: World

    func makeUIView(context: Context) -> UIView {
        let host = UIView()
        host.backgroundColor = .black
        attach(to: host)
        return host
    }

    func updateUIView(_ host: UIView, context: Context) {
        if world.webView?.superview !== host { attach(to: host) }       // (a new web view after a fall)
    }

    private func attach(to host: UIView) {
        guard let web = world.webView else { return }
        host.subviews.forEach { $0.removeFromSuperview() }
        web.translatesAutoresizingMaskIntoConstraints = false
        host.addSubview(web)
        NSLayoutConstraint.activate([
            web.leadingAnchor.constraint(equalTo: host.leadingAnchor), web.trailingAnchor.constraint(equalTo: host.trailingAnchor),
            web.topAnchor.constraint(equalTo: host.topAnchor), web.bottomAnchor.constraint(equalTo: host.bottomAnchor),
        ])
    }
}

#if DEBUG
/// For looking (launch with -worldPreview): the world alone, and a few switches to try its door.
struct WorldPreview: View {
    @StateObject private var world = World()
    @State private var flare = 3

    var body: some View {
        ZStack(alignment: .bottom) {
            WorldView(world: world)
            HStack(spacing: 10) {
                Button("слушает") { world.set(way: "listen", act: "mark") }
                Button("прыжок") { world.set(act: "jump") }
                Button("☀ \(flare + 1)/4") { flare = (flare + 1) % 4; world.set(flare: flare) }
                Button("пауза") { world.pause() }
                Button("дальше") { world.resume() }
            }
            .font(.footnote)
            .buttonStyle(.bordered)
            .tint(.white)
            .padding(.bottom, 24)
        }
        .preferredColorScheme(.dark)
        // (-worldPreviewMark: once drawn, the app tells him to come and listen — proof the app's word reaches him)
        .onChange(of: world.ready) { _, ready in
            if ready, ProcessInfo.processInfo.arguments.contains("-worldPreviewMark") { world.set(way: "listen", act: "mark") }
        }
    }
}
#endif

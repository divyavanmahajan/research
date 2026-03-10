#!/usr/bin/env swift
// samsung-tv.swift — Samsung TV Remote CLI
// Run with:  swift samsung-tv.swift <command> [args...]
//
// Commands: connect, status, key, app, scan, forget, keys, apps, doctor

import Foundation
import Darwin

// ── ANSI colours ─────────────────────────────────────────────────────────────

let RESET = "\u{001B}[0m"
let BOLD  = "\u{001B}[1m"
let RED   = "\u{001B}[31m"
let GRN   = "\u{001B}[32m"
let YEL   = "\u{001B}[33m"
let CYN   = "\u{001B}[36m"

func section(_ s: String) { print("\n\(BOLD)\(CYN)── \(s) ──\(RESET)") }
func info(_ s: String)    { print("   \(s)") }
func ok(_ s: String)      { print("   \(GRN)✓\(RESET)  \(s)") }
func warn(_ s: String)    { print("   \(YEL)⚠\(RESET)  \(s)") }
func fail(_ s: String)    { print("   \(RED)✗\(RESET)  \(s)") }

func die(_ s: String) -> Never {
    fail(s)
    exit(1)
}

// ── Config persistence ────────────────────────────────────────────────────────

let CONFIG_PATH = (NSHomeDirectory() as NSString).appendingPathComponent(".samsung-tv.json")

struct TVConfig: Codable {
    var ip: String
    var name: String
    var token: String
}

func loadConfig() -> TVConfig? {
    let url = URL(fileURLWithPath: CONFIG_PATH)
    guard let data = try? Data(contentsOf: url),
          let config = try? JSONDecoder().decode(TVConfig.self, from: data) else {
        return nil
    }
    return config
}

func saveConfig(_ config: TVConfig) {
    guard let data = try? JSONEncoder().encode(config) else {
        warn("Could not encode config for saving.")
        return
    }
    // Pretty-print
    if let json = try? JSONSerialization.jsonObject(with: data),
       let pretty = try? JSONSerialization.data(withJSONObject: json, options: .prettyPrinted) {
        try? pretty.write(to: URL(fileURLWithPath: CONFIG_PATH))
    } else {
        try? data.write(to: URL(fileURLWithPath: CONFIG_PATH))
    }
}

func maskToken(_ token: String) -> String {
    guard token.count > 3 else { return "***" }
    return String(token.prefix(3)) + "***"
}

// ── Known apps ────────────────────────────────────────────────────────────────

let knownApps: [(aliases: [String], name: String, appId: String)] = [
    (["livetv", "live", "tv"],             "Live TV",       "__key:KEY_TV"),
    (["netflix"],                          "Netflix",       "3201907018807"),
    (["youtube"],                          "YouTube",       "111299001912"),
    (["disney", "disney+"],                "Disney+",       "3201901017640"),
    (["prime", "primevideo", "amazon"],    "Prime Video",   "3201910019365"),
    (["appletv", "appletvplus"],           "Apple TV+",     "3201807016597"),
    (["spotify"],                          "Spotify",       "3201606009684"),
]

func resolveApp(_ name: String) -> (name: String, appId: String)? {
    let lower = name.lowercased()
    for entry in knownApps {
        if entry.aliases.contains(lower) {
            return (entry.name, entry.appId)
        }
    }
    return nil
}

// ── Known keys ────────────────────────────────────────────────────────────────

let keyAliases: [String: String] = [
    "volup":       "KEY_VOLUP",
    "volumeup":    "KEY_VOLUP",
    "voldown":     "KEY_VOLDOWN",
    "volumedown":  "KEY_VOLDOWN",
    "mute":        "KEY_MUTE",
    "play":        "KEY_PLAY",
    "pause":       "KEY_PLAY",
    "playpause":   "KEY_PLAY",
    "chup":        "KEY_CHUP",
    "channelup":   "KEY_CHUP",
    "chdown":      "KEY_CHDOWN",
    "channeldown": "KEY_CHDOWN",
    "up":          "KEY_UP",
    "down":        "KEY_DOWN",
    "left":        "KEY_LEFT",
    "right":       "KEY_RIGHT",
    "ok":          "KEY_ENTER",
    "enter":       "KEY_ENTER",
    "select":      "KEY_ENTER",
    "back":        "KEY_RETURN",
    "return":      "KEY_RETURN",
    "home":        "KEY_HOME",
    "menu":        "KEY_MENU",
    "power":       "KEY_POWER",
]

func resolveKey(_ name: String) -> String {
    let lower = name.lowercased()
    if let mapped = keyAliases[lower] { return mapped }
    // Pass KEY_* through unchanged
    if name.uppercased().hasPrefix("KEY_") { return name.uppercased() }
    return name.uppercased()
}

// ── TLS delegate (accept self-signed certs) ───────────────────────────────────

class TLSDelegate: NSObject, URLSessionDelegate, URLSessionWebSocketDelegate {
    var onOpen:  (() -> Void)?
    var onClose: ((URLSessionWebSocketTask.CloseCode, Data?) -> Void)?

    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
           let trust = challenge.protectionSpace.serverTrust {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didOpenWithProtocol proto: String?) {
        onOpen?()
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        onClose?(closeCode, reason)
    }
}

// ── WebSocket constants ───────────────────────────────────────────────────────

let APP_NAME     = "SamsungTVCLI"
let APP_NAME_B64 = Data(APP_NAME.utf8).base64EncodedString()
let WS_PORT      = 8002

func makeWSURL(ip: String, token: String?) -> URL? {
    var comps = URLComponents()
    comps.scheme     = "wss"
    comps.host       = ip
    comps.port       = WS_PORT
    comps.path       = "/api/v2/channels/samsung.remote.control"
    var items        = [URLQueryItem(name: "name", value: APP_NAME_B64)]
    if let t = token, !t.isEmpty { items.append(URLQueryItem(name: "token", value: t)) }
    comps.queryItems = items
    return comps.url
}

// ── WebSocket connector ───────────────────────────────────────────────────────

enum WSResult {
    case connected(token: String?)
    case unauthorized
    case timeout
    case error(String)
}

/// Attempt a single WSS connection. Returns immediately with result.
func wsConnect(ip: String, token: String?, timeoutSecs: Double = 20.0) -> WSResult {
    guard let url = makeWSURL(ip: ip, token: token) else {
        return .error("Cannot build WebSocket URL")
    }

    let delegate = TLSDelegate()
    let session  = URLSession(configuration: .default, delegate: delegate, delegateQueue: nil)
    let task     = session.webSocketTask(with: url)

    var result: WSResult = .timeout
    let sem = DispatchSemaphore(value: 0)
    var signalled = false

    func signal(_ r: WSResult) {
        guard !signalled else { return }
        signalled = true
        result = r
        sem.signal()
    }

    func listen() {
        task.receive { res in
            switch res {
            case .success(let msg):
                if case .string(let text) = msg {
                    if text.contains("ms.channel.connect") {
                        var pairingToken: String? = nil
                        if let data = text.data(using: .utf8),
                           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                           let dDict = json["data"] as? [String: Any] {
                            pairingToken = dDict["token"] as? String
                        }
                        signal(.connected(token: pairingToken))
                    } else if text.contains("ms.channel.unauthorized") {
                        signal(.unauthorized)
                    }
                }
                if !signalled { listen() }
            case .failure:
                signal(.timeout)
            }
        }
    }

    task.resume()
    listen()

    let deadline = DispatchTime.now() + timeoutSecs
    _ = sem.wait(timeout: deadline)
    task.cancel(with: .goingAway, reason: nil)
    session.invalidateAndCancel()
    return result
}

// ── REST API helpers ──────────────────────────────────────────────────────────

func restGet(ip: String, path: String = "/api/v2/", timeout: Double = 5.0) -> [String: Any]? {
    guard let url = URL(string: "http://\(ip):8001\(path)") else { return nil }
    let sem = DispatchSemaphore(value: 0)
    var result: [String: Any]? = nil
    URLSession.shared.dataTask(with: URLRequest(url: url, timeoutInterval: timeout)) { data, resp, _ in
        defer { sem.signal() }
        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
        result = json
    }.resume()
    sem.wait()
    return result
}

func restPost(ip: String, path: String, timeout: Double = 5.0) -> Bool {
    guard let url = URL(string: "http://\(ip):8001\(path)") else { return false }
    var req = URLRequest(url: url, timeoutInterval: timeout)
    req.httpMethod = "POST"
    let sem = DispatchSemaphore(value: 0)
    var success = false
    URLSession.shared.dataTask(with: req) { data, resp, _ in
        defer { sem.signal() }
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        // TV returns HTTP 200/204 or "true" body
        if code == 200 || code == 204 { success = true }
        if let data = data,
           let body = String(data: data, encoding: .utf8),
           body.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "true" {
            success = true
        }
    }.resume()
    sem.wait()
    return success
}

func fetchTVInfo(ip: String) -> (name: String, modelName: String?, powerState: String?, os: String?, networkType: String?)? {
    guard let json = restGet(ip: ip) else { return nil }
    let name = (json["name"] as? String) ?? "Samsung TV"
    let device = json["device"] as? [String: Any]
    let modelName    = device?["modelName"]    as? String
    let powerState   = device?["PowerState"]   as? String
    let osVersion    = device?["OS"]           as? String
    let networkType  = device?["networkType"]  as? String
    return (name: name, modelName: modelName, powerState: powerState, os: osVersion, networkType: networkType)
}

// ── Key sender ────────────────────────────────────────────────────────────────

func sendKey(_ keyCode: String, ip: String, token: String) -> Bool {
    guard let url = makeWSURL(ip: ip, token: token) else { return false }

    let delegate = TLSDelegate()
    let session  = URLSession(configuration: .default, delegate: delegate, delegateQueue: nil)
    let task     = session.webSocketTask(with: url)

    let sem = DispatchSemaphore(value: 0)
    var connected = false
    var signalled = false

    func signal() {
        guard !signalled else { return }
        signalled = true
        sem.signal()
    }

    task.receive { res in
        if case .success(let msg) = res, case .string(let text) = msg {
            if text.contains("ms.channel.connect") {
                connected = true
            }
        }
        signal()
    }

    task.resume()
    _ = sem.wait(timeout: .now() + 10)

    guard connected else {
        task.cancel(with: .goingAway, reason: nil)
        session.invalidateAndCancel()
        return false
    }

    let payload: [String: Any] = [
        "method": "ms.remote.control",
        "params": [
            "Cmd":          "Click",
            "DataOfCmd":    keyCode,
            "Option":       "false",
            "TypeOfRemote": "SendRemoteKey",
        ]
    ]
    guard let data = try? JSONSerialization.data(withJSONObject: payload),
          let text = String(data: data, encoding: .utf8) else {
        task.cancel(with: .goingAway, reason: nil)
        session.invalidateAndCancel()
        return false
    }

    let sendSem = DispatchSemaphore(value: 0)
    var sendOK  = false
    task.send(.string(text)) { err in
        sendOK = (err == nil)
        sendSem.signal()
    }
    sendSem.wait()

    // Brief pause to let TV process the key
    Thread.sleep(forTimeInterval: 0.3)
    task.cancel(with: .goingAway, reason: nil)
    session.invalidateAndCancel()
    return sendOK
}

// ── TCP reachability probe ────────────────────────────────────────────────────

func tcpProbe(ip: String, port: UInt16, timeoutSecs: Double = 3.0) -> Bool {
    let sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    guard sock >= 0 else { return false }
    defer { close(sock) }

    // Set non-blocking
    let flags = fcntl(sock, F_GETFL, 0)
    _ = fcntl(sock, F_SETFL, flags | O_NONBLOCK)

    var addr = sockaddr_in()
    addr.sin_family      = sa_family_t(AF_INET)
    addr.sin_addr.s_addr = inet_addr(ip)
    addr.sin_port        = port.bigEndian

    let cr = withUnsafePointer(to: &addr) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            connect(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }

    if cr == 0 { return true }          // immediate success (rare)
    guard errno == EINPROGRESS else { return false }

    // select() for timeout
    var writeFDs = fd_set()
    withUnsafeMutablePointer(to: &writeFDs) { ptr in
        ptr.pointee = fd_set()
    }
    // Manual FD_SET equivalent
    let fdIndex  = Int(sock) / 32
    let fdBit    = Int(sock) % 32
    withUnsafeMutableBytes(of: &writeFDs) { raw in
        let words = raw.bindMemory(to: Int32.self)
        words[fdIndex] |= Int32(bitPattern: 1 << fdBit)
    }

    var tv = timeval(tv_sec: Int(timeoutSecs), tv_usec: 0)
    let n  = select(sock + 1, nil, &writeFDs, nil, &tv)
    guard n > 0 else { return false }

    // Check SO_ERROR
    var errVal: Int32 = 0
    var errLen = socklen_t(MemoryLayout<Int32>.size)
    getsockopt(sock, SOL_SOCKET, SO_ERROR, &errVal, &errLen)
    return errVal == 0
}

// ── SSDP scan ─────────────────────────────────────────────────────────────────

func xmlValue(_ tag: String, in xml: String) -> String? {
    let o = "<\(tag)>", c = "</\(tag)>"
    guard let s = xml.range(of: o),
          let e = xml.range(of: c, range: s.upperBound ..< xml.endIndex) else { return nil }
    return String(xml[s.upperBound ..< e.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
}

struct FoundTV {
    var ip: String
    var friendlyName: String
    var modelName: String?
}

func ssdpScan(listenSeconds: Double = 5.0) -> [FoundTV] {
    let SSDP_ADDR = "239.255.255.250"
    let SSDP_PORT: UInt16 = 1900
    let target = "urn:samsung.com:device:RemoteControlReceiver:1"

    let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    guard sock >= 0 else { fail("socket() failed"); return [] }
    defer { close(sock) }

    var yes: Int32 = 1
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
    setsockopt(sock, SOL_SOCKET, SO_REUSEPORT, &yes, socklen_t(MemoryLayout<Int32>.size))

    var local = sockaddr_in()
    local.sin_family      = sa_family_t(AF_INET)
    local.sin_addr.s_addr = INADDR_ANY
    local.sin_port        = 0
    _ = withUnsafePointer(to: &local) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            bind(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }

    var tv = timeval(tv_sec: Int(listenSeconds), tv_usec: 0)
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))

    var dest = sockaddr_in()
    dest.sin_family      = sa_family_t(AF_INET)
    dest.sin_addr.s_addr = inet_addr(SSDP_ADDR)
    dest.sin_port        = SSDP_PORT.bigEndian

    let msg = [
        "M-SEARCH * HTTP/1.1",
        "HOST: \(SSDP_ADDR):\(SSDP_PORT)",
        "MAN: \"ssdp:discover\"",
        "MX: 3",
        "ST: \(target)",
        "", "",
    ].joined(separator: "\r\n")

    _ = msg.withCString { ptr in
        withUnsafePointer(to: &dest) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                sendto(sock, ptr, strlen(ptr), 0, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
    }

    var locations = Set<String>()
    var buf = [CChar](repeating: 0, count: 8192)

    while true {
        let n = recv(sock, &buf, buf.count - 1, 0)
        guard n > 0 else { break }
        buf[Int(n)] = 0
        let response = String(cString: buf)
        for line in response.components(separatedBy: "\r\n") {
            if line.lowercased().hasPrefix("location:") {
                let loc = String(line.dropFirst("location:".count)).trimmingCharacters(in: .whitespaces)
                locations.insert(loc)
            }
        }
    }

    // Resolve each LOCATION URL
    var found: [FoundTV] = []
    for loc in locations {
        guard let url = URL(string: loc), let host = url.host else { continue }

        let sem = DispatchSemaphore(value: 0)
        var xml = ""
        URLSession.shared.dataTask(with: URLRequest(url: url, timeoutInterval: 5)) { data, _, _ in
            defer { sem.signal() }
            xml = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
        }.resume()
        sem.wait()

        guard !xml.isEmpty else { continue }
        let friendlyName = xmlValue("friendlyName", in: xml) ?? xmlValue("modelName", in: xml) ?? "Samsung TV"

        // Also probe REST API for modelName
        var modelName: String? = nil
        if let json = restGet(ip: host, timeout: 3),
           let device = json["device"] as? [String: Any] {
            modelName = device["modelName"] as? String
        }
        found.append(FoundTV(ip: host, friendlyName: friendlyName, modelName: modelName))
    }
    return found
}

// ── Troubleshooting text ──────────────────────────────────────────────────────

func printUnauthorizedHelp() {
    print("""
\(YEL)
  The TV is showing a pairing popup. Steps:
    1. Look at the TV screen now — a dialog should say "Allow remote control?"
    2. Use the TV remote to select "Allow".
    3. If no popup appeared:
       a. On the TV go to Settings → General → External Device Manager
          → Device Connect Manager → Access Notification
       b. Set it to "First Time Only" (not "Never").
       c. If it was already "First Time Only", the TV may have a stored
          decision. Go to the same menu, open "Allowed/Blocked Devices",
          and remove this device's entry, then retry.
    4. After accepting, the CLI will automatically reconnect.\(RESET)
""")
}

func printTimeoutHelp(ip: String) {
    print("""
\(RED)
  ✗ Could not connect. Check:
    1. TV and this Mac are on the same Wi-Fi network.
    2. TV is powered on (not in deep sleep — try the power button first).
    3. Port 8002 is not blocked by a router firewall.
    4. Run: swift samsung-tv.swift doctor   for a full step-by-step diagnosis.\(RESET)
""")
}

// ── Table printer ─────────────────────────────────────────────────────────────

func printTable(headers: [String], rows: [[String]]) {
    var widths = headers.map { $0.count }
    for row in rows {
        for (i, cell) in row.enumerated() {
            if i < widths.count { widths[i] = max(widths[i], cell.count) }
        }
    }
    func pad(_ s: String, _ w: Int) -> String { s + String(repeating: " ", count: max(0, w - s.count)) }
    let sep = "+" + widths.map { String(repeating: "-", count: $0 + 2) }.joined(separator: "+") + "+"
    let headerLine = "| " + zip(headers, widths).map { pad($0, $1) }.joined(separator: " | ") + " |"
    print(sep)
    print(headerLine)
    print(sep)
    for row in rows {
        let cells = row.enumerated().map { (i, c) in pad(c, i < widths.count ? widths[i] : c.count) }
        print("| " + cells.joined(separator: " | ") + " |")
    }
    print(sep)
}

// ═══════════════════════════════════════════════════════════════════════════════
// MARK: - Commands
// ═══════════════════════════════════════════════════════════════════════════════

// ── connect [IP] ──────────────────────────────────────────────────────────────

func cmdConnect(args: [String]) {
    let argIP = args.first

    // Resolve IP to use
    let ip: String
    if let a = argIP, !a.isEmpty {
        ip = a
    } else if let saved = loadConfig() {
        info("No IP given — using saved IP: \(saved.ip)")
        ip = saved.ip
    } else {
        die("No IP address given and no saved config.\n   Usage: swift samsung-tv.swift connect <IP>")
    }

    section("Connecting to Samsung TV at \(ip)")

    // Fetch TV name from REST API
    var tvName = "Samsung TV"
    if let info_ = fetchTVInfo(ip: ip) {
        tvName = info_.name
        ok("REST API reachable — \(tvName)")
    } else {
        warn("REST API not reachable at http://\(ip):8001/api/v2/ — continuing anyway")
    }

    // First WSS connection attempt (with saved token if available)
    let savedToken = loadConfig()?.token

    info("Attempting WSS connection (port \(WS_PORT))…")
    var result = wsConnect(ip: ip, token: savedToken, timeoutSecs: 20)

    if case .unauthorized = result {
        printUnauthorizedHelp()
        info("Waiting 25 seconds for you to accept the popup on the TV…")
        Thread.sleep(forTimeInterval: 25)
        info("Reconnecting…")
        result = wsConnect(ip: ip, token: nil, timeoutSecs: 20)
    }

    switch result {
    case .connected(let token):
        let finalToken = token ?? savedToken ?? ""
        let config = TVConfig(ip: ip, name: tvName, token: finalToken)
        saveConfig(config)
        ok("Connected to \"\(tvName)\"")
        info("IP:    \(ip)")
        info("Token: \(finalToken)")
        info("Config saved to \(CONFIG_PATH)")

    case .unauthorized:
        fail("Still unauthorized after waiting.")
        printUnauthorizedHelp()
        exit(1)

    case .timeout:
        fail("Connection timed out.")
        printTimeoutHelp(ip: ip)
        exit(1)

    case .error(let msg):
        fail("Connection error: \(msg)")
        printTimeoutHelp(ip: ip)
        exit(1)
    }
}

// ── status ────────────────────────────────────────────────────────────────────

func cmdStatus() {
    guard let config = loadConfig() else {
        die("No saved config. Run: swift samsung-tv.swift connect <IP>")
    }

    section("Saved Config")
    info("Name:  \(config.name)")
    info("IP:    \(config.ip)")
    info("Token: \(config.token)")

    section("REST API  http://\(config.ip):8001/api/v2/")
    if let tvInfo = fetchTVInfo(ip: config.ip) {
        ok("Reachable")
        if let ps  = tvInfo.powerState  { info("PowerState:  \(ps)") }
        if let mn  = tvInfo.modelName   { info("Model:       \(mn)") }
        if let os  = tvInfo.os          { info("OS:          \(os)") }
        if let nt  = tvInfo.networkType { info("Network:     \(nt)") }
    } else {
        fail("REST API not reachable")
    }

    section("WebSocket  wss://\(config.ip):\(WS_PORT)")
    let result = wsConnect(ip: config.ip, token: config.token, timeoutSecs: 10)
    switch result {
    case .connected:      ok("Connected")
    case .unauthorized:   warn("Unauthorized (token may be expired — re-run connect)")
    case .timeout:        fail("Timeout")
    case .error(let msg): fail("Error: \(msg)")
    }
}

// ── key KEY [KEY2 ...] ────────────────────────────────────────────────────────

func cmdKey(args: [String]) {
    guard !args.isEmpty else {
        die("Usage: swift samsung-tv.swift key <KEY> [KEY2 ...]")
    }
    guard let config = loadConfig() else {
        die("No saved config. Run: swift samsung-tv.swift connect <IP> first.")
    }

    section("Sending keys to \(config.name)")

    for rawKey in args {
        let keyCode = resolveKey(rawKey)
        info("Sending \(keyCode)…")

        if sendKey(keyCode, ip: config.ip, token: config.token) {
            ok("\(keyCode) sent")
        } else {
            fail("Failed to send \(keyCode) — try reconnecting: swift samsung-tv.swift connect")
        }
    }
}

// ── app NAME ──────────────────────────────────────────────────────────────────

func cmdApp(args: [String]) {
    guard let appName = args.first else {
        die("Usage: swift samsung-tv.swift app <name>  (e.g. netflix, youtube, disney)")
    }
    guard let config = loadConfig() else {
        die("No saved config. Run: swift samsung-tv.swift connect <IP> first.")
    }
    guard let app = resolveApp(appName) else {
        fail("Unknown app: \(appName)")
        info("Run 'swift samsung-tv.swift apps' to see available apps.")
        exit(1)
    }

    section("Launching \(app.name) on \(config.name)")

    // Apps prefixed with "__key:" send a key press instead of a REST app launch
    if app.appId.hasPrefix("__key:") {
        let keyCode = String(app.appId.dropFirst("__key:".count))
        info("Sending key: \(keyCode)…")
        if sendKey(keyCode, ip: config.ip, token: config.token) {
            ok("\(app.name) key sent (\(keyCode))")
        } else {
            fail("Failed to send key — try reconnecting: swift samsung-tv.swift connect")
        }
        return
    }

    info("App ID: \(app.appId)")
    let success = restPost(ip: config.ip, path: "/api/v2/applications/\(app.appId)")
    if success {
        ok("\(app.name) launch request sent")
    } else {
        fail("Launch request failed — TV may not support this app ID, or TV is off")
        info("Ensure the TV is on and connected to the network.")
    }
}

// ── scan ──────────────────────────────────────────────────────────────────────

func cmdScan() {
    section("SSDP Scan (Samsung TVs on local network)")
    info("Sending M-SEARCH to 239.255.255.250:1900…")
    info("Listening 5 seconds for responses…")

    let found = ssdpScan(listenSeconds: 5)

    if found.isEmpty {
        warn("No Samsung TVs found on the local network.")
        info("Ensure your TV is powered on and on the same Wi-Fi network.")
        info("You can also connect directly: swift samsung-tv.swift connect <IP>")
        return
    }

    print()
    printTable(
        headers: ["IP", "Friendly Name", "Model"],
        rows: found.map { [$0.ip, $0.friendlyName, $0.modelName ?? "—"] }
    )
    print()
    info("To connect to a TV:")
    for tv in found {
        info("  swift samsung-tv.swift connect \(tv.ip)")
    }
}

// ── forget ────────────────────────────────────────────────────────────────────

func cmdForget() {
    let fm = FileManager.default
    if fm.fileExists(atPath: CONFIG_PATH) {
        do {
            try fm.removeItem(atPath: CONFIG_PATH)
            ok("Config deleted: \(CONFIG_PATH)")
        } catch {
            fail("Could not delete config: \(error.localizedDescription)")
            exit(1)
        }
    } else {
        warn("No config file found at \(CONFIG_PATH) — nothing to delete.")
    }
}

// ── keys ──────────────────────────────────────────────────────────────────────

func cmdKeys() {
    section("Supported Key Names")

    let categories: [(String, [(String, String)])] = [
        ("Navigation", [
            ("up",    "KEY_UP"),
            ("down",  "KEY_DOWN"),
            ("left",  "KEY_LEFT"),
            ("right", "KEY_RIGHT"),
            ("ok / enter / select", "KEY_ENTER"),
            ("back / return",       "KEY_RETURN"),
            ("home",  "KEY_HOME"),
            ("menu",  "KEY_MENU"),
        ]),
        ("Volume", [
            ("volup / volumeup",     "KEY_VOLUP"),
            ("voldown / volumedown", "KEY_VOLDOWN"),
            ("mute",                 "KEY_MUTE"),
            ("play / pause / playpause", "KEY_PLAYPAUSE"),
        ]),
        ("Channel", [
            ("chup / channelup",     "KEY_CHUP"),
            ("chdown / channeldown", "KEY_CHDOWN"),
        ]),
        ("System", [
            ("power", "KEY_POWER"),
        ]),
    ]

    for (category, keys) in categories {
        print("\n  \(BOLD)\(CYN)\(category)\(RESET)")
        printTable(headers: ["Friendly Name", "KEY_* Code"], rows: keys.map { [$0.0, $0.1] })
    }
    print()
    info("Raw KEY_* codes are also accepted directly, e.g.: swift samsung-tv.swift key KEY_HOME")
}

// ── apps ──────────────────────────────────────────────────────────────────────

func cmdApps() {
    section("Known Apps")
    printTable(
        headers: ["Name(s)", "App Name", "App ID / Action"],
        rows: knownApps.map { entry in
            let action = entry.appId.hasPrefix("__key:")
                ? "key: \(entry.appId.dropFirst("__key:".count))"
                : entry.appId
            return [entry.aliases.joined(separator: " / "), entry.name, action]
        }
    )
}

// ── doctor ────────────────────────────────────────────────────────────────────

func cmdDoctor(args: [String]) {
    let ip: String
    if let argIP = args.first, !argIP.isEmpty {
        ip = argIP
    } else if let saved = loadConfig() {
        ip = saved.ip
    } else {
        die("No saved config and no IP given.\n   Usage: swift samsung-tv.swift doctor [IP]")
    }

    section("Diagnostics for Samsung TV at \(ip)")
    var allPassed = true

    // Step 1: TCP port 8001 (REST API) as reachability probe
    print("\n  \(BOLD)Step 1: TV reachable (TCP probe on port 8001)\(RESET)")
    if tcpProbe(ip: ip, port: 8001) {
        ok("TCP port 8001 responded — TV is reachable on the network")
    } else {
        fail("TCP port 80 not reachable")
        info("Fix: Ensure TV and Mac are on the same Wi-Fi network.")
        info("     Try: TV on and not in deep sleep mode.")
        allPassed = false
    }

    // Step 2: REST API
    print("\n  \(BOLD)Step 2: REST API  (GET http://\(ip):8001/api/v2/)\(RESET)")
    if let tvInfo = fetchTVInfo(ip: ip) {
        ok("REST API returned HTTP 200")
        info("Name:  \(tvInfo.name)")
        if let mn = tvInfo.modelName   { info("Model: \(mn)") }
        if let ps = tvInfo.powerState  { info("Power: \(ps)") }
    } else {
        fail("REST API not reachable on port 8001")
        info("Fix: TV may be in standby mode — try pressing the power button.")
        info("     Some older models don't support the REST API.")
        allPassed = false
    }

    // Step 3: WebSocket port reachability
    print("\n  \(BOLD)Step 3: WebSocket port 8002 reachable (TCP probe)\(RESET)")
    if tcpProbe(ip: ip, port: 8002) {
        ok("TCP port 8002 is open")
    } else {
        fail("TCP port 8002 not reachable")
        info("Fix: Check router/firewall settings — port 8002 may be blocked.")
        info("     This port must be open for the WebSocket remote to work.")
        allPassed = false
    }

    // Step 4: WebSocket handshake
    print("\n  \(BOLD)Step 4: WebSocket handshake (WSS connect attempt)\(RESET)")
    let savedToken = loadConfig()?.token
    let wsResult   = wsConnect(ip: ip, token: savedToken, timeoutSecs: 10)
    switch wsResult {
    case .connected(let token):
        ok("WebSocket handshake succeeded")
        if let t = token { info("Token: \(t)") }
    case .unauthorized:
        warn("TV returned ms.channel.unauthorized")
        info("The TV has not paired with this remote.")
        printUnauthorizedHelp()
        info("Then run: swift samsung-tv.swift connect \(ip)")
        allPassed = false
    case .timeout:
        fail("WebSocket handshake timed out (10s)")
        printTimeoutHelp(ip: ip)
        allPassed = false
    case .error(let msg):
        fail("WebSocket error: \(msg)")
        allPassed = false
    }

    // Summary
    print()
    if allPassed {
        ok("All diagnostics passed — your TV should be working with this CLI.")
        info("If not already done: swift samsung-tv.swift connect \(ip)")
    } else {
        warn("Some diagnostics failed. Follow the fix instructions above.")
        info("After fixing, retry: swift samsung-tv.swift doctor \(ip)")
    }
}

// ── usage ─────────────────────────────────────────────────────────────────────

func printUsage() {
    print("""

\(BOLD)samsung-tv.swift\(RESET) — Samsung TV Remote CLI

\(BOLD)\(CYN)Usage:\(RESET)
  swift samsung-tv.swift <command> [arguments]

\(BOLD)\(CYN)Commands:\(RESET)
  \(BOLD)connect\(RESET) [IP]        Connect and pair with TV, save credentials
  \(BOLD)status\(RESET)              Show saved config and TV health
  \(BOLD)key\(RESET) KEY [KEY2 ...]  Send one or more remote-control key presses
  \(BOLD)app\(RESET) NAME            Launch a streaming app (netflix, youtube, etc.)
  \(BOLD)scan\(RESET)                Discover Samsung TVs on the local network
  \(BOLD)forget\(RESET)              Delete saved config (~/.samsung-tv.json)
  \(BOLD)keys\(RESET)                Print all supported key names
  \(BOLD)apps\(RESET)                Print all known app names and IDs
  \(BOLD)doctor\(RESET) [IP]         Run step-by-step connection diagnostics

\(BOLD)\(CYN)Examples:\(RESET)
  swift samsung-tv.swift scan
  swift samsung-tv.swift connect 192.168.1.42
  swift samsung-tv.swift key volup volup
  swift samsung-tv.swift key home
  swift samsung-tv.swift app netflix
  swift samsung-tv.swift status
  swift samsung-tv.swift doctor
""")
}

// ═══════════════════════════════════════════════════════════════════════════════
// MARK: - Entry point
// ═══════════════════════════════════════════════════════════════════════════════

let cliArgs = Array(CommandLine.arguments.dropFirst()) // drop script name

guard let command = cliArgs.first else {
    printUsage()
    exit(0)
}

let cmdArgs = Array(cliArgs.dropFirst())

switch command.lowercased() {
case "connect":  cmdConnect(args: cmdArgs)
case "status":   cmdStatus()
case "key":      cmdKey(args: cmdArgs)
case "app":      cmdApp(args: cmdArgs)
case "scan":     cmdScan()
case "forget":   cmdForget()
case "keys":     cmdKeys()
case "apps":     cmdApps()
case "doctor":   cmdDoctor(args: cmdArgs)
case "help", "--help", "-h":
    printUsage()
default:
    fail("Unknown command: \(command)")
    printUsage()
    exit(1)
}

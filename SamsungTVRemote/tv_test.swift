#!/usr/bin/env swift
// tv_test.swift — Samsung TV connection test harness
// Run with:  swift tv_test.swift
//            swift tv_test.swift 192.168.1.45        (skip SSDP, use known IP)
//            swift tv_test.swift 192.168.1.45 12345  (also supply pairing token)

import Foundation
import Darwin

// ── Helpers ──────────────────────────────────────────────────────────────────

let RESET = "\u{001B}[0m"
let BOLD  = "\u{001B}[1m"
let RED   = "\u{001B}[31m"
let GRN   = "\u{001B}[32m"
let YEL   = "\u{001B}[33m"
let CYN   = "\u{001B}[36m"

func step(_ s: String) { print("\n\(BOLD)\(CYN)── \(s) ──\(RESET)") }
func info(_ s: String) { print("   \(s)") }
func ok(_ s: String)   { print("   \(GRN)✓\(RESET)  \(s)") }
func warn(_ s: String) { print("   \(YEL)⚠\(RESET)  \(s)") }
func fail(_ s: String) { print("   \(RED)✗\(RESET)  \(s)") }

func die(_ s: String) -> Never {
    fail(s)
    exit(1)
}

// ── SSDP Discovery ───────────────────────────────────────────────────────────

let SSDP_ADDR = "239.255.255.250"
let SSDP_PORT: UInt16 = 1900

let SSDP_TARGETS = [
    "urn:samsung.com:device:RemoteControlReceiver:1",
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:dial-multiscreen-org:service:dial:1",
]

func ssdpSearch(listenSeconds: Double) -> Set<String> {
    let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    guard sock >= 0 else { fail("socket() failed: \(String(cString: strerror(errno)))"); return [] }
    defer { close(sock) }

    var yes: Int32 = 1
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
    setsockopt(sock, SOL_SOCKET, SO_REUSEPORT, &yes, socklen_t(MemoryLayout<Int32>.size))

    // Bind to ephemeral port to receive unicast M-SEARCH replies
    var local = sockaddr_in()
    local.sin_family      = sa_family_t(AF_INET)
    local.sin_addr.s_addr = INADDR_ANY
    local.sin_port        = 0
    _ = withUnsafePointer(to: &local) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            bind(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }

    var tv = timeval()
    tv.tv_sec  = Int(listenSeconds)
    tv.tv_usec = 0
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))

    var dest = sockaddr_in()
    dest.sin_family      = sa_family_t(AF_INET)
    dest.sin_addr.s_addr = inet_addr(SSDP_ADDR)
    dest.sin_port        = SSDP_PORT.bigEndian

    for target in SSDP_TARGETS {
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
        info("M-SEARCH → \(target)")
    }

    info("Listening \(Int(listenSeconds))s for responses…")
    var locations = Set<String>()
    var buf = [CChar](repeating: 0, count: 8192)

    while true {
        let n = recv(sock, &buf, buf.count - 1, 0)
        guard n > 0 else { break }
        buf[Int(n)] = 0
        let response = String(cString: buf)

        // Print raw response so we can see exactly what the TV said
        info("Raw SSDP response:")
        response.components(separatedBy: "\r\n").forEach { info("  \($0)") }

        for line in response.components(separatedBy: "\r\n") {
            if line.lowercased().hasPrefix("location:") {
                let loc = String(line.dropFirst("location:".count)).trimmingCharacters(in: .whitespaces)
                if locations.insert(loc).inserted {
                    ok("LOCATION: \(loc)")
                }
            }
        }
    }
    return locations
}

// ── Device description XML ────────────────────────────────────────────────────

func xmlValue(_ tag: String, in xml: String) -> String? {
    let o = "<\(tag)>", c = "</\(tag)>"
    guard let s = xml.range(of: o),
          let e = xml.range(of: c, range: s.upperBound ..< xml.endIndex) else { return nil }
    return String(xml[s.upperBound ..< e.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
}

func fetchDescription(location: String) -> (name: String, ip: String)? {
    guard let url = URL(string: location), let host = url.host else { return nil }
    info("Fetching: \(location)")

    let sem  = DispatchSemaphore(value: 0)
    var xml  = ""
    var code = 0

    URLSession.shared.dataTask(with: URLRequest(url: url, timeoutInterval: 5)) { data, resp, err in
        defer { sem.signal() }
        if let err = err { fail("HTTP error: \(err.localizedDescription)"); return }
        code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        xml  = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
    }.resume()
    sem.wait()

    info("HTTP \(code)   XML length: \(xml.count) chars")
    if !xml.isEmpty {
        info("--- Device XML ---")
        print(xml)
        info("-----------------")
    }

    guard xml.localizedCaseInsensitiveContains("samsung") else {
        warn("Not a Samsung device")
        return nil
    }

    let name = xmlValue("friendlyName", in: xml) ?? xmlValue("modelName", in: xml) ?? "Samsung TV"
    return (name: name, ip: host)
}

// ── Samsung REST API (port 8001) ──────────────────────────────────────────────

func fetchRestInfo(ip: String) {
    step("Samsung REST API  http://\(ip):8001/api/v2/")
    guard let url = URL(string: "http://\(ip):8001/api/v2/") else { return }

    let sem = DispatchSemaphore(value: 0)
    URLSession.shared.dataTask(with: URLRequest(url: url, timeoutInterval: 3)) { data, resp, err in
        defer { sem.signal() }
        if let err = err { fail("REST error: \(err.localizedDescription)"); return }
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        info("HTTP \(code)")
        if let data, let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            info("REST response:")
            if let device = json["device"] as? [String: Any] {
                for (k, v) in device.sorted(by: { $0.key < $1.key }) {
                    info("  \(k): \(v)")
                }
            } else {
                info(String(data: try! JSONSerialization.data(withJSONObject: json, options: .prettyPrinted), encoding: .utf8) ?? "")
            }
        }
    }.resume()
    sem.wait()
}

// ── WebSocket test ────────────────────────────────────────────────────────────

let APP_NAME    = "SamsungTVHarness"
let APP_NAME_B64 = Data(APP_NAME.utf8).base64EncodedString()
let WS_PORT     = 8002   // 8002=WSS (encrypted), 8001=WS (plain)
let WS_TIMEOUT  = 30.0

class WSTest: NSObject, URLSessionWebSocketDelegate {
    let ip: String
    var token: String?
    var wsTask: URLSessionWebSocketTask?
    var session: URLSession?

    let ackSem  = DispatchSemaphore(value: 0)
    let doneSem = DispatchSemaphore(value: 0)
    var ackReceived = false
    var gotUnauthorized = false
    var pairingToken: String?

    init(ip: String, token: String?) { self.ip = ip; self.token = token }

    func makeURL(token: String?) -> URL? {
        var c = URLComponents()
        c.scheme = WS_PORT == 8002 ? "wss" : "ws"
        c.host = ip; c.port = WS_PORT
        c.path = "/api/v2/channels/samsung.remote.control"
        var q = [URLQueryItem(name: "name", value: APP_NAME_B64)]
        if let t = token { q.append(URLQueryItem(name: "token", value: t)) }
        c.queryItems = q
        return c.url
    }

    var url: URL? { makeURL(token: token) }

    func connect(withToken t: String?) {
        guard let url = makeURL(token: t) else { fail("Cannot build WS URL"); return }
        info("URL: \(url)")
        session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
        wsTask  = session?.webSocketTask(with: url)
        wsTask?.resume()
        listen()
    }

    func run() -> Bool {
        // First attempt (no token or stored token)
        connect(withToken: token)

        info("Waiting up to \(Int(WS_TIMEOUT))s for ms.channel.connect ack…")
        info(">>> WATCH THE TV SCREEN — accept 'Allow remote control?' if it appears <<<")
        _ = ackSem.wait(timeout: .now() + WS_TIMEOUT)

        if ackReceived { return true }

        // If we got unauthorized, the TV showed a popup — reconnect after user accepts
        if gotUnauthorized {
            warn("Got ms.channel.unauthorized — TV is showing pairing popup on screen")
            info("Waiting 20s for you to accept on the TV screen, then reconnecting…")
            info(">>> ACCEPT THE POPUP ON THE TV NOW <<<")
            Thread.sleep(forTimeInterval: 20)

            // Reset state for second attempt
            gotUnauthorized = false
            ackReceived = false
            // ackSem may be at 0 already; ensure it doesn't block forever
            // by using a fresh WSTest-style reconnect via a new semaphore approach
            let ack2 = DispatchSemaphore(value: 0)
            let session2 = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
            guard let url2 = makeURL(token: nil) else { fail("Cannot build WS URL"); return false }
            info("Reconnecting: \(url2)")
            wsTask = session2.webSocketTask(with: url2)
            wsTask?.resume()
            // Override ackSem signaling for this second attempt via a local listener
            wsTask?.receive { [weak self] result in
                guard let self else { return }
                if case .success(let msg) = result, case .string(let text) = msg {
                    info("← \(text)")
                    if text.contains("ms.channel.connect") {
                        self.ackReceived = true
                        if let data = text.data(using: .utf8),
                           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                           let dDict = json["data"] as? [String: Any],
                           let tok = dDict["token"] as? String {
                            ok("Pairing token: \(tok)  ← save this for next run")
                            self.pairingToken = tok
                            self.token = tok
                        }
                    } else if text.contains("ms.channel.unauthorized") {
                        warn("Still unauthorized — popup may have expired")
                    }
                } else if case .failure(let err) = result {
                    fail("Receive error on reconnect: \(err)")
                }
                ack2.signal()
            }
            _ = ack2.wait(timeout: .now() + WS_TIMEOUT)
            guard ackReceived else {
                fail("Still no ack after reconnect — did you accept the popup on the TV screen?")
                return false
            }
            return true
        }

        fail("Timed out — TV did not send connection ack")
        fail("Possible reasons:")
        fail("  • TV needs to be on the same Wi-Fi network")
        fail("  • Samsung TV may be showing a pairing popup — check the TV screen")
        fail("  • Port 8001 may be blocked (try: nc -zv \(ip) 8001)")
        return false
    }

    /// Try every known Samsung remote-control API variant in order.
    func sendKey(_ key: String) {
        let variants: [(String, [String: Any])] = [
            // ① New API — Tizen 2016+ ("ms.remote.control")
            ("ms.remote.control (new)", [
                "method": "ms.remote.control",
                "params": [
                    "Cmd":          "Click",
                    "DataOfCmd":    key,
                    "Option":       "false",
                    "TypeOfRemote": "SendRemoteKey",
                ]
            ]),
            // ② Old API — MSF 2.x / H-series 2014-2015 ("ms.channel.emit" + "ed.sendKey")
            ("ms.channel.emit/ed.sendKey (old)", [
                "method": "ms.channel.emit",
                "params": [
                    "event": "ed.sendKey",
                    "to":    "host",
                    "data": [
                        "Cmd":          "Click",
                        "DataOfCmd":    key,
                        "Option":       "false",
                        "TypeOfRemote": "SendRemoteKey",
                    ]
                ]
            ]),
            // ③ Old API with base64-encoded key (some 2013-2014 firmware)
            ("ms.channel.emit/ed.sendKey + base64 key", [
                "method": "ms.channel.emit",
                "params": [
                    "event": "ed.sendKey",
                    "to":    "host",
                    "data": [
                        "Cmd":          "Click",
                        "DataOfCmd":    Data(key.utf8).base64EncodedString(),
                        "Option":       "false",
                        "TypeOfRemote": "SendRemoteKey",
                    ]
                ]
            ]),
        ]

        // ── Pre-step: request pairing (some 2014 TVs need this before accepting key events)
        info("── Pre-step: requesting pairing / checking for popup on TV screen")
        let pairingRequest: [String: Any] = [
            "method": "ms.channel.emit",
            "params": [
                "event": "ed.edenTV.inputControlOwnership",
                "to": "host",
                "data": ["ownership": "true"]
            ]
        ]
        if let data = try? JSONSerialization.data(withJSONObject: pairingRequest),
           let text = String(data: data, encoding: .utf8) {
            info("Sending ownership request: \(text)")
            let s = DispatchSemaphore(value: 0)
            wsTask?.send(.string(text)) { _ in s.signal() }
            s.wait()
        }
        info(">>> CHECK TV SCREEN — accept the pairing popup if shown. Waiting 8s… <<<")
        Thread.sleep(forTimeInterval: 8)

        for (label, payload) in variants {
            info("── Trying variant: \(label)")
            guard let data = try? JSONSerialization.data(withJSONObject: payload),
                  let text = String(data: data, encoding: .utf8) else {
                fail("JSON encode failed"); continue
            }
            info("Sending: \(text)")

            let sem = DispatchSemaphore(value: 0)
            wsTask?.send(.string(text)) { err in
                if let err = err { fail("Send error: \(err)") }
                else             { ok("Frame sent — waiting for TV response…") }
                sem.signal()
            }
            sem.wait()

            // Give the TV 2 s to respond (error or silence) before next variant
            Thread.sleep(forTimeInterval: 2)
        }
    }

    func listen() {
        wsTask?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let msg):
                if case .string(let text) = msg {
                    info("← \(text)")
                    if text.contains("ms.channel.connect") {
                        self.ackReceived = true
                        if let data    = text.data(using: .utf8),
                           let json    = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                           let dDict   = json["data"] as? [String: Any],
                           let token   = dDict["token"] as? String {
                            ok("Pairing token: \(token)  ← save this for next run")
                            self.pairingToken = token
                            self.token = token
                        }
                        self.ackSem.signal()
                    } else if text.contains("ms.channel.unauthorized") {
                        warn("Got ms.channel.unauthorized — pairing popup should appear on TV")
                        self.gotUnauthorized = true
                        // Connection will close; signal so run() can handle reconnect
                        self.ackSem.signal()
                    } else if text.contains("ms.error") {
                        fail("TV returned error: \(text)")
                    }
                }
                self.listen()   // keep listening for follow-up messages
            case .failure(let err):
                // Ignore expected close-after-unauthorized; only fail if we didn't handle it
                if !self.gotUnauthorized {
                    fail("Receive error: \(err)")
                    if !self.ackReceived { self.ackSem.signal() }
                }
            }
        }
    }

    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        // Accept Samsung TV self-signed TLS cert
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
           let trust = challenge.protectionSpace.serverTrust {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didOpenWithProtocol p: String?) {
        ok("TCP connection open (waiting for app-level ack…)")
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didCloseWith code: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        let r = reason.flatMap { String(data: $0, encoding: .utf8) } ?? "—"
        warn("WebSocket closed  code=\(code.rawValue)  reason=\(r)")
    }
}

// ── Legacy TCP remote protocol (pre-2016 Samsung TVs, port 55000) ─────────────
//
// Packet format (from samsungctl legacy.py):
//   send_packet(header, payload)
//   → header + [len(payload)] + \x00 + payload
//
// Handshake:  header=\x00\x00\x00  payload=\x64\x00 + ser(localIP) + ser(appName)
// Key:        header=\x00\x00\x00\x01\x00  payload=\x00\x00\x00 + ser(key)
// where ser(s) = [len(s)] + \x00 + s

func legacyLocalIP() -> String {
    var ifaddr: UnsafeMutablePointer<ifaddrs>?
    guard getifaddrs(&ifaddr) == 0 else { return "0.0.0.0" }
    defer { freeifaddrs(ifaddr) }
    var ptr = ifaddr
    while let cur = ptr {
        let fl = Int32(cur.pointee.ifa_flags)
        if (fl & IFF_UP) != 0, (fl & IFF_RUNNING) != 0, (fl & IFF_LOOPBACK) == 0,
           let sa = cur.pointee.ifa_addr, sa.pointee.sa_family == sa_family_t(AF_INET) {
            var h = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            getnameinfo(sa, socklen_t(sa.pointee.sa_len), &h, socklen_t(NI_MAXHOST), nil, 0, NI_NUMERICHOST)
            let ip = String(cString: h)
            if ip != "0.0.0.0" { return ip }
        }
        ptr = cur.pointee.ifa_next
    }
    return "0.0.0.0"
}

func legacySerialize(_ s: String) -> Data {
    let b = Data(s.utf8)
    return Data([UInt8(b.count & 0xFF), 0x00]) + b
}

func legacySendPacket(sock: Int32, header: [UInt8], payload: Data) -> Bool {
    var pkt = Data(header)
    pkt.append(UInt8(payload.count & 0xFF))
    pkt.append(0x00)
    pkt.append(payload)
    return pkt.withUnsafeBytes { ptr in
        send(sock, ptr.baseAddress!, pkt.count, 0) == pkt.count
    }
}

func legacyRecv(sock: Int32) -> String {
    var buf = [UInt8](repeating: 0, count: 1024)
    let n = recv(sock, &buf, buf.count, 0)
    guard n > 0 else { return "(no response / timeout)" }
    let hex = buf[0..<Int(n)].map { String(format: "%02x", $0) }.joined(separator: " ")
    let str = String(bytes: buf[0..<Int(n)], encoding: .utf8) ?? ""
    return "hex=[\(hex)]  ascii=[\(str)]"
}

func tryLegacyProtocol(tvIP: String, key: String) {
    step("Legacy TCP Remote Protocol  \(tvIP):55000")
    let localIP  = legacyLocalIP()
    info("Controller IP: \(localIP)")

    let sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    guard sock >= 0 else { fail("socket() failed"); return }
    defer { close(sock) }

    var tv = sockaddr_in()
    tv.sin_family      = sa_family_t(AF_INET)
    tv.sin_addr.s_addr = inet_addr(tvIP)
    tv.sin_port        = UInt16(55000).bigEndian

    let cr = withUnsafePointer(to: &tv) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            connect(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }
    guard cr == 0 else {
        fail("connect() failed: \(String(cString: strerror(errno)))")
        warn("Port 55000 may not be open on this TV (newer Tizen-only TVs dropped it)")
        return
    }
    ok("TCP connected to port 55000")

    var timeout = timeval(tv_sec: 3, tv_usec: 0)
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))

    // ── Handshake ──
    var handshake = Data([0x64, 0x00])
    handshake.append(legacySerialize(localIP))
    handshake.append(legacySerialize(APP_NAME))

    info("Sending handshake (ip=\(localIP) name=\(APP_NAME))…")
    let sent = legacySendPacket(sock: sock, header: [0x00, 0x00, 0x00], payload: handshake)
    info("Handshake sent: \(sent)")
    info("TV handshake response: \(legacyRecv(sock: sock))")
    // TV may show a pairing dialog; give user time to accept
    info("If TV shows a pairing popup, accept it now. Waiting 5s…")
    Thread.sleep(forTimeInterval: 5)

    // ── Key command ──
    var keyPayload = Data([0x00, 0x00, 0x00])
    keyPayload.append(legacySerialize(key))

    info("Sending key \(key)…")
    let keySent = legacySendPacket(sock: sock, header: [0x00, 0x00, 0x00, 0x01, 0x00], payload: keyPayload)
    info("Key sent: \(keySent)")
    info("TV key response: \(legacyRecv(sock: sock))")
    Thread.sleep(forTimeInterval: 2)
}

// ── Main ─────────────────────────────────────────────────────────────────────

let args = CommandLine.arguments   // [scriptName, optionalIP, optionalToken]

print("\n\(BOLD)Samsung TV Connection Test Harness\(RESET)")
print(String(repeating: "─", count: 40))

// Step 1: resolve TV IP
var tvIP:    String? = args.count > 1 ? args[1] : nil
var tvToken: String? = args.count > 2 ? args[2] : nil
var tvName = "Samsung TV"

if let ip = tvIP {
    info("Using IP from command line: \(ip)")
} else {
    step("SSDP Discovery")
    let locations = ssdpSearch(listenSeconds: 4)

    if locations.isEmpty {
        warn("No SSDP responses received.")
        print("\nEnter TV IP address manually: ", terminator: "")
        fflush(stdout)
        tvIP = readLine()?.trimmingCharacters(in: .whitespaces)
    } else {
        step("Fetching device descriptions")
        for loc in locations {
            if let info = fetchDescription(location: loc) {
                ok("Found: \(info.name) @ \(info.ip)")
                tvIP   = info.ip
                tvName = info.name
                break
            }
        }
        if tvIP == nil {
            warn("SSDP found LOCATIONs but none resolved to a Samsung TV.")
            print("\nEnter TV IP address manually: ", terminator: "")
            fflush(stdout)
            tvIP = readLine()?.trimmingCharacters(in: .whitespaces)
        }
    }
}

guard let ip = tvIP, !ip.isEmpty else { die("No TV IP — cannot continue.") }

// Step 2: REST API info
fetchRestInfo(ip: ip)

// Step 3: WebSocket + KEY_HOME
step("WebSocket Connection  ws://\(ip):\(WS_PORT)")
let ws = WSTest(ip: ip, token: tvToken)
guard ws.run() else { die("Connection failed.") }
ok("Connected to \(tvName)")

step("Sending KEY_HOME")
ws.sendKey("KEY_HOME")

// Final pause for any trailing messages
info("Waiting 1s for trailing messages…")
Thread.sleep(forTimeInterval: 1)
ws.wsTask?.cancel(with: .goingAway, reason: nil)

// Step 4: Legacy TCP (port 55000) — for pre-2016 Samsung TVs
tryLegacyProtocol(tvIP: ip, key: "KEY_HOME")

step("Done")
if let token = ws.pairingToken {
    print("\n\(BOLD)Re-run with saved token:\(RESET)")
    print("  swift tv_test.swift \(ip) \(token)\n")
}

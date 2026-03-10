import Foundation
import Darwin

// MARK: - TVNetworkScanner

/// Discovers Samsung TVs on the local network using SSDP (Simple Service Discovery Protocol).
///
/// Two complementary modes run simultaneously:
///   • Active  – sends UPnP M-SEARCH multicast to 239.255.255.250:1900 and collects unicast replies.
///   • Passive – joins the SSDP multicast group and captures NOTIFY ssdp:alive broadcasts
///               that TVs send when they connect to the network.
///
/// For each discovered LOCATION URL the description XML is fetched, filtered to Samsung devices,
/// and—when available—the Samsung REST API (port 8001) is queried for the Wi-Fi MAC address.
@MainActor
final class TVNetworkScanner: ObservableObject {
    @Published var isScanning    = false
    @Published var foundDevices: [TVDevice] = []
    @Published var progress:     Double = 0   // 0.0 – 1.0
    @Published var statusMessage = ""

    private var currentTask: Task<Void, Never>?

    // Search targets sent in M-SEARCH (most specific first).
    // Samsung TVs respond to MediaRenderer and their proprietary ST.
    private static let searchTargets = [
        "urn:samsung.com:device:RemoteControlReceiver:1",
        "urn:schemas-upnp-org:device:MediaRenderer:1",
        "urn:dial-multiscreen-org:service:dial:1",
    ]

    // MARK: - Public API

    func startScan() {
        guard !isScanning else { return }
        currentTask?.cancel()
        foundDevices  = []
        progress      = 0
        statusMessage = ""
        currentTask   = Task { await runScan() }
    }

    func cancel() {
        currentTask?.cancel()
        isScanning    = false
        statusMessage = "Scan cancelled."
    }

    // MARK: - Orchestration

    private func runScan() async {
        isScanning    = true
        statusMessage = "Sending SSDP discovery…"
        defer { isScanning = false }

        // Animate progress while the blocking SSDP phase runs (~4 s).
        let progressTask = Task {
            let step: Double = 0.01
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(50))
                if progress < 0.45 { progress += step }
            }
        }

        // Run active M-SEARCH + passive NOTIFY listener concurrently.
        let locations = await withCheckedContinuation { (cont: CheckedContinuation<Set<String>, Never>) in
            Task.detached(priority: .userInitiated) {
                let listenSeconds = 4.0
                async let activeLocations  = SSDPSocket.mSearch(
                    targets: TVNetworkScanner.searchTargets, listenSeconds: listenSeconds
                )
                async let passiveLocations = SSDPSocket.listenForNotify(seconds: listenSeconds)
                let (a, b) = await (activeLocations, passiveLocations)
                cont.resume(returning: a.union(b))
            }
        }

        progressTask.cancel()
        progress = 0.5

        guard !Task.isCancelled else { return }

        if locations.isEmpty {
            progress      = 1.0
            statusMessage = "No SSDP responses received. Make sure your TV is on and connected to Wi-Fi."
            return
        }

        statusMessage = "Checking \(locations.count) device(s)…"

        // Fetch device descriptions concurrently, filter to Samsung TVs.
        var seen   = Set<String>()       // dedup by IP
        let total  = Double(locations.count)
        var done   = 0.0

        await withTaskGroup(of: TVDevice?.self) { group in
            for loc in locations {
                group.addTask { await self.fetchDevice(location: loc) }
            }
            for await result in group {
                guard !Task.isCancelled else { break }
                done += 1
                progress = 0.5 + (done / total) * 0.5
                if let device = result, !seen.contains(device.ipAddress) {
                    seen.insert(device.ipAddress)
                    foundDevices.append(device)
                    statusMessage = "Found \(foundDevices.count) TV(s)…"
                }
            }
        }

        guard !Task.isCancelled else { return }
        progress      = 1.0
        statusMessage = foundDevices.isEmpty
            ? "No Samsung TVs found. Is your TV powered on and on the same Wi-Fi?"
            : "Found \(foundDevices.count) Samsung TV(s)."
    }

    // MARK: - Device description

    /// Downloads the UPnP device description XML and returns a TVDevice if it's a Samsung TV.
    private func fetchDevice(location: String) async -> TVDevice? {
        guard let url  = URL(string: location),
              let host = url.host else { return nil }

        let req = URLRequest(url: url, timeoutInterval: 3)
        do {
            let (data, response) = try await URLSession.shared.data(for: req)
            guard (response as? HTTPURLResponse)?.statusCode == 200,
                  let xml = String(data: data, encoding: .utf8) else { return nil }

            // Must be a Samsung device
            guard xml.localizedCaseInsensitiveContains("samsung") else { return nil }

            let name = xmlValue("friendlyName", in: xml)
                    ?? xmlValue("modelName",     in: xml)
                    ?? "Samsung TV"

            // Best-effort MAC from Samsung REST API
            let mac = await samsungMAC(ip: host)

            return TVDevice(name: name, ipAddress: host, macAddress: mac)
        } catch {
            return nil
        }
    }

    /// Queries `GET http://<ip>:8001/api/v2/` for the device's Wi-Fi MAC address.
    private func samsungMAC(ip: String) async -> String {
        guard let url = URL(string: "http://\(ip):8001/api/v2/") else { return "" }
        let req = URLRequest(url: url, timeoutInterval: 2)
        guard let (data, _) = try? await URLSession.shared.data(for: req),
              let json   = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let device = json["device"] as? [String: Any],
              let mac    = device["wifiMac"] as? String else { return "" }
        return mac.replacingOccurrences(of: "-", with: ":")
    }

    // MARK: - XML helper

    private func xmlValue(_ tag: String, in xml: String) -> String? {
        let open = "<\(tag)>", close = "</\(tag)>"
        guard let s = xml.range(of: open),
              let e = xml.range(of: close, range: s.upperBound ..< xml.endIndex) else { return nil }
        let v = String(xml[s.upperBound ..< e.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
        return v.isEmpty ? nil : v
    }
}

// MARK: - SSDPSocket

/// Low-level SSDP via POSIX UDP sockets. All methods are blocking and must run off the main thread.
private enum SSDPSocket {
    static let multicastAddress = "239.255.255.250"
    static let ssdpPort: UInt16  = 1900

    // MARK: Active — M-SEARCH

    /// Sends an M-SEARCH for each search target on a single socket and collects LOCATION URLs
    /// from all unicast replies received within `listenSeconds`.
    static func mSearch(targets: [String], listenSeconds: Double) async -> Set<String> {
        await withCheckedContinuation { continuation in
            let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
            guard sock >= 0 else { continuation.resume(returning: []); return }
            defer { close(sock) }

            configureSocket(sock)
            bindAny(sock)
            setReceiveTimeout(sock, seconds: listenSeconds)

            // Send one M-SEARCH per search target
            for target in targets {
                let msg = mSearchMessage(st: target)
                sendToSSDPGroup(sock, message: msg)
            }

            continuation.resume(returning: collectLocations(sock))
        }
    }

    // MARK: Passive — NOTIFY listener

    /// Joins the SSDP multicast group on port 1900 and collects LOCATION URLs from
    /// NOTIFY ssdp:alive messages for `seconds`.
    static func listenForNotify(seconds: Double) async -> Set<String> {
        await withCheckedContinuation { continuation in
            let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
            guard sock >= 0 else { continuation.resume(returning: []); return }
            defer { close(sock) }

            configureSocket(sock)
            bindPort(sock, port: ssdpPort)         // must bind to 1900 to receive multicast
            joinMulticastGroup(sock)
            setReceiveTimeout(sock, seconds: seconds)

            continuation.resume(returning: collectLocations(sock))
        }
    }

    // MARK: Receive loop

    /// Reads packets until the receive timeout expires, returning all LOCATION values found.
    private static func collectLocations(_ sock: Int32) -> Set<String> {
        var result = Set<String>()
        var buf    = [CChar](repeating: 0, count: 8192)
        while true {
            let n = recv(sock, &buf, buf.count - 1, 0)
            guard n > 0 else { break }
            buf[Int(n)] = 0
            let response = String(cString: buf)
            // Accept responses (200 OK from M-SEARCH) and NOTIFY ssdp:alive broadcasts
            if response.hasPrefix("HTTP/1.1 200") || response.hasPrefix("NOTIFY") {
                if let loc = headerValue("location", in: response) {
                    result.insert(loc)
                }
            }
        }
        return result
    }

    // MARK: Socket helpers

    private static func configureSocket(_ sock: Int32) {
        var yes: Int32 = 1
        setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
        setsockopt(sock, SOL_SOCKET, SO_REUSEPORT, &yes, socklen_t(MemoryLayout<Int32>.size))
    }

    /// Binds to an OS-assigned ephemeral port (for M-SEARCH unicast replies).
    private static func bindAny(_ sock: Int32) {
        var addr = sockaddr_in()
        addr.sin_family      = sa_family_t(AF_INET)
        addr.sin_addr.s_addr = INADDR_ANY
        addr.sin_port        = 0
        _ = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
    }

    /// Binds to a specific port (for multicast NOTIFY reception).
    private static func bindPort(_ sock: Int32, port: UInt16) {
        var addr = sockaddr_in()
        addr.sin_family      = sa_family_t(AF_INET)
        addr.sin_addr.s_addr = INADDR_ANY
        addr.sin_port        = port.bigEndian
        _ = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(sock, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
    }

    /// Joins the SSDP multicast group so the socket receives NOTIFY packets.
    private static func joinMulticastGroup(_ sock: Int32) {
        var mreq        = ip_mreq()
        mreq.imr_multiaddr.s_addr = inet_addr(multicastAddress)
        mreq.imr_interface.s_addr = INADDR_ANY
        setsockopt(sock, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, socklen_t(MemoryLayout<ip_mreq>.size))
    }

    private static func setReceiveTimeout(_ sock: Int32, seconds: Double) {
        var tv    = timeval()
        tv.tv_sec = Int(seconds)
        tv.tv_usec = 0
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))
    }

    private static func sendToSSDPGroup(_ sock: Int32, message: String) {
        var dest = sockaddr_in()
        dest.sin_family      = sa_family_t(AF_INET)
        dest.sin_addr.s_addr = inet_addr(multicastAddress)
        dest.sin_port        = ssdpPort.bigEndian
        _ = message.withCString { ptr in
            withUnsafePointer(to: &dest) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    sendto(sock, ptr, strlen(ptr), 0, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
                }
            }
        }
    }

    // MARK: Message builder

    private static func mSearchMessage(st: String) -> String {
        [
            "M-SEARCH * HTTP/1.1",
            "HOST: \(multicastAddress):\(ssdpPort)",
            "MAN: \"ssdp:discover\"",
            "MX: 3",
            "ST: \(st)",
            "", "",
        ].joined(separator: "\r\n")
    }

    // MARK: Header parsing

    /// Case-insensitive HTTP header extraction from a raw SSDP message.
    private static func headerValue(_ name: String, in message: String) -> String? {
        let prefix = name.lowercased() + ":"
        for line in message.components(separatedBy: "\r\n") {
            if line.lowercased().hasPrefix(prefix) {
                return String(line.dropFirst(prefix.count)).trimmingCharacters(in: .whitespaces)
            }
        }
        return nil
    }
}

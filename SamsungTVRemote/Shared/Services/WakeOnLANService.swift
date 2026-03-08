import Foundation

enum WoLError: LocalizedError {
    case invalidMAC
    case socketFailed
    var errorDescription: String? {
        switch self {
        case .invalidMAC:    return "Invalid MAC address format"
        case .socketFailed:  return "Failed to create UDP socket"
        }
    }
}

final class WakeOnLANService {
    func send(macAddress: String) throws {
        let macBytes = macAddress
            .split(separator: ":")
            .compactMap { UInt8($0, radix: 16) }
        guard macBytes.count == 6 else { throw WoLError.invalidMAC }

        // Build 102-byte magic packet
        var packet = [UInt8](repeating: 0xFF, count: 6)
        for _ in 0..<16 { packet.append(contentsOf: macBytes) }

        // UDP broadcast to 255.255.255.255:9
        let sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        guard sock >= 0 else { throw WoLError.socketFailed }
        defer { close(sock) }

        var broadcast: Int32 = 1
        setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = UInt16(9).bigEndian
        addr.sin_addr.s_addr = UInt32.max // 255.255.255.255

        withUnsafeBytes(of: &addr) { addrPtr in
            packet.withUnsafeBytes { pktPtr in
                let _ = sendto(
                    sock,
                    pktPtr.baseAddress,
                    packet.count,
                    0,
                    addrPtr.bindMemory(to: sockaddr.self).baseAddress,
                    socklen_t(MemoryLayout<sockaddr_in>.size)
                )
            }
        }
    }
}

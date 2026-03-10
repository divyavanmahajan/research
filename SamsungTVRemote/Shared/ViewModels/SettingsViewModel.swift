import Foundation
import SwiftUI

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var tvDevices: [TVDevice] = []
    @Published var smartThingsToken: String = ""
    @Published var preferLocal: Bool = true
    @Published var localTimeout: Double = 2.0

    private let devicesKey = "tvDevices"
    private let tokenKey   = "smartthings_token"

    init() {
        load()
    }

    func save() {
        if let data = try? JSONEncoder().encode(tvDevices) {
            UserDefaults.standard.set(data, forKey: devicesKey)
        }
        // Store token in Keychain
        KeychainHelper.save(key: tokenKey, value: smartThingsToken)
    }

    func addDevice(_ device: TVDevice) {
        tvDevices.append(device)
        save()
    }

    func removeDevice(at offsets: IndexSet) {
        tvDevices.remove(atOffsets: offsets)
        save()
    }

    private func load() {
        if let data = UserDefaults.standard.data(forKey: devicesKey),
           let devices = try? JSONDecoder().decode([TVDevice].self, from: data) {
            tvDevices = devices
        }
        smartThingsToken = KeychainHelper.read(key: tokenKey) ?? ""
    }
}

// MARK: - Keychain helper

enum KeychainHelper {
    static func save(key: String, value: String) {
        let data = value.data(using: .utf8)!
        let query: [CFString: Any] = [
            kSecClass:       kSecClassGenericPassword,
            kSecAttrAccount: key,
            kSecValueData:   data
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    static func read(key: String) -> String? {
        let query: [CFString: Any] = [
            kSecClass:            kSecClassGenericPassword,
            kSecAttrAccount:      key,
            kSecReturnData:       true,
            kSecMatchLimit:       kSecMatchLimitOne
        ]
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        guard let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}

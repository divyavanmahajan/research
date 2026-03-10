import SwiftUI

package struct SettingsView: View {
    @EnvironmentObject var settings: SettingsViewModel
    @EnvironmentObject var manager: TVConnectionManager
    @Environment(\.dismiss) private var dismiss

    @State private var showAddTV = false
    @State private var newName = ""
    @State private var newIP = ""
    @State private var newMAC = ""

    package init() {}

    package var body: some View {
        #if os(macOS)
        macosSettings
        #else
        iosSettings
        #endif
    }

    // MARK: - iOS Settings (sheet Form)
    private var iosSettings: some View {
        NavigationStack {
            Form {
                Section("My TVs") {
                    ForEach(settings.tvDevices) { tv in
                        TVRowView(tv: tv, manager: manager, onUpdate: { settings.updateDevice($0) }) {
                            if let idx = settings.tvDevices.firstIndex(where: { $0.id == tv.id }) {
                                settings.removeDevice(at: IndexSet([idx]))
                                if manager.currentTV?.id == tv.id { manager.disconnect() }
                            }
                        }
                    }
                    .onDelete(perform: settings.removeDevice)

                    Button("Add TV") { showAddTV = true }
                }

                Section("SmartThings (Optional)") {
                    SecureField("Personal Access Token", text: $settings.smartThingsToken)
                        .onChange(of: settings.smartThingsToken) { _ in settings.save() }

                    Button("Discover My TVs") {
                        Task {
                            manager.cloudService.token = settings.smartThingsToken
                            if let tvs = try? await manager.cloudService.discoverTVDevices() {
                                for tv in tvs where !settings.tvDevices.contains(where: { $0.smartThingsDeviceId == tv.smartThingsDeviceId }) {
                                    settings.addDevice(tv)
                                }
                            }
                        }
                    }
                    .disabled(settings.smartThingsToken.isEmpty)
                }

                Section("Connection") {
                    Toggle("Prefer Local Network", isOn: $settings.preferLocal)
                    LabeledContent("Local Timeout") {
                        Stepper("\(Int(settings.localTimeout))s",
                                value: $settings.localTimeout,
                                in: 1...10, step: 1)
                    }
                }

                Section("Troubleshooting") {
                    NavigationLink("Connection Help") {
                        TroubleshootingView()
                            .navigationTitle("Troubleshooting")
                    }
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .sheet(isPresented: $showAddTV) {
                AddTVSheet(settings: settings, isPresented: $showAddTV)
            }
        }
    }

    // MARK: - macOS Settings (TabView)
    private var macosSettings: some View {
        TabView {
            tvListTab.tabItem { Label("TVs", systemImage: "tv") }
            smTabView.tabItem { Label("SmartThings", systemImage: "cloud") }
            connectionTab.tabItem { Label("Connection", systemImage: "wifi") }
            TroubleshootingView().tabItem { Label("Help", systemImage: "questionmark.circle") }
        }
        .frame(width: 480, height: 360)
        .padding()
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Close") { dismiss() }
            }
        }
    }

    private var tvListTab: some View {
        VStack(alignment: .leading, spacing: 0) {
            List {
                ForEach(settings.tvDevices) { tv in
                    TVRowView(tv: tv, manager: manager, onUpdate: { settings.updateDevice($0) }) {
                        if let idx = settings.tvDevices.firstIndex(where: { $0.id == tv.id }) {
                            settings.removeDevice(at: IndexSet([idx]))
                            if manager.currentTV?.id == tv.id { manager.disconnect() }
                        }
                    }
                }
            }
            Divider()
            HStack {
                Button("+ Add TV") { showAddTV = true }
                Spacer()
            }
            .padding(8)
        }
        .sheet(isPresented: $showAddTV) {
            AddTVSheet(settings: settings, isPresented: $showAddTV)
        }
    }

    private var smTabView: some View {
        Form {
            SecureField("Personal Access Token", text: $settings.smartThingsToken)
                .onChange(of: settings.smartThingsToken) { _ in settings.save() }
            Button("Discover TVs") {
                Task {
                    manager.cloudService.token = settings.smartThingsToken
                    if let tvs = try? await manager.cloudService.discoverTVDevices() {
                        for tv in tvs { settings.addDevice(tv) }
                    }
                }
            }
            .disabled(settings.smartThingsToken.isEmpty)
        }
    }

    private var connectionTab: some View {
        Form {
            Toggle("Prefer Local Network", isOn: $settings.preferLocal)
            Stepper("Local Timeout: \(Int(settings.localTimeout))s",
                    value: $settings.localTimeout, in: 1...10, step: 1)
        }
    }
}

// MARK: - Add TV Sheet

struct AddTVSheet: View {
    @ObservedObject var settings: SettingsViewModel
    @Binding var isPresented: Bool

    @StateObject private var scanner = TVNetworkScanner()
    @State private var newName = ""
    @State private var newIP = ""
    @State private var newMAC = ""
    @State private var newToken = ""

    var body: some View {
        NavigationStack {
            Form {
                scanSection
                manualSection
            }
            .navigationTitle("Add TV")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        scanner.cancel()
                        isPresented = false
                    }
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.large])
        #endif
    }

    // MARK: - Scan section

    private var scanSection: some View {
        Section {
            // Scan button / cancel
            if scanner.isScanning {
                HStack {
                    ProgressView()
                        .controlSize(.small)
                    Text(scanner.statusMessage)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button("Stop") { scanner.cancel() }
                        .buttonStyle(.borderless)
                        .foregroundStyle(.red)
                }

                ProgressView(value: scanner.progress)
                    .progressViewStyle(.linear)
                    .animation(.linear(duration: 0.2), value: scanner.progress)
            } else {
                Button {
                    scanner.startScan()
                } label: {
                    Label("Scan Local Network", systemImage: "network")
                }

                if !scanner.statusMessage.isEmpty {
                    Text(scanner.statusMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            // Found TVs
            if !scanner.foundDevices.isEmpty {
                ForEach(scanner.foundDevices) { tv in
                    FoundTVRow(tv: tv, alreadyAdded: settings.tvDevices.contains(where: { $0.ipAddress == tv.ipAddress })) {
                        settings.addDevice(tv)
                    }
                }
            }
        } header: {
            Text("Network Scan")
        } footer: {
            Text("Scans your local Wi-Fi for Samsung TVs on port 8001.")
                .font(.caption)
        }
    }

    // MARK: - Manual entry section

    private var manualSection: some View {
        Section("Manual Entry") {
            TextField("Name (e.g. Living Room)", text: $newName)
            TextField("IP Address (e.g. 192.168.1.100)", text: $newIP)
                #if os(iOS)
                .keyboardType(.numbersAndPunctuation)
                #endif
            TextField("MAC Address (AA:BB:CC:DD:EE:FF)", text: $newMAC)
            TextField("Pairing Token (optional)", text: $newToken)

            Button("Add") {
                var tv = TVDevice(name: newName, ipAddress: newIP, macAddress: newMAC)
                tv.pairingToken = newToken.isEmpty ? nil : newToken
                settings.addDevice(tv)
                newName = ""; newIP = ""; newMAC = ""; newToken = ""
            }
            .disabled(newName.isEmpty || newIP.isEmpty)
        }
    }
}

// MARK: - TV Row (settings list)

/// A row in the saved-TV list showing connect/disconnect/delete actions.
private struct TVRowView: View {
    let tv: TVDevice
    @ObservedObject var manager: TVConnectionManager
    let onUpdate: (TVDevice) -> Void
    let onDelete: () -> Void

    @State private var showEdit = false

    private var isCurrent: Bool { manager.currentTV?.id == tv.id }
    private var isConnected: Bool {
        isCurrent && (manager.connectionState == .connectedLocal || manager.connectionState == .connectedCloud)
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(tv.name).font(.headline)
                Text(tv.ipAddress).font(.caption).foregroundStyle(.secondary)
                if let token = tv.pairingToken, !token.isEmpty {
                    Text("Token: \(token)")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            Spacer()
            if isConnected {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                Button("Disconnect") { manager.disconnect() }
                    .buttonStyle(.borderless)
                    .foregroundStyle(.red)
            } else {
                Button(isCurrent ? "Reconnect" : "Connect") {
                    Task { await manager.selectAndConnect(tv) }
                }
                .buttonStyle(.borderless)
                .foregroundStyle(Color.accentColor)
            }
            Button { showEdit = true } label: {
                Image(systemName: "pencil")
            }
            .buttonStyle(.borderless)
            .foregroundStyle(.secondary)
            Button(role: .destructive, action: onDelete) {
                Image(systemName: "trash")
            }
            .buttonStyle(.borderless)
            .foregroundStyle(.red)
        }
        .padding(.vertical, 2)
        .sheet(isPresented: $showEdit) {
            EditTVSheet(tv: tv, onSave: { updated in
                onUpdate(updated)
                showEdit = false
            }, onCancel: { showEdit = false })
        }
    }
}

// MARK: - Edit TV Sheet

private struct EditTVSheet: View {
    let tv: TVDevice
    let onSave: (TVDevice) -> Void
    let onCancel: () -> Void

    @State private var name: String
    @State private var token: String

    init(tv: TVDevice, onSave: @escaping (TVDevice) -> Void, onCancel: @escaping () -> Void) {
        self.tv = tv
        self.onSave = onSave
        self.onCancel = onCancel
        _name  = State(initialValue: tv.name)
        _token = State(initialValue: tv.pairingToken ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("TV Details") {
                    LabeledContent("IP Address", value: tv.ipAddress)
                    TextField("Name", text: $name)
                }
                Section {
                    TextField("Pairing Token", text: $token)
                        .font(.system(.body, design: .monospaced))
                } header: {
                    Text("Pairing Token")
                } footer: {
                    Text("Obtain the token by running: swift samsung-tv.swift status\nOr let the app pair automatically when you connect.")
                        .font(.caption)
                }
            }
            .navigationTitle("Edit TV")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel", action: onCancel) }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        var updated = tv
                        updated.name = name
                        updated.pairingToken = token.isEmpty ? nil : token
                        onSave(updated)
                    }
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.medium])
        #endif
    }
}

// MARK: - Troubleshooting

struct TroubleshootingView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                tipSection(
                    icon: "tv.slash",
                    title: "No popup appeared when connecting",
                    steps: [
                        "On the TV remote press Menu (or the Settings gear icon).",
                        "Go to General → External Device Manager → Device Connect Manager.",
                        "Set Access Notification to \"First Time Only\" or \"Always\".",
                        "On newer firmware the path may be General & Privacy → External Device Manager.",
                        "Try connecting again — a popup should now appear on the TV screen."
                    ]
                )

                tipSection(
                    icon: "wifi.slash",
                    title: "TV shows as disconnected after adding",
                    steps: [
                        "Make sure your iPhone/Mac and the TV are on the same Wi-Fi network.",
                        "Check that port 8001 is not blocked by a router or firewall.",
                        "Go to Settings → TVs and tap Connect next to the TV.",
                        "If the TV is off, use the Power button — it sends a Wake-on-LAN packet first."
                    ]
                )

                tipSection(
                    icon: "exclamationmark.triangle",
                    title: "Buttons do nothing after connecting",
                    steps: [
                        "The TV may have closed the session. Tap Reconnect in Settings.",
                        "Accept the pairing popup on the TV screen if one appears.",
                        "If you previously denied the pairing request, go to TV Settings → General → External Device Manager → Device Connection Manager and remove the entry for this device, then reconnect."
                    ]
                )

                tipSection(
                    icon: "tv",
                    title: "2014–2015 Samsung TVs (H-series)",
                    steps: [
                        "These models use an older protocol (MSF 2.x) that may not support remote control from third-party apps.",
                        "Try enabling \"IP Control\" under TV Settings → General → Network → Expert Settings if available.",
                        "SmartThings cloud control (via a Personal Access Token in Settings) may work as an alternative."
                    ]
                )
            }
            .padding()
        }
        #if os(macOS)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        #endif
    }

    @ViewBuilder
    private func tipSection(icon: String, title: String, steps: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: icon)
                .font(.headline)
            ForEach(Array(steps.enumerated()), id: \.offset) { index, step in
                HStack(alignment: .top, spacing: 8) {
                    Text("\(index + 1).")
                        .foregroundStyle(.secondary)
                        .frame(width: 20, alignment: .trailing)
                    Text(step)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .font(.subheadline)
            }
        }
        .padding()
        .background(Color.gray.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - Found TV Row

private struct FoundTVRow: View {
    let tv: TVDevice
    let alreadyAdded: Bool
    let onAdd: () -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(tv.name).font(.headline)
                Text(tv.ipAddress)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if !tv.macAddress.isEmpty {
                    Text(tv.macAddress)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            Spacer()
            if alreadyAdded {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            } else {
                Button("Add") { onAdd() }
                    .buttonStyle(.borderless)
                    .foregroundStyle(Color.accentColor)
                    .controlSize(.small)
            }
        }
        .padding(.vertical, 2)
    }
}

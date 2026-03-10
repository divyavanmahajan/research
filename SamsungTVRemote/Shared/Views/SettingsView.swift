import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var settings: SettingsViewModel
    @EnvironmentObject var manager: TVConnectionManager
    @Environment(\.dismiss) private var dismiss

    @State private var showAddTV = false
    @State private var newName = ""
    @State private var newIP = ""
    @State private var newMAC = ""

    var body: some View {
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
                        VStack(alignment: .leading, spacing: 2) {
                            Text(tv.name).font(.headline)
                            Text(tv.ipAddress).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .onDelete(perform: settings.removeDevice)

                    Button("Add TV") { showAddTV = true }
                }

                Section("SmartThings (Optional)") {
                    SecureField("Personal Access Token", text: $settings.smartThingsToken)
                        .onChange(of: settings.smartThingsToken) { _, _ in settings.save() }

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
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .sheet(isPresented: $showAddTV) { addTVSheet }
        }
    }

    // MARK: - macOS Settings (TabView)
    private var macosSettings: some View {
        TabView {
            tvListTab.tabItem { Label("TVs", systemImage: "tv") }
            smTabView.tabItem { Label("SmartThings", systemImage: "cloud") }
            connectionTab.tabItem { Label("Connection", systemImage: "wifi") }
        }
        .frame(width: 480, height: 320)
        .padding()
    }

    private var tvListTab: some View {
        VStack(alignment: .leading) {
            List(settings.tvDevices) { tv in
                VStack(alignment: .leading) {
                    Text(tv.name).font(.headline)
                    Text(tv.ipAddress).font(.caption).foregroundStyle(.secondary)
                }
            }
            HStack {
                Button("+ Add TV") { showAddTV = true }
                Spacer()
            }
        }
        .sheet(isPresented: $showAddTV) { addTVSheet }
    }

    private var smTabView: some View {
        Form {
            SecureField("Personal Access Token", text: $settings.smartThingsToken)
                .onChange(of: settings.smartThingsToken) { _, _ in settings.save() }
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

    // MARK: - Add TV Sheet

    private var addTVSheet: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Name (e.g. Living Room)", text: $newName)
                    TextField("IP Address (e.g. 192.168.1.100)", text: $newIP)
                        .keyboardType(.numbersAndPunctuation)
                    TextField("MAC Address (AA:BB:CC:DD:EE:FF)", text: $newMAC)
                }
            }
            .navigationTitle("Add TV")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        showAddTV = false
                        clearForm()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        let tv = TVDevice(name: newName, ipAddress: newIP, macAddress: newMAC)
                        settings.addDevice(tv)
                        showAddTV = false
                        clearForm()
                    }
                    .disabled(newName.isEmpty || newIP.isEmpty)
                }
            }
        }
        #if os(iOS)
        .presentationDetents([.medium])
        #endif
    }

    private func clearForm() {
        newName = ""; newIP = ""; newMAC = ""
    }
}

import SwiftUI

struct RemoteControlView: View {
    @EnvironmentObject var manager: TVConnectionManager
    @EnvironmentObject var settings: SettingsViewModel
    @StateObject private var vm = RemoteViewModel()
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    ConnectionStatusBanner()
                    PowerButtonView()
                    DPadView()
                    QuickNavRow()
                    Divider()
                    MediaControlsView()
                    Divider()
                    AppLauncherView()
                }
                .padding()
            }
            .navigationTitle(manager.currentTV?.name ?? "Samsung TV Remote")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape")
                    }
                }
            }
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
                .environmentObject(settings)
                .environmentObject(manager)
        }
        .onAppear {
            if let first = settings.tvDevices.first {
                manager.setTV(first)
                Task { await manager.connect() }
            }
        }
        #if os(macOS)
        .frame(width: 380, height: 680)
        .keyboardShortcuts(manager: manager)
        #endif
    }
}

// MARK: - Connection Banner

struct ConnectionStatusBanner: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(manager.connectionState.color)
                .frame(width: 8, height: 8)
            Text(manager.connectionState.label)
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
        }
    }
}

// MARK: - Power Button

struct PowerButtonView: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        Button {
            Task { await manager.togglePower() }
        } label: {
            Image(systemName: "power")
                .font(.title)
                .foregroundStyle(.red)
                .frame(width: 56, height: 56)
        }
        .buttonStyle(.bordered)
        .tint(.red)
    }
}

// MARK: - D-Pad

struct DPadView: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        ZStack {
            Circle()
                .fill(Color(.systemGray5))
                .frame(width: 200, height: 200)

            VStack(spacing: 0) {
                dpadBtn(.up, "chevron.up")
                HStack(spacing: 0) {
                    dpadBtn(.left, "chevron.left")
                    Button {
                        Task { await manager.send(key: .ok) }
                    } label: {
                        Text("OK")
                            .font(.headline)
                            .frame(width: 60, height: 60)
                    }
                    .buttonStyle(.plain)
                    dpadBtn(.right, "chevron.right")
                }
                dpadBtn(.down, "chevron.down")
            }
        }
    }

    @ViewBuilder
    private func dpadBtn(_ key: RemoteKey, _ icon: String) -> some View {
        Button {
            Task { await manager.send(key: key) }
        } label: {
            Image(systemName: icon)
                .font(.title3)
                .frame(width: 60, height: 60)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Quick Nav

struct QuickNavRow: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        HStack(spacing: 32) {
            navBtn(.home, "house",              "Home")
            navBtn(.back, "arrow.uturn.left",   "Back")
            navBtn(.menu, "line.3.horizontal",  "Menu")
        }
    }

    @ViewBuilder
    private func navBtn(_ key: RemoteKey, _ icon: String, _ label: String) -> some View {
        Button {
            Task { await manager.send(key: key) }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon)
                Text(label).font(.caption2)
            }
            .frame(width: 60, height: 44)
        }
        .buttonStyle(.bordered)
    }
}

// MARK: - Media Controls

struct MediaControlsView: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 16) {
                mediaBtn(.volumeDown, "speaker.minus.fill", "Vol–")
                mediaBtn(.mute,       "speaker.slash.fill", "Mute")
                mediaBtn(.volumeUp,   "speaker.plus.fill",  "Vol+")
            }
            HStack(spacing: 48) {
                mediaBtn(.channelDown, "chevron.down.circle", "CH–")
                mediaBtn(.channelUp,   "chevron.up.circle",   "CH+")
            }
        }
    }

    @ViewBuilder
    private func mediaBtn(_ key: RemoteKey, _ icon: String, _ label: String) -> some View {
        Button {
            Task { await manager.send(key: key) }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon).font(.title3)
                Text(label).font(.caption2)
            }
            .frame(width: 72, height: 52)
        }
        .buttonStyle(.bordered)
    }
}

// MARK: - App Launcher

struct AppLauncherView: View {
    @EnvironmentObject var manager: TVConnectionManager
    let columns = [GridItem(.adaptive(minimum: 80))]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Apps")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(TVApp.knownApps) { app in
                    Button {
                        Task { await manager.launch(app: app) }
                    } label: {
                        VStack(spacing: 4) {
                            Image(systemName: app.icon)
                                .font(.largeTitle)
                                .foregroundStyle(.primary)
                                .frame(height: 40)
                            Text(app.name)
                                .font(.caption2)
                                .lineLimit(1)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

// MARK: - macOS Keyboard Shortcuts

#if os(macOS)
extension View {
    func keyboardShortcuts(manager: TVConnectionManager) -> some View {
        self.onKeyPress(.upArrow)    { Task { await manager.send(key: .up) };         return .handled }
            .onKeyPress(.downArrow)  { Task { await manager.send(key: .down) };       return .handled }
            .onKeyPress(.leftArrow)  { Task { await manager.send(key: .left) };       return .handled }
            .onKeyPress(.rightArrow) { Task { await manager.send(key: .right) };      return .handled }
            .onKeyPress(.return)     { Task { await manager.send(key: .ok) };         return .handled }
            .onKeyPress(.escape)     { Task { await manager.send(key: .back) };       return .handled }
            .onKeyPress(characters: CharacterSet(charactersIn: "+")) { _ in
                Task { await manager.send(key: .volumeUp) }; return .handled
            }
            .onKeyPress(characters: CharacterSet(charactersIn: "-")) { _ in
                Task { await manager.send(key: .volumeDown) }; return .handled
            }
            .onKeyPress(characters: CharacterSet(charactersIn: "mM")) { _ in
                Task { await manager.send(key: .mute) }; return .handled
            }
    }
}
#endif

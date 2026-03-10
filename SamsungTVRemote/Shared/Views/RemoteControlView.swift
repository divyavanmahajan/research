import SwiftUI

package struct RemoteControlView: View {
    @EnvironmentObject var manager: TVConnectionManager
    @EnvironmentObject var settings: SettingsViewModel
    @StateObject private var vm = RemoteViewModel()
    @State private var showSettings = false

    package init() {}

    package var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Sticky connection banner — pinned above ScrollView, never scrolls away
                ConnectionStatusBanner()
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(.bar)

                Divider()

                ScrollView {
                    VStack(spacing: 20) {
                        // D-Pad (left) + Power button (right)
                        HStack(alignment: .center, spacing: 12) {
                            DPadView()
                            Spacer()
                            PowerButtonView()
                                .frame(width: 72)
                        }
                        .padding(.horizontal, 16)

                        QuickNavRow()

                        Divider().padding(.horizontal)

                        MediaControlsView()

                        Divider().padding(.horizontal)

                        AppLauncherView()
                    }
                    .padding(.vertical, 16)
                }
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
            manager.onDeviceUpdated = { settings.updateDevice($0) }
            if let first = settings.tvDevices.first {
                manager.setTV(first)
                Task { await manager.connect() }
            }
        }
        .onChange(of: settings.tvDevices) { devices in
            guard manager.currentTV == nil, let first = devices.first else { return }
            Task { await manager.selectAndConnect(first) }
        }
        #if os(macOS)
        .frame(width: 380, height: 660)
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
            if manager.connectionState == .disconnected && manager.currentTV != nil {
                Button("Reconnect") {
                    Task { await manager.connect() }
                }
                .font(.caption)
                .buttonStyle(.borderless)
                .foregroundStyle(Color.accentColor)
            }
        }
    }
}

// MARK: - Power Button (compact, for side-by-side layout)

struct PowerButtonView: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        Button {
            Task { await manager.togglePower() }
        } label: {
            Image(systemName: "power")
                .font(.title2)
                .foregroundStyle(.red)
                .frame(width: 48, height: 48)
        }
        .buttonStyle(.bordered)
        .tint(.red)
    }
}

// MARK: - D-Pad (smaller)

struct DPadView: View {
    @EnvironmentObject var manager: TVConnectionManager

    private let outerSize: CGFloat = 160
    private let btnSize: CGFloat   = 42
    private let okSize: CGFloat    = 50

    var body: some View {
        ZStack {
            Circle()
                .fill(Color.gray.opacity(0.15))
                .frame(width: outerSize, height: outerSize)

            VStack(spacing: 0) {
                dpadBtn(.up, "chevron.up")
                HStack(spacing: 0) {
                    dpadBtn(.left, "chevron.left")
                    Button {
                        Task { await manager.send(key: .ok) }
                    } label: {
                        Text("OK")
                            .font(.headline)
                            .frame(width: okSize, height: okSize)
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
                .font(.system(size: 14, weight: .medium))
                .frame(width: btnSize, height: btnSize)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Quick Nav

struct QuickNavRow: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        HStack(spacing: 0) {
            navBtn(.home, "house",             "Home")
            Spacer()
            navBtn(.back, "arrow.uturn.left",  "Back")
            Spacer()
            navBtn(.menu, "line.3.horizontal", "Menu")
        }
        .padding(.horizontal, 24)
    }

    @ViewBuilder
    private func navBtn(_ key: RemoteKey, _ icon: String, _ label: String) -> some View {
        Button {
            Task { await manager.send(key: key) }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .regular))
                    .frame(width: 22, height: 22)
                Text(label)
                    .font(.caption2)
            }
            .frame(width: 72, height: 50)
        }
        .buttonStyle(.bordered)
    }
}

// MARK: - Media Controls

struct MediaControlsView: View {
    @EnvironmentObject var manager: TVConnectionManager

    var body: some View {
        VStack(spacing: 12) {
            // Volume row
            HStack(spacing: 0) {
                mediaBtn(.volumeDown, "speaker.minus.fill", "Vol–")
                Spacer()
                mediaBtn(.mute,       "speaker.slash.fill", "Mute")
                Spacer()
                mediaBtn(.volumeUp,   "speaker.plus.fill",  "Vol+")
            }
            .padding(.horizontal, 24)

            // Channel / Playback row
            HStack(spacing: 0) {
                mediaBtn(.channelDown, "chevron.down.circle", "CH–")
                Spacer()
                mediaBtn(.playPause,   "playpause.fill",      "Play/Pause")
                Spacer()
                mediaBtn(.channelUp,   "chevron.up.circle",   "CH+")
            }
            .padding(.horizontal, 24)
        }
    }

    @ViewBuilder
    private func mediaBtn(_ key: RemoteKey, _ icon: String, _ label: String) -> some View {
        Button {
            Task { await manager.send(key: key) }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .regular))
                    .frame(width: 24, height: 24)
                Text(label)
                    .font(.caption2)
            }
            .frame(width: 72, height: 52)
        }
        .buttonStyle(.bordered)
    }
}

// MARK: - App Launcher

struct AppLauncherView: View {
    @EnvironmentObject var manager: TVConnectionManager

    private let columns = [
        GridItem(.flexible()),
        GridItem(.flexible()),
        GridItem(.flexible()),
        GridItem(.flexible()),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Apps")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 16)

            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(TVApp.knownApps) { app in
                    Button {
                        Task { await manager.launch(app: app) }
                    } label: {
                        VStack(spacing: 6) {
                            Image(systemName: app.icon)
                                .font(.system(size: 24))
                                .foregroundStyle(.primary)
                                .frame(width: 28, height: 28)
                            Text(app.name)
                                .font(.caption2)
                                .lineLimit(1)
                                .minimumScaleFactor(0.8)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(Color.gray.opacity(0.15))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
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

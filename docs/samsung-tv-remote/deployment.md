# Samsung TV Remote — Deployment Guide

**Version:** 1.0
**Date:** 2026-03-08

---

## Part 1 — Deploy to a Physical iPhone

### Prerequisites

| Requirement | Details |
|---|---|
| Apple Developer account | Free (sideloading) or Paid ($99/yr, App Store + all devices) |
| iPhone running iOS 16+ | Connected via USB or on same network (wireless) |
| Xcode 15+ installed | On the Mac doing the build |
| iPhone trusted on Mac | "Trust This Computer" shown once on iPhone |

---

### Step 1 — Register Your Device

**Option A — Xcode auto-registration (easiest)**
1. Plug iPhone into Mac via USB
2. Open Xcode → **Window → Devices and Simulators**
3. Your iPhone appears; click **Add** if prompted to add it to your team's device list
4. Xcode registers the UDID with Apple Developer portal automatically

**Option B — Manual via Developer Portal**
1. On iPhone: **Settings → General → About → scroll to UDID** (tap to copy)
2. Go to `https://developer.apple.com/account/resources/devices/list`
3. Click **+**, paste UDID, name the device (e.g. "My iPhone 15"), click **Continue**

---

### Step 2 — Configure Signing in Xcode

1. Open `SamsungTVRemote.xcodeproj`
2. Click the project root → select `SamsungRemote-iOS` target
3. **Signing & Capabilities** tab:
   - Team: select your Apple ID / developer account
   - Bundle Identifier: `com.yourcompany.samsungremote.ios` (must be unique)
   - Check **Automatically manage signing**
4. Xcode creates a provisioning profile automatically

---

### Step 3 — Select Device and Build

1. In the Xcode toolbar (top-left), click the destination dropdown
2. Select your physical iPhone (it appears under "iOS Device" when plugged in)
3. Press **⌘R** (or **Product → Run**)
4. Xcode builds, signs, and installs the app on your iPhone

> **Wireless deployment:** After the first USB connection, enable **Window → Devices → Connect via Network** checkbox. Future deploys work over Wi-Fi (both Mac and iPhone on same network).

---

### Step 4 — Trust Developer on iPhone (first time only)

If you see "Untrusted Developer" on iPhone:
1. iPhone → **Settings → General → VPN & Device Management**
2. Under "Developer App", tap your Apple ID
3. Tap **Trust "Your Apple ID"** → confirm

---

### Step 5 — Verify the App

```bash
# Confirm build succeeded and app is installed
xcrun devicectl device info processes --device <UDID> | grep Samsung
```

Or check manually on iPhone: the app icon appears on the home screen.

---

### Troubleshooting (iPhone)

| Error | Fix |
|---|---|
| "Provisioning profile doesn't include device" | Add device UDID in Developer Portal, refresh profile in Xcode |
| "No signing certificate found" | Xcode → Preferences → Accounts → Add Apple ID → Download Certificates |
| App crashes on launch | Check **Xcode → Window → Devices → View Device Logs** |
| "Could not connect to iPhone" | Toggle Airplane mode on/off on iPhone; replug USB |
| Build fails with `ITMS-90xxx` code | Update build settings: set correct deployment target, remove unsupported frameworks |

---

## Part 2 — Deploy to a Mac (for development / testing)

### Step 1 — Select Destination

1. In Xcode toolbar, set destination to **"My Mac"**
2. Select `SamsungRemote-macOS` scheme

### Step 2 — Build and Run

```bash
xcodebuild \
  -scheme SamsungRemote-macOS \
  -destination 'platform=macOS,arch=arm64' \
  -configuration Debug \
  clean build

# Or just press ⌘R in Xcode
```

### Step 3 — App Bundle Location

After a successful build:
```bash
# Default DerivedData path
open ~/Library/Developer/Xcode/DerivedData/SamsungTVRemote-*/Build/Products/Debug/SamsungTVRemote.app
```

To distribute the `.app` to other Macs without the App Store, see §4 below.

---

## Part 3 — Ad Hoc Distribution (iPhone, without App Store)

For distributing to testers (up to 100 devices on free dev account):

### Step 1 — Archive the Build

1. Set scheme to **SamsungRemote-iOS**, destination to **Any iOS Device**
2. **Product → Archive**
3. Xcode Organizer opens with the archive

### Step 2 — Export IPA

1. In Organizer, click the archive → **Distribute App**
2. Choose **Ad Hoc**
3. Select your provisioning profile (ensure tester devices are registered)
4. Click **Export** — saves a `.ipa` file

### Step 3 — Install on Tester Device

**Via AltStore (no Mac required by testers):**
```bash
# Use AltServer on a shared Mac to push the IPA
altserver --install SamsungTVRemote.ipa --device <UDID>
```

**Via Apple Configurator 2:**
1. Open Apple Configurator 2 on a Mac
2. Drag the `.ipa` onto the connected iPhone icon

**Via Diawi / TestFlight (alternative):**
- Upload IPA to `diawi.com` → share link with testers (they open on iPhone)
- Or use TestFlight (requires paid Apple Developer account — see §5)

---

## Part 4 — Direct Mac App Distribution (outside App Store)

For distributing a `.app` to other Macs without App Store review:

### Step 1 — Archive

1. Set scheme to **SamsungRemote-macOS**, destination to **My Mac**
2. **Product → Archive**

### Step 2 — Export and Notarize

```bash
# Export signed app
xcodebuild -exportArchive \
  -archivePath ~/Desktop/SamsungTVRemote.xcarchive \
  -exportPath ~/Desktop/SamsungTVRemoteExport \
  -exportOptionsPlist ExportOptions-mac.plist
```

`ExportOptions-mac.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
  <key>method</key>
  <string>developer-id</string>
  <key>signingStyle</key>
  <string>automatic</string>
</dict>
</plist>
```

### Step 3 — Notarize (required for Gatekeeper)

macOS Gatekeeper blocks unsigned apps from running. Notarize with Apple:

```bash
# Submit for notarization
xcrun notarytool submit \
  ~/Desktop/SamsungTVRemoteExport/SamsungTVRemote.app \
  --apple-id "you@example.com" \
  --password "app-specific-password" \
  --team-id "YOUR_TEAM_ID" \
  --wait

# Staple the notarization ticket to the app
xcrun stapler staple ~/Desktop/SamsungTVRemoteExport/SamsungTVRemote.app
```

### Step 4 — Distribute as DMG

```bash
# Create a DMG for distribution
hdiutil create -volname "Samsung TV Remote" \
  -srcfolder ~/Desktop/SamsungTVRemoteExport/SamsungTVRemote.app \
  -ov -format UDZO \
  SamsungTVRemote.dmg
```

Send `SamsungTVRemote.dmg` to users. They drag the app to `/Applications`.

---

## Part 5 — TestFlight Distribution (beta testing)

TestFlight allows up to 10,000 external beta testers (requires paid Apple Developer account).

### Step 1 — Archive and Upload

```bash
# Archive
xcodebuild archive \
  -scheme SamsungRemote-iOS \
  -archivePath ~/Desktop/SamsungTVRemote.xcarchive \
  -destination 'generic/platform=iOS'

# Upload to App Store Connect
xcrun altool --upload-app \
  --type ios \
  --file ~/Desktop/SamsungTVRemote.xcarchive/Products/Applications/SamsungTVRemote.ipa \
  --apiKey YOUR_API_KEY_ID \
  --apiIssuer YOUR_ISSUER_ID
```

Or use Xcode Organizer: **Archive → Distribute App → App Store Connect → Upload**.

### Step 2 — Add Beta Testers

1. Go to `https://appstoreconnect.apple.com`
2. Select **Samsung TV Remote** app → **TestFlight** tab
3. **Internal Testing**: Add up to 100 team members (instant, no review)
4. **External Testing**: Click **+** next to External Groups → Enter tester emails → Submit for Beta App Review (1-2 day review)

### Step 3 — Tester Instructions

Send testers:
1. Install **TestFlight** from the App Store
2. Open the invite email link on their iPhone
3. Tap **Accept** → **Install**

---

## Build Configuration Reference

| Configuration | Use Case | Code Signing | Bundle ID Suffix |
|---|---|---|---|
| Debug | Development on device | Development cert | `.debug` optional |
| Ad Hoc | QA / limited testers | Distribution cert | (same as release) |
| TestFlight | Beta program | Distribution cert | (same as release) |
| Release | App Store / direct | Distribution cert | (none) |

---

## Environment-Specific Settings

| Setting | Debug | Release |
|---|---|---|
| SmartThings base URL | `api.smartthings.com` | `api.smartthings.com` |
| Local WS timeout | 5 seconds | 2 seconds |
| Verbose logging | ON | OFF |
| Analytics | OFF | ON (if added) |

Toggle via Xcode Build Settings → `DEBUG=1` compiler flag:
```swift
#if DEBUG
let wsTimeout: TimeInterval = 5.0
#else
let wsTimeout: TimeInterval = 2.0
#endif
```

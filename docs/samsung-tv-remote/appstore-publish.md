# Samsung TV Remote — App Store Publishing Guide

**Version:** 1.0
**Date:** 2026-03-08
**Covers:** iOS App Store + Mac App Store (two separate submissions, one developer account)

---

## Overview

| Store | App | Review Time |
|---|---|---|
| iOS App Store | SamsungRemote-iOS | 24–48 hours typically |
| Mac App Store | SamsungRemote-macOS | 24–48 hours typically |

Both stores use the same Apple Developer account ($99/year) and App Store Connect portal.

---

## Prerequisites

- [ ] Apple Developer Program membership (paid, $99/year)
  - Enroll at: `https://developer.apple.com/programs/enroll/`
- [ ] Final app version tested on a real iPhone and real Mac
- [ ] All crashes resolved (0 crashes in TestFlight for 48 hours is ideal)
- [ ] App Store Connect account configured
- [ ] App icons in all required sizes (see §3)
- [ ] Screenshots captured for all required device sizes (see §4)
- [ ] Privacy Policy URL hosted publicly

---

## 1. Create the App in App Store Connect

### iOS App

1. Go to `https://appstoreconnect.apple.com`
2. Click **My Apps → +** → **New App**
3. Fill in:
   - **Platforms:** iOS
   - **Name:** Samsung TV Remote
   - **Primary Language:** English (U.S.)
   - **Bundle ID:** `com.yourcompany.samsungremote.ios` (must match Xcode)
   - **SKU:** `SAMSUNG-TV-REMOTE-IOS` (internal, not user-visible)
4. Click **Create**

### Mac App

Repeat the above with:
- **Platforms:** macOS
- **Bundle ID:** `com.yourcompany.samsungremote.mac`
- **SKU:** `SAMSUNG-TV-REMOTE-MAC`

---

## 2. App Information (both apps)

Navigate to **App Information** tab for each app:

| Field | Suggested Value |
|---|---|
| Name | Samsung TV Remote |
| Subtitle | Control your Samsung Smart TV |
| Category | Utilities |
| Secondary Category | Entertainment |
| Content Rights | No third-party content |
| Age Rating | 4+ (no restricted content) |
| Privacy Policy URL | `https://yoursite.com/privacy` |

### App Description (use this draft)

```
Samsung TV Remote turns your iPhone or Mac into a full remote control for your Samsung Smart TV.

FEATURES
• Full D-pad navigation — up, down, left, right, OK, back, home, and menu
• Volume and channel control with a single tap
• Power on and off — even wake a sleeping TV from across the house
• App launcher — start Netflix, YouTube, Disney+, Prime Video, Hulu, and more directly
• Dual connection — blazing-fast local Wi-Fi control with automatic SmartThings cloud fallback
• Works remotely — control your TV from anywhere with a SmartThings account

SETUP IS SIMPLE
1. Enter your TV's IP address
2. Approve the pairing on your TV — one time only
3. Done. Start controlling.

COMPATIBILITY
Works with Samsung Smart TVs from 2016 onward (Tizen OS).
Local control requires the TV and your device to be on the same Wi-Fi network.
Remote (cloud) control requires a free Samsung SmartThings account.
```

### Keywords (100 characters max, comma-separated)

```
samsung,tv remote,smart tv,television,channel,volume,netflix,tizen,smartthings,remote control
```

---

## 3. App Icons

### iOS Icon Requirements

| Size | Usage |
|---|---|
| 1024×1024 px | App Store listing (required) |
| 180×180 px | iPhone @3x |
| 120×120 px | iPhone @2x |
| 167×167 px | iPad Pro @2x |
| 152×152 px | iPad @2x |

All icons must be PNG, no transparency, no rounded corners (iOS applies them).

**Add to Xcode:** Drag PNGs into `iOS/Assets.xcassets/AppIcon.appiconset/`.

Or use an icon generator tool:
```bash
# Generate all sizes from a single 1024×1024 source
uvx showboat exec docs/samsung-tv-remote/demo-session.md bash \
  "sips -Z 1024 AppIcon-1024.png --out AppIcon-1024.png && echo 'Icon ready'"
```

### macOS Icon Requirements

| Size | Usage |
|---|---|
| 1024×1024 px | App Store listing |
| 512×512 @2x | Finder |
| 256×256 @2x | Finder (smaller) |
| 128×128 | Finder (small) |
| 32×32 @2x | Toolbar |
| 16×16 @2x | Menu bar |

**Add to Xcode:** `macOS/Assets.xcassets/AppIcon.appiconset/`

---

## 4. Screenshots

Screenshots are required — no app can be submitted without them.

### iOS Screenshot Sizes Required

| Device | Resolution | Required? |
|---|---|---|
| iPhone 6.7" (15 Pro Max) | 1290×2796 | **Required** |
| iPhone 6.5" (14 Plus) | 1284×2778 | Required or inherited |
| iPhone 5.5" (8 Plus) | 1242×2208 | Required or inherited |
| iPad Pro 12.9" (6th gen) | 2048×2732 | Required if iPad supported |

Minimum: 1 screenshot, maximum: 10 per device size.

**Capture from Simulator:**
```bash
# Launch simulator, then capture
xcrun simctl io booted screenshot docs/samsung-tv-remote/screenshots/ios-main.png

# Or use rodney for automated screenshot in a browser-based test flow
uvx rodney start --show
uvx rodney open "http://localhost:3000/app-preview"   # if you have a web preview
uvx rodney screenshot -w 393 -h 852 docs/samsung-tv-remote/screenshots/app-preview.png
uvx rodney stop
```

### macOS Screenshot Sizes Required

| Size | Notes |
|---|---|
| 2560×1600 | MacBook Pro (required) |
| 2880×1800 | MacBook Pro Retina (if different content) |

**Capture from running Mac app:**
```bash
screencapture -w docs/samsung-tv-remote/screenshots/mac-main.png
# Select the app window when cursor changes
```

---

## 5. App Review Information

App Store Review team needs to test your app. Provide:

| Field | Value |
|---|---|
| Notes | "The app controls a Samsung Smart TV. For review, the SmartThings cloud API can be tested with the demo token below. Local WebSocket control requires a real Samsung TV on the same network — not required for review." |
| Demo Account | Create a SmartThings account at smartthings.com with a virtual device for reviewers |
| Demo Token | Generate a read/write token from your SmartThings demo account |

> **Tip:** Without a real Samsung TV, reviewers will still be able to exercise the full UI using the SmartThings cloud path and a virtual device. Add clear notes explaining this.

---

## 6. Pricing and Availability

| Setting | Recommendation |
|---|---|
| Price | Free (or $1.99 — your choice) |
| Availability | All App Store territories |
| Pre-Order | Not required |
| Phased Release | Enable (rolls out over 7 days, lets you catch issues) |

---

## 7. Build and Upload

### Step 1 — Increment Version

In Xcode → target → **General**:
- **Version:** `1.0.0` (user-visible, e.g. 1.0.0)
- **Build:** `1` (increment each submission, must be unique per version)

Or via command line:
```bash
xcrun agvtool new-marketing-version 1.0.0
xcrun agvtool new-version -all 1
```

### Step 2 — Archive iOS

```bash
xcodebuild archive \
  -scheme SamsungRemote-iOS \
  -archivePath ~/Desktop/SamsungTVRemote-iOS.xcarchive \
  -destination 'generic/platform=iOS' \
  -configuration Release
```

### Step 3 — Validate iOS Archive

```bash
xcrun altool --validate-app \
  --type ios \
  --file ~/Desktop/SamsungTVRemote-iOS.xcarchive \
  --apiKey YOUR_API_KEY_ID \
  --apiIssuer YOUR_ISSUER_ID
```

Or in Xcode Organizer: select archive → **Validate App** → follow wizard.

### Step 4 — Upload iOS

```bash
xcrun altool --upload-app \
  --type ios \
  --file ~/Desktop/SamsungTVRemote-iOS.xcarchive \
  --apiKey YOUR_API_KEY_ID \
  --apiIssuer YOUR_ISSUER_ID
```

Or in Xcode Organizer: **Distribute App → App Store Connect → Upload**.

### Step 5 — Repeat for macOS

```bash
xcodebuild archive \
  -scheme SamsungRemote-macOS \
  -archivePath ~/Desktop/SamsungTVRemote-macOS.xcarchive \
  -destination 'generic/platform=macOS' \
  -configuration Release

xcrun altool --upload-app \
  --type osx \
  --file ~/Desktop/SamsungTVRemote-macOS.xcarchive \
  --apiKey YOUR_API_KEY_ID \
  --apiIssuer YOUR_ISSUER_ID
```

---

## 8. Submit for Review

### iOS

1. In App Store Connect → **Samsung TV Remote (iOS)** → **App Store** tab
2. Select the build you just uploaded (may take 15–30 min to process)
3. Fill in all required fields (screenshots, description, review notes from §5)
4. Click **Add for Review** → **Submit to App Review**

### macOS

Same process under the macOS app listing.

---

## 9. Privacy Nutrition Labels

App Store Connect requires you to declare all data your app collects:

| Data Type | Collected? | Used For | Linked to Identity? |
|---|---|---|---|
| Contact Info | No | — | — |
| Identifiers (Device ID) | No | — | — |
| Usage Data | No | — | — |
| Diagnostics | No | — | — |
| Credentials (API token) | Yes | App Functionality | No (stored locally only) |

> The SmartThings token is stored in the device Keychain and never transmitted to any server other than `api.smartthings.com`. Select **"Not Linked to You"** and purpose **"App Functionality"**.

---

## 10. Post-Submission Checklist

- [ ] Watch App Store Connect for review status emails
- [ ] Monitor **Crashes** in Xcode Organizer → Crashes after launch
- [ ] Check **TestFlight** feedback tab for beta tester notes
- [ ] Respond to App Review rejection within 48 hours if needed
- [ ] Enable **Phased Release** — appears in the Release tab after approval
- [ ] Post release notes to users (version history visible on App Store page)

---

## 11. App API Key Setup (for CI/CD uploads)

Instead of using Apple ID + password for uploads, use an API key:

1. `https://appstoreconnect.apple.com` → **Users and Access → Keys**
2. Click **+**, name it "CI Upload Key", role: **App Manager**
3. Download the `.p8` file (download once — keep safe)
4. Note the **Key ID** and **Issuer ID**

Store in CI secrets:
```bash
export APP_STORE_CONNECT_KEY_ID="XXXXXXXXXX"
export APP_STORE_CONNECT_ISSUER_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export APP_STORE_CONNECT_KEY_PATH="/path/to/AuthKey_XXXXXXXXXX.p8"
```

Use with `xcrun altool` or Fastlane:
```bash
# With altool
xcrun altool --upload-app \
  --apiKey $APP_STORE_CONNECT_KEY_ID \
  --apiIssuer $APP_STORE_CONNECT_ISSUER_ID \
  ...

# With Fastlane deliver
fastlane deliver --api_key_path AuthKey.json
```

---

## 12. Common Rejection Reasons & Fixes

| Rejection | Fix |
|---|---|
| 2.1 — App is incomplete / crashes | Fix crashes shown in review feedback; test on oldest supported iOS |
| 4.0 — Copycat / clone | Ensure app has unique value; add original features |
| 5.1.1 — Data collection without consent | Add Privacy Policy URL; update nutrition labels |
| 2.5.4 — Background mode undeclared | Remove unused background modes from Info.plist |
| Local network — no description | Add `NSLocalNetworkUsageDescription` to Info.plist |
| Missing Demo Credentials | Provide SmartThings demo account token in Review Notes |

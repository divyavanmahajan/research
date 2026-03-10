#!/usr/bin/env bash
# =============================================================================
# Samsung TV Remote — Build & Deploy Script
# =============================================================================
# Usage:
#   ./build.sh ios          Build iOS and install on connected iPhone
#   ./build.sh mac          Build macOS and launch on this Mac
#   ./build.sh ios sim      Build iOS and run in iPhone Simulator
#   ./build.sh both         Build both iOS and macOS
#   ./build.sh clean        Clean all derived data
#
# Options (set as env vars or edit defaults below):
#   BUNDLE_ID_IOS   iOS bundle identifier        (default: com.samsungremote.ios)
#   BUNDLE_ID_MAC   macOS bundle identifier      (default: com.samsungremote.mac)
#   TEAM_ID         Apple Developer Team ID      (default: auto-detect from Xcode)
#   CONFIG          Build configuration          (default: Debug)
#   DEVICE_UDID     Specific device UDID to use  (default: first connected device)
# =============================================================================

set -euo pipefail

# ── Config defaults ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
DERIVED_DATA="$PROJECT_DIR/.build/DerivedData"
ARCHIVE_DIR="$PROJECT_DIR/.build/Archives"
EXPORT_DIR="$PROJECT_DIR/.build/Export"
LOG_DIR="$PROJECT_DIR/.build/Logs"

SCHEME_IOS="${SCHEME_IOS:-SamsungRemote-iOS}"
SCHEME_MAC="${SCHEME_MAC:-SamsungRemote-macOS}"
BUNDLE_ID_IOS="${BUNDLE_ID_IOS:-com.samsungremote.ios}"
BUNDLE_ID_MAC="${BUNDLE_ID_MAC:-com.samsungremote.mac}"
CONFIG="${CONFIG:-Debug}"
TEAM_ID="${TEAM_ID:-}"            # auto-detected if empty
DEVICE_UDID="${DEVICE_UDID:-}"   # auto-detected if empty

# Project file — looks for .xcodeproj; falls back to Package.swift (SPM)
XCODEPROJ=$(find "$PROJECT_DIR" -maxdepth 1 -name "*.xcodeproj" | head -1)
XCWORKSPACE=$(find "$PROJECT_DIR" -maxdepth 1 -name "*.xcworkspace" | head -1)

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()     { echo -e "${BLUE}▶${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
error()   { echo -e "${RED}✗${NC}  $*" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}\n"; }
die()     { error "$*"; exit 1; }

# ── Helpers ────────────────────────────────────────────────────────────────────

require_mac() {
  [[ "$(uname)" == "Darwin" ]] || die "This script must run on macOS."
}

require_xcode() {
  command -v xcodebuild &>/dev/null || \
    die "Xcode not found. Install from: https://developer.apple.com/xcode/"
  local ver; ver=$(xcodebuild -version 2>/dev/null | head -1)
  log "Using $ver"
}

resolve_project_flag() {
  if [[ -n "$XCWORKSPACE" ]]; then
    echo "-workspace $XCWORKSPACE"
  elif [[ -n "$XCODEPROJ" ]]; then
    echo "-project $XCODEPROJ"
  else
    # SPM project — use Package.swift
    echo ""
  fi
}

# Detect first connected physical iPhone via xcrun devicectl
find_connected_iphone() {
  if [[ -n "$DEVICE_UDID" ]]; then
    echo "$DEVICE_UDID"
    return
  fi
  # devicectl (Xcode 15+)
  if command -v xcrun &>/dev/null && xcrun devicectl list devices 2>/dev/null | grep -q "iPhone"; then
    xcrun devicectl list devices 2>/dev/null \
      | grep "iPhone" \
      | awk '{print $1}' \
      | head -1
    return
  fi
  # Legacy: instruments / cfgutil
  if command -v idevice_id &>/dev/null; then
    idevice_id -l | head -1
    return
  fi
  echo ""
}

# Best available iPhone Simulator UDID
find_simulator() {
  # Parse text output of simctl — avoids python3 stdin/heredoc conflict
  # Lines look like:  "    iPhone 16 Pro (XXXXXXXX-...) (Shutdown)"
  local udid=""
  local in_ios=0
  while IFS= read -r line; do
    if [[ "$line" =~ ^"-- iOS" ]]; then
      in_ios=1
    elif [[ "$line" =~ ^"-- " ]]; then
      in_ios=0
    elif [[ $in_ios -eq 1 && "$line" =~ "iPhone" ]]; then
      local candidate
      candidate=$(echo "$line" | grep -oE '[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}' | head -1)
      [[ -n "$candidate" ]] && udid="$candidate"
    fi
  done < <(xcrun simctl list devices available 2>/dev/null)
  echo "$udid"
}

detect_team_id() {
  [[ -n "$TEAM_ID" ]] && echo "$TEAM_ID" && return
  # Try to read from Xcode preferences
  defaults read com.apple.dt.Xcode IDEProvisioningTeams 2>/dev/null \
    | grep -m1 '"teamID"' | sed 's/.*= "\(.*\)".*/\1/' || echo ""
}

mkdir -p "$DERIVED_DATA" "$ARCHIVE_DIR" "$EXPORT_DIR" "$LOG_DIR"

# ── Build iOS ──────────────────────────────────────────────────────────────────

build_ios_device() {
  header "Building iOS — Device"
  local proj_flag; proj_flag=$(resolve_project_flag)
  local udid; udid=$(find_connected_iphone)
  local team; team=$(detect_team_id)
  local log_file="$LOG_DIR/ios-device-build.log"

  if [[ -z "$udid" ]]; then
    warn "No iPhone detected via USB."
    warn "Connect an iPhone and trust this Mac, then re-run."
    warn "Trying xcrun devicectl to list known devices…"
    xcrun devicectl list devices 2>/dev/null || true
    die "Cannot deploy to device — no iPhone found."
  fi

  log "Target device UDID: $udid"
  log "Config: $CONFIG"
  log "Logging to: $log_file"

  local team_args=()
  [[ -n "$team" ]] && team_args=(DEVELOPMENT_TEAM="$team")

  # shellcheck disable=SC2086
  xcodebuild \
    $proj_flag \
    -scheme "$SCHEME_IOS" \
    -configuration "$CONFIG" \
    -destination "id=$udid" \
    -derivedDataPath "$DERIVED_DATA" \
    ${team_args[@]+"${team_args[@]}"} \
    BUNDLE_IDENTIFIER="$BUNDLE_ID_IOS" \
    CODE_SIGN_STYLE=Automatic \
    clean build 2>&1 | tee "$log_file" | _build_filter

  success "iOS build complete."

  # Install app via xcrun devicectl (Xcode 15+) or fallback to ios-deploy
  local app_path
  app_path=$(find "$DERIVED_DATA/Build/Products" -name "*.app" -path "*-iphoneos*" | head -1)

  if [[ -z "$app_path" ]]; then
    die "Could not find built .app bundle. Check $log_file"
  fi

  log "Installing $app_path → device $udid"

  if xcrun devicectl device install app --device "$udid" "$app_path" 2>/dev/null; then
    success "App installed on iPhone."
    _launch_on_device "$udid" "$BUNDLE_ID_IOS"
  elif command -v ios-deploy &>/dev/null; then
    ios-deploy --bundle "$app_path" --id "$udid" --justlaunch
    success "App installed and launched (ios-deploy)."
  else
    warn "Could not auto-install. To install manually:"
    warn "  1. Open Xcode → Window → Devices and Simulators"
    warn "  2. Drag $app_path onto your iPhone"
    warn "Or install ios-deploy:  brew install ios-deploy"
  fi
}

build_ios_simulator() {
  header "Building iOS — Simulator"
  local proj_flag; proj_flag=$(resolve_project_flag)
  local sim_udid; sim_udid=$(find_simulator)
  local log_file="$LOG_DIR/ios-sim-build.log"

  if [[ -z "$sim_udid" ]]; then
    die "No available iPhone Simulator found. Open Xcode → Platforms and install iOS."
  fi

  log "Simulator UDID: $sim_udid"

  # Boot simulator if not running
  local sim_state
  sim_state=$(xcrun simctl list devices 2>/dev/null \
    | grep "$sim_udid" | grep -o "(Booted)" | tr -d '()' || echo "")
  if [[ "$sim_state" != "Booted" ]]; then
    log "Booting simulator…"
    xcrun simctl boot "$sim_udid" 2>/dev/null || true
    open -a Simulator 2>/dev/null || true
    sleep 3
  fi

  # shellcheck disable=SC2086
  xcodebuild \
    $proj_flag \
    -scheme "$SCHEME_IOS" \
    -configuration "$CONFIG" \
    -destination "id=$sim_udid" \
    -derivedDataPath "$DERIVED_DATA" \
    BUNDLE_IDENTIFIER="$BUNDLE_ID_IOS" \
    clean build 2>&1 | tee "$log_file" | _build_filter

  local build_exit=${PIPESTATUS[0]}
  if [[ $build_exit -ne 0 ]]; then
    error "Build failed (exit $build_exit). Check: $log_file"
    exit $build_exit
  fi
  success "iOS Simulator build complete."

  local app_path
  app_path=$(find "$DERIVED_DATA" -name "*.app" -path "*iphonesimulator*" 2>/dev/null | head -1)
  [[ -z "$app_path" ]] && die "Could not find .app for simulator. Check $log_file"

  log "Installing $app_path → simulator $sim_udid"
  xcrun simctl install "$sim_udid" "$app_path"
  xcrun simctl launch "$sim_udid" "$BUNDLE_ID_IOS"
  success "App launched in iPhone Simulator."
}

# ── Build macOS ────────────────────────────────────────────────────────────────

build_mac() {
  header "Building macOS"
  local log_file="$LOG_DIR/mac-build.log"
  local swift_config
  swift_config=$(echo "$CONFIG" | tr '[:upper:]' '[:lower:]')  # Debug→debug, Release→release

  log "Config: $CONFIG"
  log "Logging to: $log_file"

  # SPM project — use swift build directly (no .xcodeproj present)
  if [[ -z "$XCODEPROJ" && -z "$XCWORKSPACE" ]]; then
    swift build -c "$swift_config" 2>&1 | tee "$log_file"
    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -ne 0 ]]; then
      error "Build failed (exit $exit_code). Check: $log_file"
      exit $exit_code
    fi
    success "macOS build complete."

    # Locate the executable produced by swift build
    local bin_dir
    bin_dir=$(swift build -c "$swift_config" --show-bin-path 2>/dev/null)
    local exe_path="$bin_dir/SamsungRemote-macOS"

    if [[ -f "$exe_path" ]]; then
      log "Launching $exe_path"
      open "$exe_path"
      success "Mac app launched."
    else
      warn "Build succeeded but could not locate executable."
      warn "Expected: $exe_path"
    fi
    return
  fi

  # Xcode project / workspace — use xcodebuild
  local proj_flag; proj_flag=$(resolve_project_flag)
  local team; team=$(detect_team_id)
  local team_args=()
  [[ -n "$team" ]] && team_args=(DEVELOPMENT_TEAM="$team")

  # shellcheck disable=SC2086
  xcodebuild \
    $proj_flag \
    -scheme "$SCHEME_MAC" \
    -configuration "$CONFIG" \
    -destination "platform=macOS,arch=$(uname -m)" \
    -derivedDataPath "$DERIVED_DATA" \
    ${team_args[@]+"${team_args[@]}"} \
    BUNDLE_IDENTIFIER="$BUNDLE_ID_MAC" \
    CODE_SIGN_STYLE=Automatic \
    clean build 2>&1 | tee "$log_file" | _build_filter

  success "macOS build complete."

  local app_path
  app_path=$(find "$DERIVED_DATA/Build/Products" -name "*.app" \
    -not -path "*iphonesimulator*" -not -path "*iphoneos*" | head -1)

  if [[ -n "$app_path" ]]; then
    log "Launching $app_path"
    open "$app_path"
    success "Mac app launched."
  else
    warn "App built but could not auto-locate the .app bundle."
    warn "Check: $DERIVED_DATA/Build/Products/"
  fi
}

# ── Archive & Export (Release / TestFlight / App Store) ───────────────────────

archive_ios() {
  header "Archiving iOS (Release)"
  local proj_flag; proj_flag=$(resolve_project_flag)
  local archive_path="$ARCHIVE_DIR/SamsungRemote-iOS.xcarchive"
  local log_file="$LOG_DIR/ios-archive.log"
  local team; team=$(detect_team_id)
  [[ -z "$team" ]] && die "TEAM_ID required for archiving. Set: export TEAM_ID=XXXXXXXXXX"

  log "Archive → $archive_path"

  # shellcheck disable=SC2086
  xcodebuild archive \
    $proj_flag \
    -scheme "$SCHEME_IOS" \
    -configuration Release \
    -destination "generic/platform=iOS" \
    -archivePath "$archive_path" \
    DEVELOPMENT_TEAM="$team" \
    BUNDLE_IDENTIFIER="$BUNDLE_ID_IOS" \
    CODE_SIGN_STYLE=Automatic \
    2>&1 | tee "$log_file" | _build_filter

  success "iOS archive ready: $archive_path"

  # Write export options
  local export_opts="$EXPORT_DIR/ExportOptions-iOS.plist"
  cat > "$export_opts" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key>
  <string>development</string>
  <key>teamID</key>
  <string>$team</string>
  <key>signingStyle</key>
  <string>automatic</string>
  <key>compileBitcode</key>
  <false/>
</dict>
</plist>
PLIST

  log "Exporting IPA…"
  xcodebuild -exportArchive \
    -archivePath "$archive_path" \
    -exportPath "$EXPORT_DIR/iOS" \
    -exportOptionsPlist "$export_opts" \
    2>&1 | tee -a "$log_file"

  success "IPA exported to: $EXPORT_DIR/iOS/"
}

archive_mac() {
  header "Archiving macOS (Release)"
  local proj_flag; proj_flag=$(resolve_project_flag)
  local archive_path="$ARCHIVE_DIR/SamsungRemote-macOS.xcarchive"
  local log_file="$LOG_DIR/mac-archive.log"
  local team; team=$(detect_team_id)
  [[ -z "$team" ]] && die "TEAM_ID required for archiving. Set: export TEAM_ID=XXXXXXXXXX"

  # shellcheck disable=SC2086
  xcodebuild archive \
    $proj_flag \
    -scheme "$SCHEME_MAC" \
    -configuration Release \
    -destination "generic/platform=macOS" \
    -archivePath "$archive_path" \
    DEVELOPMENT_TEAM="$team" \
    BUNDLE_IDENTIFIER="$BUNDLE_ID_MAC" \
    CODE_SIGN_STYLE=Automatic \
    2>&1 | tee "$log_file" | _build_filter

  success "macOS archive ready: $archive_path"

  local export_opts="$EXPORT_DIR/ExportOptions-mac.plist"
  cat > "$export_opts" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key>
  <string>developer-id</string>
  <key>teamID</key>
  <string>$team</string>
  <key>signingStyle</key>
  <string>automatic</string>
</dict>
</plist>
PLIST

  log "Exporting .app…"
  xcodebuild -exportArchive \
    -archivePath "$archive_path" \
    -exportPath "$EXPORT_DIR/macOS" \
    -exportOptionsPlist "$export_opts" \
    2>&1 | tee -a "$log_file"

  success ".app exported to: $EXPORT_DIR/macOS/"
}

# ── Upload to App Store Connect ───────────────────────────────────────────────

upload_appstore() {
  local platform="$1"   # ios | mac
  header "Uploading $platform to App Store Connect"

  # Prefer API key auth (CI-safe) over Apple ID + password
  local key_id="${APP_STORE_CONNECT_KEY_ID:-}"
  local issuer="${APP_STORE_CONNECT_ISSUER_ID:-}"
  local key_path="${APP_STORE_CONNECT_KEY_PATH:-}"

  if [[ -z "$key_id" || -z "$issuer" || -z "$key_path" ]]; then
    warn "App Store Connect API key not configured."
    warn "Set these env vars:"
    warn "  APP_STORE_CONNECT_KEY_ID=XXXXXXXXXX"
    warn "  APP_STORE_CONNECT_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    warn "  APP_STORE_CONNECT_KEY_PATH=/path/to/AuthKey_XXXXXXXXXX.p8"
    die "Cannot upload without API credentials."
  fi

  local type archive_path
  if [[ "$platform" == "ios" ]]; then
    type="ios"
    archive_path="$ARCHIVE_DIR/SamsungRemote-iOS.xcarchive"
  else
    type="osx"
    archive_path="$ARCHIVE_DIR/SamsungRemote-macOS.xcarchive"
  fi

  [[ -d "$archive_path" ]] || die "Archive not found: $archive_path  (run: ./build.sh archive-$platform first)"

  xcrun altool --upload-app \
    --type "$type" \
    --file "$archive_path" \
    --apiKey "$key_id" \
    --apiIssuer "$issuer" \
    --verbose

  success "Upload complete — check App Store Connect for processing status."
}

# ── Clean ─────────────────────────────────────────────────────────────────────

clean_all() {
  header "Cleaning build artifacts"
  rm -rf "$DERIVED_DATA" "$ARCHIVE_DIR" "$EXPORT_DIR"
  log "Removed: $PROJECT_DIR/.build/"
  # Also clean via xcodebuild if project exists
  local proj_flag; proj_flag=$(resolve_project_flag)
  if [[ -n "$proj_flag" ]]; then
    # shellcheck disable=SC2086
    xcodebuild $proj_flag clean -configuration Debug  2>/dev/null || true
    # shellcheck disable=SC2086
    xcodebuild $proj_flag clean -configuration Release 2>/dev/null || true
  fi
  success "Clean complete."
}

# ── Private helpers ────────────────────────────────────────────────────────────

_launch_on_device() {
  local udid="$1" bundle="$2"
  if xcrun devicectl device process launch --device "$udid" "$bundle" 2>/dev/null; then
    success "App launched on device."
  else
    log "App installed. Open it manually on your iPhone."
  fi
}

# Filter xcodebuild output to key lines only
_build_filter() {
  grep -E "error:|warning:|BUILD SUCCEEDED|BUILD FAILED|Compiling|Linking|CodeSign" || true
}

# ── Usage ─────────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF

${BOLD}Samsung TV Remote — Build & Deploy${NC}

${BOLD}USAGE${NC}
  ./build.sh <command> [options]

${BOLD}COMMANDS${NC}
  ios               Build iOS and install on connected iPhone (USB)
  ios sim           Build iOS and run in iPhone Simulator
  mac               Build macOS app and launch it
  both              Build both iOS (device) and macOS
  archive-ios       Archive iOS for App Store / TestFlight (Release)
  archive-mac       Archive macOS for App Store / direct dist (Release)
  upload-ios        Upload iOS archive to App Store Connect
  upload-mac        Upload macOS archive to App Store Connect
  clean             Remove all build artifacts

${BOLD}ENVIRONMENT VARIABLES${NC}
  SCHEME_IOS        Xcode scheme for iOS  (default: SamsungRemote-iOS)
  SCHEME_MAC        Xcode scheme for macOS (default: SamsungRemote-macOS)
  BUNDLE_ID_IOS     iOS bundle ID          (default: com.samsungremote.ios)
  BUNDLE_ID_MAC     macOS bundle ID        (default: com.samsungremote.mac)
  TEAM_ID           Apple Developer Team ID (required for archive/upload)
  CONFIG            Build configuration    (default: Debug)
  DEVICE_UDID       Target device UDID     (default: first connected iPhone)
  APP_STORE_CONNECT_KEY_ID      API Key ID for App Store Connect
  APP_STORE_CONNECT_ISSUER_ID   API Issuer ID
  APP_STORE_CONNECT_KEY_PATH    Path to .p8 key file

${BOLD}EXAMPLES${NC}
  ./build.sh ios                    # Build debug + deploy to USB iPhone
  ./build.sh ios sim                # Build debug + run in Simulator
  ./build.sh mac                    # Build debug + launch on this Mac
  ./build.sh both                   # Build both targets

  CONFIG=Release ./build.sh mac     # Release build

  TEAM_ID=ABC123 ./build.sh archive-ios   # Archive for App Store
  TEAM_ID=ABC123 ./build.sh archive-mac

  APP_STORE_CONNECT_KEY_ID=X \\
  APP_STORE_CONNECT_ISSUER_ID=Y \\
  APP_STORE_CONNECT_KEY_PATH=./key.p8 \\
  ./build.sh upload-ios             # Upload to App Store Connect

${BOLD}TIPS${NC}
  - Install xcbeautify for cleaner output:  brew install xcbeautify
  - Install ios-deploy for device deploy fallback:  brew install ios-deploy
  - Logs are saved to: .build/Logs/

EOF
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
  require_mac
  require_xcode

  local cmd="${1:-help}"
  local opt2="${2:-}"

  case "$cmd" in
    ios)
      if [[ "$opt2" == "sim" || "$opt2" == "simulator" ]]; then
        build_ios_simulator
      else
        build_ios_device
      fi
      ;;
    mac|macos)
      build_mac
      ;;
    both)
      build_ios_device
      build_mac
      ;;
    archive-ios)
      archive_ios
      ;;
    archive-mac|archive-macos)
      archive_mac
      ;;
    upload-ios)
      archive_ios
      upload_appstore "ios"
      ;;
    upload-mac|upload-macos)
      archive_mac
      upload_appstore "mac"
      ;;
    clean)
      clean_all
      ;;
    help|--help|-h)
      usage
      ;;
    *)
      error "Unknown command: $cmd"
      usage
      exit 1
      ;;
  esac
}

main "$@"

# WhatsUp — Project Plan

## Vision

Build a WhatsApp-like end-to-end encrypted messaging application in pure Rust that:

- Implements the full **Signal Protocol** (X3DH + Double Ratchet + Sender Keys) from scratch
- Requires **zero external infrastructure** — one binary, embedded SQLite, no Docker
- Provides two clients: a **SvelteKit web app** and a **Ratatui terminal UI**
- Supports **two-factor authentication** via TOTP (RFC 6238)

---

## Milestones

### M1 — Cryptographic Foundation (complete)

- [x] X3DH key agreement (`whatsup-crypto/x3dh`)
  - Identity keys (X25519 DH + Ed25519 signing)
  - Signed prekeys with Ed25519 signature
  - One-time prekeys
  - Initiator and responder handshake paths
- [x] Double Ratchet session (`whatsup-crypto/double_ratchet`)
  - KDF chain (HMAC-SHA256 for chain keys, 48-byte message keys)
  - DH ratchet step
  - Out-of-order message delivery (skipped-key cache, `MAX_SKIP = 1000`)
  - AES-256-GCM encryption with authenticated header
- [x] Sender Keys for group messaging (`whatsup-crypto/sender_keys`)
  - `SenderKey` (chain key + signing key)
  - `SenderKeyDistributionMessage` serialisation
  - `GroupSession` encrypt/decrypt
- [x] Unit tests for all three subsystems

### M2 — Server Core (complete)

- [x] Database schema (SQLite WAL, 16 tables)
- [x] REST API (Axum): auth, users, key bundles, messages, groups, files
- [x] JWT access tokens (HS256, 15-minute TTL)
- [x] Refresh-token rotation with token-family replay detection
- [x] Two-factor authentication: TOTP setup/verify/disable, backup codes
- [x] WebSocket hub — ticket-based auth, per-user `mpsc` channel
- [x] File upload/download (multipart, server-side stored, client-side encrypted)
- [x] Pre-key replenishment notification (`PreKeyLow` event at ≤ 5 remaining OPKs)
- [x] CORS, request-body size limit (100 MB global)

### M3 — Protocol Layer (complete)

- [x] Shared wire types in `whatsup-protocol`:
  - `ClientEvent` / `ServerEvent` WebSocket envelopes
  - REST request/response structs
  - `Envelope` and `ConversationKind`

### M4 — Terminal Client (complete skeleton)

- [x] Ratatui TUI with three screens: Login, 2FA Challenge, Chat
- [x] REST client (`reqwest`) for login, 2FA, token management
- [x] WebSocket client stub (`tokio-tungstenite`)
- [x] Key navigation: Tab between fields, Enter to submit, Ctrl-C to quit

### M5 — Web Client (planned)

- [ ] SvelteKit scaffold (`whatsup-web`)
- [ ] JavaScript Signal Protocol client (WebCrypto API)
- [ ] Login / 2FA flow
- [ ] Conversation list and chat pane
- [ ] File attachment upload/download UI

### M6 — Production Hardening (planned)

- [ ] Integrate Prometheus metrics endpoint
- [ ] Rate limiting middleware (per-IP and per-user)
- [ ] Structured JSON logging in production mode
- [ ] Database migrations (versioned schema evolution)
- [ ] Graceful shutdown with connection drain
- [ ] CI pipeline (GitHub Actions): `cargo test`, `cargo clippy`, `cargo fmt`
- [ ] Docker image (optional — single static binary is the default)

---

## Dependency Inventory

| Crate | Purpose |
|---|---|
| `axum` | HTTP + WebSocket server framework |
| `tokio` | Async runtime |
| `rusqlite` | Embedded SQLite |
| `jsonwebtoken` | JWT encode/decode |
| `argon2` | Password hashing (Argon2id) |
| `totp-rs` | TOTP / RFC 6238 |
| `x25519-dalek` | X25519 Diffie-Hellman |
| `ed25519-dalek` | Ed25519 signing |
| `aes-gcm` | AES-256-GCM authenticated encryption |
| `hkdf` | HKDF key derivation (SHA-256) |
| `hmac` / `sha2` | HMAC-SHA256 for KDF chains |
| `rand` | Cryptographic randomness (OsRng) |
| `zeroize` | Secure memory zeroing for key material |
| `base64` | Base64 encoding for wire format |
| `serde` / `serde_json` | Serialisation |
| `uuid` | UUID v4 primary keys |
| `chrono` | Timestamps (RFC 3339 / ISO 8601) |
| `dashmap` | Lock-free concurrent hashmap for WS hub |
| `tower-http` | CORS, tracing, body-size middleware |
| `ratatui` | Terminal UI rendering |
| `crossterm` | Terminal input/output |
| `reqwest` | HTTP client (TUI) |
| `tokio-tungstenite` | WebSocket client (TUI) |

---

## Open Questions / Design Decisions

| Topic | Decision / Status |
|---|---|
| Message persistence | Ciphertexts stored server-side; server never has plaintext |
| Offline delivery | Messages stored until recipient connects and ACKs delivery |
| Key rotation | SPK rotation policy: client-initiated, not yet enforced server-side |
| Group membership changes | New member must receive sender keys from all existing members |
| File encryption | Client encrypts before upload; file_id referenced in message |
| Presence | last_seen_at updated on WS connect/disconnect; no live presence push yet |
| Web client crypto | Will use WebCrypto SubtleCrypto (ECDH P-256 or Curve25519 via wasm) |

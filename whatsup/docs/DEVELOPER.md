# WhatsUp — Developer Guide

## Prerequisites

| Tool | Minimum version | Purpose |
|---|---|---|
| Rust toolchain | 1.77 | Build all crates |
| Cargo | ships with Rust | Build / test |
| Node.js | 20 LTS | Web client (M5) |
| openssl CLI | any | Generate secrets |

Install Rust: https://rustup.rs

---

## Repository Layout

```
whatsup/
├── Cargo.toml              Workspace manifest (resolver = "2")
├── Cargo.lock
├── .env.example            Copy → .env and fill in secrets
├── README.md
├── docs/
│   ├── PLANS.md
│   ├── ARCHITECTURE.md     ← You are reading DEVELOPER.md
│   ├── DEVELOPER.md
│   └── CODE_WALKTHROUGH.md
└── crates/
    ├── whatsup-crypto/     Signal Protocol — pure Rust, no I/O
    ├── whatsup-protocol/   Shared wire types (serde JSON)
    ├── whatsup-server/     Axum server
    └── whatsup-tui/        Ratatui terminal client
```

---

## Initial Setup

### 1. Clone and enter the directory

```bash
git clone <repo-url>
cd whatsup
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Generate the two required secrets:

```bash
# JWT signing secret
openssl rand -hex 32

# TOTP encryption key
openssl rand -hex 32
```

Paste each output into `.env`:

```env
JWT_SECRET=<64 hex characters>
TOTP_ENCRYPTION_KEY=<64 hex characters>
```

All other values have sensible defaults and can be left as-is for local development.

### 3. Build

```bash
# Build everything in the workspace
cargo build

# Build only the server
cargo build -p whatsup-server

# Build only the TUI
cargo build -p whatsup-tui
```

### 4. Run the server

```bash
cargo run -p whatsup-server
```

The server will:
- Load configuration from `.env` (falls back to environment variables)
- Create `whatsup.db` and run `PRAGMA journal_mode=WAL` + schema creation on first start
- Create the `uploads/` directory if it does not exist
- Listen on `127.0.0.1:3000` by default
- Log at `info` level (set `RUST_LOG=debug` for more detail)

### 5. Run the TUI client

```bash
cargo run -p whatsup-tui
```

The TUI reads `~/.config/whatsup/config.toml` (or a `WHATSUP_CONFIG` env var path). If it does not exist, defaults to `http://127.0.0.1:3000`.

---

## Running Tests

```bash
# All workspace tests
cargo test

# Only the crypto crate
cargo test -p whatsup-crypto

# With output (useful for debugging)
cargo test -- --nocapture
```

The crypto crate has thorough unit tests covering:

- X3DH round-trip with and without a one-time prekey
- X3DH tampered-signature rejection
- Double Ratchet sequential and bidirectional messages
- Double Ratchet out-of-order delivery
- Double Ratchet message-key uniqueness and wrong-AD rejection
- Sender key distribution and group encrypt/decrypt

---

## Code Style & Linting

```bash
# Format
cargo fmt

# Lint
cargo clippy -- -D warnings
```

All new code should pass `clippy` without warnings. Use `#[allow(...)]` sparingly and with a comment.

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `HOST` | `127.0.0.1` | no | Bind address |
| `PORT` | `3000` | no | TCP port |
| `DATABASE_PATH` | `./whatsup.db` | no | SQLite file path |
| `JWT_SECRET` | — | **yes** | 64 hex chars (32 bytes); signs access tokens |
| `TOTP_ENCRYPTION_KEY` | — | **yes** | 64 hex chars (32 bytes); encrypts TOTP secrets at rest |
| `CORS_ORIGIN` | `http://localhost:5173` | no | Allowed CORS origin for the web client |
| `UPLOAD_DIR` | `./uploads` | no | Directory for uploaded files |
| `RUST_LOG` | `info` | no | Log level (`trace`, `debug`, `info`, `warn`, `error`) |

---

## Making API Calls (curl examples)

### Register

```bash
curl -s -X POST http://localhost:3000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"s3cr3t","display_name":"Alice"}'
```

### Login

```bash
curl -s -X POST http://localhost:3000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"s3cr3t"}'
```

Save the `access_token` as `$TOKEN`.

### Get own profile

```bash
curl -s http://localhost:3000/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### Upload a key bundle

```bash
curl -s -X PUT http://localhost:3000/keys/bundle \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "ik_public": "<base64>",
    "ik_public_ed": "<base64>",
    "spk_id": 1,
    "spk_public": "<base64>",
    "spk_signature": "<base64>",
    "one_time_prekeys": [{"id":1,"public_key":"<base64>"}]
  }'
```

### Open a WebSocket connection

```bash
# 1. Get a ticket
TICKET=$(curl -s -X POST http://localhost:3000/api/v1/auth/ws-ticket \
  -H "Authorization: Bearer $TOKEN" | jq -r .ticket)

# 2. Connect (requires websocat or wscat)
websocat "ws://localhost:3000/ws?ticket=$TICKET"
```

---

## Adding a New API Endpoint

1. Define request/response structs in `crates/whatsup-protocol/src/rest.rs`.
2. Implement the handler `async fn` in the appropriate `crates/whatsup-server/src/api/<module>.rs`.
3. Register the route in `crates/whatsup-server/src/api/mod.rs` (protected or unprotected router).
4. Add tests if the logic is non-trivial.

Handler signature pattern:

```rust
pub async fn my_handler(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>, // only for authenticated routes
    Json(req): Json<MyRequest>,
) -> Result<Json<MyResponse>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();
    // ...
}
```

---

## Adding a New WebSocket Event

1. Add a variant to `ClientEvent` or `ServerEvent` in `crates/whatsup-protocol/src/events.rs`.
2. Handle the new `ClientEvent` arm in `crates/whatsup-server/src/ws/handler.rs` → `handle_client_event`.
3. Send the new `ServerEvent` from any handler via `state.ws_hub.send(user_id, event)`.

---

## Database Schema Changes

The schema is applied idempotently on startup via `CREATE TABLE IF NOT EXISTS`. For additive changes (new tables, new columns with defaults) this is sufficient. For destructive changes, add a migration step before calling `schema::apply`.

Schema file: `crates/whatsup-server/src/db/schema.rs`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `JWT_SECRET must be set` | `.env` not found or variable missing | Copy `.env.example` → `.env` and fill in values |
| `JWT_SECRET must be valid hex` | Non-hex characters in the value | Run `openssl rand -hex 32` to generate a clean value |
| `database is locked` | Another process has the SQLite file open | Stop the other process |
| WS connection returns 401 | Ticket expired or already used | Request a new ticket from `/api/v1/auth/ws-ticket` |
| TUI shows blank screen | Terminal too small | Resize terminal to at least 80×24 |

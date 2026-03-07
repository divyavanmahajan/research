# WhatsUp — Claude Code Guide

## Project Overview

Rust workspace implementing a Signal-Protocol encrypted messaging server and TUI client. The server uses Axum, embedded SQLite (via r2d2 connection pool), and WebSockets.

## Workspace Crates

| Crate | Purpose |
|---|---|
| `whatsup-crypto` | X3DH key exchange, Double Ratchet session encryption, Sender Keys for groups |
| `whatsup-protocol` | Shared JSON wire types for REST and WebSocket messages |
| `whatsup-server` | Axum HTTP/WebSocket server, SQLite persistence, auth middleware |
| `whatsup-tui` | Ratatui terminal client |

## Build & Run

```bash
# Build all crates
cargo build

# Run the server (auto-creates whatsup.db)
cargo run -p whatsup-server

# Run the TUI client
cargo run -p whatsup-tui

# Run tests
cargo test

# Check only (faster than build)
cargo check
```

## Key Files

- `crates/whatsup-server/src/main.rs` — server entry point
- `crates/whatsup-server/src/db/schema.rs` — SQLite schema
- `crates/whatsup-server/src/db/writer.rs` — batched background write queue
- `crates/whatsup-server/src/api/` — REST route handlers
- `crates/whatsup-server/src/ws/` — WebSocket handler
- `crates/whatsup-crypto/src/x3dh/` — X3DH handshake
- `crates/whatsup-crypto/src/double_ratchet/` — Double Ratchet encryption

## Environment

Copy `.env.example` to `.env` before running. Required variables are documented in `.env.example`.

## Performance Notes

- Uses r2d2 connection pool to eliminate SQLite write contention
- Batched background writer for high-throughput message persistence
- Load tested to 1000 concurrent users — see `loadtests/` for results

## Testing

```bash
# Run the automated test harness
python harness.py

# Run load tests (see loadtests/HOW_TO_RUN.md)
```

## Conventions

- Crypto primitives: x25519-dalek, ed25519-dalek, aes-gcm, hkdf, sha2
- Error handling: thiserror for library errors, anyhow for application errors
- Async: Tokio runtime throughout
- Serialization: serde + serde_json

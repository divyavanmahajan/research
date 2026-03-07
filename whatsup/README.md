# WhatsUp

A WhatsApp-like end-to-end encrypted messaging application built in Rust.

## Features

- End-to-end encryption using the Signal Protocol (X3DH + Double Ratchet + Sender Keys)
- Two-factor authentication (TOTP — RFC 6238)
- 1:1 and group messaging
- File attachments (client-side encrypted)
- Real-time delivery via WebSocket
- Read receipts and typing indicators
- Terminal client (Ratatui TUI) and planned SvelteKit web client
- Zero external infrastructure — embedded SQLite, no Docker required

## Architecture

```
whatsup/
├── crates/
│   ├── whatsup-crypto/    Signal Protocol: X3DH, Double Ratchet, Sender Keys
│   ├── whatsup-protocol/  Shared wire types (JSON)
│   ├── whatsup-server/    Axum REST + WebSocket server
│   └── whatsup-tui/       Ratatui terminal client
├── docs/
│   ├── ARCHITECTURE.md    Security model and system design
│   ├── DEVELOPER.md       Developer setup and conventions
│   ├── CODE_WALKTHROUGH.md Line-by-line code guide
│   └── PLANS.md           Roadmap and planned features
├── loadtests/             Load test logs and summaries (100–1000 users)
└── harness.py             Test harness for automated workflow testing
```

## Quick Start

```bash
# Start the server (creates whatsup.db automatically)
cargo run -p whatsup-server

# Use the terminal client
cargo run -p whatsup-tui
```

## Load Test Results

The server has been tested at up to 1000 concurrent users. See [`loadtests/INDEX.md`](loadtests/INDEX.md) for full results and [`loadtests/HOW_TO_RUN.md`](loadtests/HOW_TO_RUN.md) to reproduce.

## Security

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full security model. All messages are encrypted client-side — the server stores only ciphertext and never has access to message content or private keys.

## Documentation

| Document | Description |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Security model, protocol design, component overview |
| [`docs/DEVELOPER.md`](docs/DEVELOPER.md) | Dev setup, conventions, how to run and test |
| [`docs/CODE_WALKTHROUGH.md`](docs/CODE_WALKTHROUGH.md) | Annotated walkthrough of key code paths |
| [`docs/PLANS.md`](docs/PLANS.md) | Roadmap and open issues |

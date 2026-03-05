# WhatsUp

A WhatsApp-like end-to-end encrypted messaging application built in Rust.

## Features

- End-to-end encryption using the Signal Protocol (X3DH + Double Ratchet + Sender Keys)
- Two-factor authentication (TOTP — RFC 6238)
- 1:1 and group messaging
- File attachments (client-side encrypted)
- Real-time delivery via WebSocket
- Read receipts and typing indicators
- Web client (SvelteKit) and terminal client (Ratatui TUI)
- Zero external infrastructure — embedded SQLite, no Docker required

## Architecture

```
whatsup/
├── crates/
│   ├── whatsup-crypto/    Signal Protocol: X3DH, Double Ratchet, Sender Keys
│   ├── whatsup-protocol/  Shared wire types (JSON)
│   ├── whatsup-server/    Axum REST + WebSocket server
│   ├── whatsup-web/       SvelteKit web client
│   └── whatsup-tui/       Ratatui terminal client
└── docs/
    ├── PLANS.md
    ├── ARCHITECTURE.md
    ├── DEVELOPER.md
    └── CODE_WALKTHROUGH.md
```

## Quick Start

```bash
# Start the server (creates whatsup.db automatically)
cargo run -p whatsup-server

# Open the web client
cd crates/whatsup-web && npm install && npm run dev

# Or use the terminal client
cargo run -p whatsup-tui
```

## Security

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full security model.
All messages are encrypted client-side. The server stores only ciphertext and never has access to message content or private keys.

# WhatsUp — Code Walkthrough

This document traces the key data flows through the codebase from startup to message delivery.

---

## 1. Server Startup (`crates/whatsup-server/src/main.rs`)

```
main()
  ├─ tracing_subscriber::fmt() + EnvFilter  → structured logging to stdout
  ├─ Config::from_env()                      → reads .env / environment variables
  ├─ db::open(&config.database_path)         → opens SQLite, applies schema
  ├─ AppState::new(config, db)               → creates shared state (Arc<WsHub>, Arc<Config>, Db)
  ├─ CorsLayer                               → restricts origins to CORS_ORIGIN
  ├─ Router::new()
  │   ├─ GET  /health       → health handler
  │   ├─ GET  /ws           → ws::handler::ws_handler
  │   └─ api::router(state) → all /api/v1/… routes
  └─ axum::serve(TcpListener::bind(host:port), app)
```

Key types:
- `AppState` (`state.rs`): `Clone`-able wrapper around `Arc<Config>`, `Arc<Mutex<Connection>>` (the `Db` type alias), and `Arc<WsHub>`.
- `WsHub` (`state.rs`): `DashMap<UserId, mpsc::UnboundedSender<ServerEvent>>` — the in-process message bus for WebSocket connections.

---

## 2. Database Initialisation (`crates/whatsup-server/src/db/`)

`db::open` (in `db/mod.rs`) calls `rusqlite::Connection::open`, then `schema::apply` which runs a single `execute_batch` with all `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements.

Pragmas applied at schema time:
- `PRAGMA journal_mode=WAL` — allows concurrent readers while a writer is active
- `PRAGMA foreign_keys=ON` — enforces referential integrity

---

## 3. Authentication Flow (`crates/whatsup-server/src/api/auth.rs`)

### 3a. Registration — `POST /api/v1/auth/register`

```
RegisterRequest { username, password, display_name, phone_number? }
  → argon2id(password, random_salt)   → password_hash
  → INSERT INTO users                 → user_id (UUID v4)
  → 201 Created { user_id }
```

Argon2id parameters: m=65536 KiB, t=3 iterations, p=4 lanes.

### 3b. Login — `POST /api/v1/auth/login`

```
LoginRequest { username, password }
  → SELECT id, password_hash FROM users WHERE username = ?
  → argon2::verify_password(password, stored_hash)
  → SELECT enabled FROM totp_secrets WHERE user_id = ?
      ├─ enabled=false → issue_tokens() → { access_token, refresh_token, expires_in }
      └─ enabled=true  → INSERT INTO two_fa_challenges
                       → { status:"2fa_required", challenge_token }
```

### 3c. Token issuance — `issue_tokens()`

```
→ JWT HS256 { sub: user_id, iat, exp: now+900 }   → access_token
→ OsRng 32 random bytes → hex string               → refresh_token (returned to client)
→ SHA-256(refresh_token)                           → token_hash (stored)
→ INSERT INTO refresh_tokens { id, user_id, token_hash, family_id, expires_at }
→ { access_token, refresh_token, expires_in: 900 }
```

### 3d. Refresh — `POST /api/v1/auth/refresh`

```
RefreshRequest { refresh_token }
  → token_hash = SHA-256(refresh_token)
  → SELECT id, user_id, family_id, expires_at FROM refresh_tokens WHERE token_hash = ?
  → check expiry
  → DELETE FROM refresh_tokens WHERE id = ?  (atomic consume)
      ├─ 1 row deleted → issue_tokens() (rotation)
      └─ 0 rows deleted → DELETE entire family → 401 (replay detected)
```

### 3e. WebSocket ticket — `POST /api/v1/auth/ws-ticket`

```
(requires valid Bearer JWT)
→ INSERT INTO ws_tickets { id: UUID, user_id, expires_at: now+60s }
→ { ticket: UUID }
```

---

## 4. Authentication Middleware (`crates/whatsup-server/src/middleware/auth.rs`)

All protected routes use `require_auth`:

```
Authorization: Bearer <jwt>
  → jsonwebtoken::decode(jwt, HS256, JWT_SECRET)
  → validates exp, extracts sub (user_id)
  → inserts Claims into request Extensions
  → calls next handler
```

Handlers extract the caller's identity via `Extension(claims): Extension<Claims>`.

---

## 5. Key Bundle Upload & Retrieval (`crates/whatsup-server/src/api/keys.rs`)

### Upload — `PUT /keys/bundle`

Client calls this after registration to publish its public keys:

```
UploadKeyBundleRequest {
  ik_public (base64 X25519), ik_public_ed (base64 Ed25519),
  spk_id, spk_public (base64 X25519), spk_signature (base64 Ed25519 sig),
  one_time_prekeys: [{ id, public_key }…]
}
  → INSERT OR REPLACE INTO identity_keys
  → INSERT OR REPLACE INTO signed_prekeys
  → INSERT INTO one_time_prekeys (batch)
  → 204 No Content
```

### Fetch — `GET /keys/bundle/:user_id`

Called by a client wanting to start a 1:1 session with another user:

```
→ SELECT ik_public, ik_public_ed FROM identity_keys WHERE user_id = ?
→ SELECT id, spk_public, spk_signature FROM signed_prekeys WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
→ SELECT id, opk_public FROM one_time_prekeys WHERE user_id = ? AND consumed_at IS NULL LIMIT 1
→ UPDATE one_time_prekeys SET consumed_at = now WHERE id = ?   (consume OPK)
→ if remaining OPKs ≤ 5: ws_hub.send(user_id, ServerEvent::PreKeyLow { remaining })
→ KeyBundleResponse { user_id, ik_public, ik_public_ed, spk_id, spk_public, spk_signature, opk_id?, opk_public? }
```

---

## 6. Crypto — X3DH (`crates/whatsup-crypto/src/x3dh/`)

### Key types

| File | Type | Description |
|---|---|---|
| `identity_key.rs` | `IdentityKeyPair` | X25519 `dh_secret` + Ed25519 `signing_key` |
| `identity_key.rs` | `IdentityKeyPublic` | X25519 + Ed25519 public bytes; `verify()` + `dh_public_key()` |
| `signed_prekey.rs` | `SignedPreKey` | X25519 `secret`; `to_public(&ik)` signs with IK Ed25519 |
| `one_time_prekey.rs` | `OneTimePreKey` | X25519 `secret`; `to_public()` returns id + public bytes |
| `key_bundle.rs` | `PreKeyBundle` | `{user_id, identity_key, signed_prekey, one_time_prekey?}` |

### `initiate(alice_ik, bob_bundle)` → `(SharedSecret, InitMessage)`

```
1. Verify bob_bundle.signed_prekey.signature against bob_bundle.identity_key (Ed25519)
2. Generate ephemeral key EK_A (X25519, OsRng)
3. DH1 = DH(IK_A.dh_secret, SPK_B)          Alice identity × Bob signed prekey
4. DH2 = DH(EK_A, IK_B.dh_public)           Alice ephemeral × Bob identity
5. DH3 = DH(EK_A, SPK_B)                     Alice ephemeral × Bob signed prekey
6. [DH4 = DH(EK_A, OPK_B)]                  Optional, if OPK present
7. IKM = 0xFF×32 ‖ DH1 ‖ DH2 ‖ DH3 [‖ DH4]
8. SK = HKDF-SHA256(IKM, info="WhatsUp_X3DH_v1")
9. Return (SK, InitMessage { ik_public: alice's, ek_public, spk_id, opk_id? })
```

### `respond(bob_ik, bob_spk, bob_opk?, init_msg)` → `SharedSecret`

Mirrors the DH operations with Bob's private keys, producing the same SK.

---

## 7. Crypto — Double Ratchet (`crates/whatsup-crypto/src/double_ratchet/`)

### Chain KDF (`chain.rs`)

```
kdf_ck(chain_key: &[u8; 32]) → (new_chain_key: [u8; 32], message_key: [u8; 48])
  HMAC-SHA256(chain_key, 0x01) → new_chain_key
  HMAC-SHA256(chain_key, 0x02) → message_key (32 bytes key + 12 bytes nonce + 4 bytes padding)

kdf_rk(root_key: &[u8; 32], dh_output: &[u8]) → (new_root_key, chain_key)
  HKDF-SHA256(ikm=dh_output, salt=root_key, info="WhatsUp_DR_v1")
  output length = 64 bytes → split into two 32-byte halves
```

### Session state (`state.rs`)

```rust
struct RatchetState {
    root_key: [u8; 32],
    cks: Option<[u8; 32]>,   // sending chain key
    ckr: Option<[u8; 32]>,   // receiving chain key
    ns: u32,                  // number of messages sent in current chain
    nr: u32,                  // number of messages received in current chain
    pn: u32,                  // messages sent in previous sending chain
    dhs_secret: StaticSecret, // our current ratchet DH secret
    dhr_pub: Option<X25519PublicKey>, // their current ratchet DH public
    skipped: HashMap<SkipKey, [u8; 48]>, // buffered out-of-order keys
}

const MAX_SKIP: usize = 1000;
```

### Session encrypt (`session.rs`)

```
encrypt(plaintext, ad):
  1. kdf_ck(cks) → (new_cks, mk)
  2. header = { dh_pub: our current ratchet public, pn, n: ns }
  3. ns += 1
  4. aes_gcm_encrypt(mk, header_bytes, plaintext, ad)
     key = mk[0..32], nonce = mk[32..44]
     AAD = header_bytes ‖ ad
  5. Return EncryptedMessage { header, ciphertext }
```

### Session decrypt (`session.rs`)

```
decrypt(msg, ad):
  1. Check skipped-key cache for (dh_pub, n) → decrypt directly if found
  2. If msg.header.dh_pub ≠ current dhr_pub:
       a. skip_message_keys(msg.header.pn)   → buffer remaining receiving chain keys
       b. dh_ratchet(their_dh):
            - DH with current dhs_secret × their_dh → kdf_rk → new root key + ckr
            - Generate new dhs_secret → DH × their_dh → kdf_rk → new root key + cks
  3. skip_message_keys(msg.header.n)         → buffer any skipped messages in new chain
  4. kdf_ck(ckr) → (new_ckr, mk); nr += 1
  5. aes_gcm_decrypt(mk, header_bytes, ciphertext, ad)
```

---

## 8. Crypto — Sender Keys (`crates/whatsup-crypto/src/sender_keys/`)

### Key types

| File | Type | Description |
|---|---|---|
| `sender_key.rs` | `SenderKey` | `chain_key: [u8; 32]` + `signing_key: Ed25519SigningKey` |
| `distribution.rs` | `SenderKeyDistributionMessage` | Serialisable `{sender_key_id, chain_key_bytes, signing_key_bytes}` |
| `group_session.rs` | `GroupSession` | `HashMap<String, SenderKey>` (sender_id → SenderKey) |

### Group message flow

```
Sender:
  skdm = my_sender_key.to_distribution_message()
  For each group member:
    encrypt skdm.serialise() using 1:1 Double Ratchet → send via ClientEvent::SenderKeyDistribute

  encrypt(plaintext):
    mk = HMAC-SHA256(chain_key, 0x01)   (message key)
    chain_key = HMAC-SHA256(chain_key, 0x02) (advance)
    sig = Ed25519.sign(ciphertext)
    Return SenderKeyMessage { sender_id, chain_key_id, ciphertext, signature }

Recipient:
  decrypt(msg):
    sk = session.sender_keys[msg.sender_id]
    verify Ed25519 signature
    advance chain_key to matching key_id
    AES-256-GCM decrypt
```

---

## 9. Message Send (`crates/whatsup-server/src/api/messages.rs`)

### `POST /messages/send`

```
SendMessageRequest { message_id, kind, to, ciphertext, message_type, file_id? }
  kind="direct":
    → find or create conversation (ordered user_id pair, CHECK participant_a < participant_b)
    → INSERT INTO messages { id, conversation_id, sender_id, recipient_id, ciphertext, … }
    → if recipient is online: ws_hub.send(recipient_id, ServerEvent::NewMessage { … })
    → 200 OK { message_id }

  kind="group":
    → verify caller is member of groups/:to
    → INSERT INTO messages { id, group_id, sender_id, ciphertext, … }
    → for each other online member: ws_hub.send(member_id, ServerEvent::NewMessage { … })
    → 200 OK { message_id }
```

---

## 10. WebSocket Connection (`crates/whatsup-server/src/ws/handler.rs`)

### Upgrade — `GET /ws?ticket=<uuid>`

```
ws_handler:
  1. SELECT user_id, expires_at FROM ws_tickets WHERE id = ?ticket
  2. Check not expired
  3. DELETE the ticket (single-use)
  4. UPDATE users SET last_seen_at = now WHERE id = user_id
  5. ws.on_upgrade(|socket| handle_socket(socket, state, user_id))
```

### `handle_socket`

```
split WebSocket → (ws_tx, ws_rx)
create mpsc::unbounded_channel() → (tx, rx)
ws_hub.register(user_id, tx)

spawn write_task:
  loop: rx.recv() → serde_json::to_string(event) → ws_tx.send(Message::Text)

read loop (current task):
  ws_rx.next() → Message::Text → serde_json::from_str::<ClientEvent>
               → handle_client_event(&state, &user_id, event)
  on Close → break

cleanup:
  ws_hub.unregister(user_id)
  write_task.abort()
  UPDATE users SET last_seen_at = now
```

### `handle_client_event`

| Event | Action |
|---|---|
| `Ping` | `ws_hub.send(user_id, ServerEvent::Pong)` |
| `AckDelivery { message_id }` | `UPDATE messages SET delivered_at`; notify sender via `ServerEvent::MessageDelivered` |
| `AckRead { message_id }` | `UPDATE messages SET read_at`; notify sender via `ServerEvent::MessageRead` |
| `Typing { conversation_id, is_typing }` | Fan-out `TypingStart` / `TypingStop` to conversation partner |
| `SendMessage` | Mirrors REST send (useful for TUI WS-only mode) |
| `SenderKeyDistribute` | Store SKDM for recipient retrieval |

---

## 11. TUI Client (`crates/whatsup-tui/`)

### Entry point (`main.rs`)

```
Config::load()   →  reads server URL from config file / env
App::new(config) →  creates RestClient, default AppState
app.run()        →  enters Ratatui event loop
```

### Screen state machine (`state/mod.rs`)

```rust
enum AppScreen {
    Login,
    TwoFaChallenge { challenge_token: String },
    Chat,
}
```

### Event loop (`app.rs`)

```
loop:
  terminal.draw(|f| ui::draw(f, &state))   ← renders current screen
  event::poll(100ms)
    Key(Ctrl-C)   → break
    Key(other)    → handle_key(code) dispatches to:
      handle_login_key()     → Tab/Char/Backspace/Enter
      handle_2fa_key()       → Char/Backspace/Esc/Enter
      handle_chat_key()      → Char/Backspace/Up/Down/Enter
```

### REST client (`net/rest.rs`)

Uses `reqwest::Client`. Key methods:
- `login(username, password)` → `LoginResponse` (tokens or 2FA challenge)
- `two_fa_challenge(challenge_token, otp_code)` → `AuthTokens`
- `get_me()` → `UserProfile`
- HTTP calls set `Authorization: Bearer <token>` via a stored `token` field on the client

### WebSocket client (`net/ws.rs`)

Stub using `tokio-tungstenite`. Connects to `ws://<server>/ws?ticket=<ticket>` and drives a read/write loop that translates between the TUI event system and `ClientEvent` / `ServerEvent` JSON frames.

---

## 12. Protocol Types (`crates/whatsup-protocol/`)

All types derive `serde::Serialize + Deserialize`. The two key modules:

- **`events.rs`**: `ClientEvent` and `ServerEvent` tagged enums (`#[serde(tag="type", content="payload", rename_all="PascalCase")]`).
- **`rest.rs`**: Request/response structs for every REST endpoint.
- **`messages.rs`**: `Envelope` (thin wrapper for a ciphertext + routing info) and `ConversationKind`.
- **`error.rs`**: `ProtocolError` enum.

The `whatsup-crypto` crate uses `CryptoError` (`error.rs`) separately and is not exposed in the protocol layer — the protocol only carries base64-encoded opaque blobs.

# WhatsUp — Architecture & Security Model

## System Overview

```
┌────────────────────────────────────────────────────────────┐
│                        Clients                             │
│                                                            │
│   ┌──────────────────┐       ┌──────────────────────────┐  │
│   │  whatsup-tui     │       │  whatsup-web (SvelteKit) │  │
│   │  (Ratatui/Rust)  │       │  (browser)               │  │
│   └────────┬─────────┘       └───────────┬──────────────┘  │
└────────────│───────────────────────────── │ ───────────────┘
             │  HTTPS REST + WSS            │
             ▼                              ▼
┌────────────────────────────────────────────────────────────┐
│                  whatsup-server (Axum)                     │
│                                                            │
│   ┌──────────┐  ┌────────┐  ┌──────────┐  ┌───────────┐   │
│   │ /api/v1  │  │  /ws   │  │  CORS    │  │  Tracing  │   │
│   │  routes  │  │ handler│  │ middleware│  │  layer    │   │
│   └────┬─────┘  └───┬────┘  └──────────┘  └───────────┘   │
│        │             │                                      │
│        └──────┬──────┘                                     │
│               ▼                                            │
│   ┌───────────────────────┐   ┌────────────────────────┐   │
│   │      AppState         │   │        WsHub           │   │
│   │  Arc<Config>          │   │  DashMap<UserId,       │   │
│   │  Db (Arc<Mutex<…>>)   │   │    mpsc::Sender>       │   │
│   └───────────┬───────────┘   └────────────────────────┘   │
│               │                                            │
│               ▼                                            │
│   ┌───────────────────────┐                               │
│   │  SQLite (WAL mode)    │                               │
│   │  whatsup.db           │                               │
│   └───────────────────────┘                               │
└────────────────────────────────────────────────────────────┘
```

---

## Crate Structure

| Crate | Role |
|---|---|
| `whatsup-crypto` | Signal Protocol primitives — no I/O, no async, pure crypto |
| `whatsup-protocol` | Shared wire types used by server and clients |
| `whatsup-server` | Axum HTTP/WebSocket server with embedded SQLite |
| `whatsup-tui` | Ratatui terminal client |
| `whatsup-web` | SvelteKit web client (planned) |

---

## Security Model

### Threat Model

The server is treated as **honest-but-curious**: it stores and routes messages faithfully but must not learn their content. Private keys and plaintext **never leave the client**.

| Asset | Protected by |
|---|---|
| Message content | E2E encryption (Double Ratchet / AES-256-GCM) |
| Session establishment | X3DH key agreement |
| Group message content | Sender Keys (Signal group protocol) |
| File content | Client-side AES-256-GCM before upload |
| Passwords | Argon2id (m=64 MiB, t=3, p=4) |
| TOTP secrets at rest | AES-256-GCM with server-side `TOTP_ENCRYPTION_KEY` |
| Access tokens | HS256 JWT, 15-minute TTL |
| Refresh tokens | SHA-256 hashed before storage; token-family rotation |
| WebSocket auth | Single-use ticket (60 s TTL), burned on first use |

### Signal Protocol — Key Hierarchy

```
Identity Key Pair (IK)
  ├─ X25519 private key  → used in X3DH DH operations
  └─ Ed25519 signing key → signs the Signed PreKey

Signed PreKey (SPK)     → rotated by client, signed by IK Ed25519
One-Time PreKeys (OPK)  → consumed once per session establishment

X3DH produces a 32-byte Shared Secret (SK):
  IKM = 0xFF×32 ‖ DH(IK_A, SPK_B) ‖ DH(EK_A, IK_B) ‖ DH(EK_A, SPK_B) [‖ DH(EK_A, OPK_B)]
  SK  = HKDF-SHA256(IKM, info="WhatsUp_X3DH_v1")

Double Ratchet (per session):
  Root Key ──KDF──► (new Root Key, Chain Key)
  Chain Key ──KDF──► (new Chain Key, Message Key 48 bytes)
  Message Key: [0..32] = AES-256 key, [32..44] = GCM nonce
  Plaintext encrypted with AES-256-GCM, header as AAD

Sender Keys (groups):
  Each sender generates a SenderKey (chain key + signing key)
  Distributes it to every group member over their 1:1 Double Ratchet session
  Group messages encrypted with the sender's current chain key
```

### Authentication Flow

```
1. POST /api/v1/auth/register
   → Argon2id hash stored; user_id (UUIDv4) returned

2. POST /api/v1/auth/login
   a. 2FA disabled → access_token + refresh_token returned
   b. 2FA enabled  → challenge_token returned (5-minute TTL, 5-attempt limit)
      POST /api/v1/auth/2fa/challenge {challenge_token, otp_code}
      → access_token + refresh_token returned

3. POST /api/v1/auth/refresh  (with refresh_token)
   → old token deleted, new token pair issued (rotation)
   → token reuse detected → entire token family revoked

4. POST /api/v1/auth/ws-ticket  (requires Bearer token)
   → single-use WS ticket (60 s TTL)
   GET /ws?ticket=<uuid>
   → ticket validated and burned; WS connection established
```

---

## Database Schema

16 tables in `whatsup.db` (SQLite, WAL journal mode, foreign keys ON):

| Table | Description |
|---|---|
| `users` | Account records; `password_hash` (Argon2id) |
| `refresh_tokens` | Hashed refresh tokens with `family_id` for rotation |
| `identity_keys` | Users' X25519 + Ed25519 public identity keys |
| `signed_prekeys` | Current signed prekey per user |
| `one_time_prekeys` | Pool of OPKs; `consumed_at` marks used ones |
| `conversations` | Direct 1:1 conversation records (ordered participant pair) |
| `groups` | Group metadata |
| `group_members` | Many-to-many; `role` is `admin` or `member` |
| `messages` | Ciphertext blobs; belongs to a conversation OR group |
| `files` | File metadata; actual bytes on filesystem |
| `sender_keys` | SKDM ciphertexts stored for recipient retrieval |
| `totp_secrets` | AES-256-GCM encrypted TOTP secret; `enabled` flag |
| `backup_codes` | Argon2id-hashed 2FA backup codes (8 per user) |
| `otp_used` | Anti-replay table for TOTP codes (pruned after 3 windows) |
| `two_fa_challenges` | Short-lived 2FA challenge tokens |
| `ws_tickets` | Single-use WebSocket upgrade tokens |

---

## API Surface

### Unauthenticated

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — returns `{status:"ok", version}` |
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Password login; returns tokens or 2FA challenge |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | Revoke refresh token |
| `POST` | `/api/v1/auth/2fa/challenge` | Complete 2FA after login |

### Authenticated (Bearer JWT)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/2fa/setup` | Generate TOTP secret, returns QR code |
| `POST` | `/api/v1/auth/2fa/verify` | Enable 2FA, returns backup codes |
| `POST` | `/api/v1/auth/2fa/disable` | Disable 2FA (requires password + OTP) |
| `POST` | `/api/v1/auth/ws-ticket` | Issue single-use WS ticket |
| `GET` | `/users/me` | Own profile |
| `PATCH` | `/users/me` | Update display name / avatar |
| `GET` | `/users/search?q=` | Search users by username |
| `GET` | `/users/:id` | Get any user profile |
| `PUT` | `/keys/bundle` | Upload identity + signed + one-time prekeys |
| `GET` | `/keys/bundle/:user_id` | Fetch a user's prekey bundle (consumes one OPK) |
| `POST` | `/keys/prekeys` | Replenish one-time prekeys |
| `GET` | `/keys/prekey-count` | Count remaining unconsumed OPKs |
| `POST` | `/messages/send` | Send an encrypted message |
| `GET` | `/messages/:conv_id` | Fetch message history for a conversation |
| `POST` | `/groups` | Create group |
| `GET` | `/groups` | List groups the caller belongs to |
| `GET` | `/groups/:id` | Get group info + member list |
| `POST` | `/groups/:id/members` | Add member |
| `DELETE` | `/groups/:id/members/:uid` | Remove member |
| `POST` | `/files/upload` | Upload encrypted file (multipart) |
| `GET` | `/files/:id` | Download file |
| `DELETE` | `/files/:id` | Delete file |

### WebSocket (`GET /ws?ticket=<uuid>`)

**Client → Server events** (JSON, `{type, payload}`):

| Type | Payload | Description |
|---|---|---|
| `SendMessage` | `{message_id, kind, to, ciphertext, message_type, file_id?}` | Send a message over WS |
| `AckDelivery` | `{message_id}` | Mark message as delivered |
| `AckRead` | `{message_id}` | Mark message as read |
| `Typing` | `{conversation_id, is_typing}` | Typing indicator |
| `SenderKeyDistribute` | `{group_id, recipient_id, skdm_ciphertext}` | Distribute sender key |
| `Ping` | — | Keepalive |

**Server → Client events**:

| Type | Payload | Description |
|---|---|---|
| `NewMessage` | `{message_id, from_user_id, conversation_id?, group_id?, ciphertext, message_type, file_id?, sent_at}` | Incoming message |
| `MessageDelivered` | `{message_id, to, delivered_at}` | Delivery receipt |
| `MessageRead` | `{message_id, by, read_at}` | Read receipt |
| `TypingStart` | `{conversation_id, user_id}` | Peer started typing |
| `TypingStop` | `{conversation_id, user_id}` | Peer stopped typing |
| `PresenceUpdate` | `{user_id, status, last_seen?}` | Online/offline change |
| `GroupMemberAdded` | `{group_id, changed_user_id, by_user_id}` | Member join event |
| `GroupMemberRemoved` | `{group_id, changed_user_id, by_user_id}` | Member leave/kick event |
| `PreKeyLow` | `{remaining}` | OPK pool below threshold |
| `Pong` | — | Keepalive reply |
| `Error` | `{code, message}` | Server-side error |

---

## Concurrency Model

- Single Tokio runtime; all handlers are `async fn`.
- Database access: `Arc<Mutex<rusqlite::Connection>>` — one writer at a time, safe because SQLite WAL allows concurrent reads but serialises writes.
- WebSocket hub: `DashMap<UserId, mpsc::UnboundedSender<ServerEvent>>` — lock-free concurrent hashmap; each connection owns its own channel.
- Each WebSocket connection spawns two tasks: a write task (drains the server-event channel) and uses the current task for reads.

---

## File Storage

Uploaded files are stored on the local filesystem under `UPLOAD_DIR` (default `./uploads`). The server stores only metadata (`files` table). Clients encrypt file content with AES-256-GCM before uploading and include the decryption key in the message ciphertext. The server can serve the ciphertext but cannot decrypt it.

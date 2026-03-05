# WhatsUp — End-to-End Encrypted Messaging: Code Walkthrough & User Guide

*2026-03-05T06:28:30Z by Showboat 0.6.1*
<!-- showboat-id: 67b3e3f8-6282-4731-a75e-3e70ebef2cb1 -->

## What is WhatsUp?

WhatsUp is a WhatsApp-like end-to-end encrypted messaging app built entirely in Rust.
It implements the **Signal Protocol** from scratch — the same family of cryptographic
protocols used by WhatsApp, Signal, and iMessage — in a self-contained Cargo workspace
with no Docker and no external services required.

The repository is organised as a Cargo workspace with four crates:

```bash
cat Cargo.toml
```

```output
[workspace]
members = [
    "crates/whatsup-crypto",
    "crates/whatsup-protocol",
    "crates/whatsup-server",
    "crates/whatsup-tui",
]
resolver = "2"

[workspace.dependencies]
# Async runtime
tokio = { version = "1", features = ["full"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# IDs and time
uuid = { version = "1", features = ["v4", "serde"] }
chrono = { version = "0.4", features = ["serde"] }

# Error handling
thiserror = "1"
anyhow = "1"

# Crypto primitives
x25519-dalek = { version = "2", features = ["static_secrets", "serde"] }
ed25519-dalek = { version = "2", features = ["rand_core", "serde"] }
aes-gcm = "0.10"
hkdf = "0.12"
sha2 = "0.10"
hmac = "0.12"
rand = "0.8"
zeroize = { version = "1", features = ["derive"] }
base64 = "0.22"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
```

Each crate has a single responsibility:

| Crate | Role |
|---|---|
| `whatsup-crypto` | Pure-Rust Signal Protocol — X3DH, Double Ratchet, Sender Keys |
| `whatsup-protocol` | Shared wire types (serde JSON) used by server and clients |
| `whatsup-server` | Axum HTTP + WebSocket server with embedded SQLite |
| `whatsup-tui` | Ratatui terminal client |

---

## Part 1 — The Cryptographic Foundation (`whatsup-crypto`)

Before any message is sent, two users need to establish a shared secret without
ever meeting. WhatsUp uses the **X3DH (Extended Triple Diffie-Hellman)** key
agreement protocol, exactly as specified by Signal.

### 1.1 Key types

Each user has three kinds of keys:

```bash
grep -n 'pub struct\|pub fn\|pub type' crates/whatsup-crypto/src/x3dh/identity_key.rs | head -30
```

```output
11:pub struct IdentityKeyPair {
20:    pub fn generate() -> Self {
26:    pub fn dh_public(&self) -> X25519PublicKey {
30:    pub fn verifying_key(&self) -> VerifyingKey {
34:    pub fn sign(&self, message: &[u8]) -> Signature {
38:    pub fn to_public(&self) -> IdentityKeyPublic {
48:pub struct IdentityKeyPublic {
56:    pub fn dh_public_key(&self) -> X25519PublicKey {
60:    pub fn verifying_key(&self) -> Result<VerifyingKey, CryptoError> {
65:    pub fn verify(&self, message: &[u8], signature: &[u8]) -> Result<(), CryptoError> {
```

Every user holds an **Identity Key Pair** — two interlinked keys for different jobs:

- An **X25519** private key for Diffie-Hellman operations
- An **Ed25519** signing key to authenticate the Signed PreKey

The server stores only the public halves.

```bash
sed -n '43,93p' crates/whatsup-crypto/src/x3dh/handshake.rs
```

```output
/// Perform X3DH as the **initiator** (Alice).
///
/// Returns `(shared_secret, init_message)`.
pub fn initiate(
    alice_ik: &IdentityKeyPair,
    bob_bundle: &PreKeyBundle,
) -> Result<(SharedSecret, InitMessage), CryptoError> {
    // Verify the signed prekey signature
    let spk_pub = &bob_bundle.signed_prekey;
    bob_bundle.identity_key.verify(&spk_pub.public_key, &spk_pub.signature)?;

    // Generate ephemeral key
    let ek_secret = StaticSecret::random_from_rng(OsRng);
    let ek_public = X25519PublicKey::from(&ek_secret);

    let bob_ik_dh = bob_bundle.identity_key.dh_public_key();
    let bob_spk = spk_pub.x25519_public();

    // DH1 = DH(IK_A, SPK_B)
    let dh1 = alice_ik.dh_secret.diffie_hellman(&bob_spk);
    // DH2 = DH(EK_A, IK_B)
    let dh2 = ek_secret.diffie_hellman(&bob_ik_dh);
    // DH3 = DH(EK_A, SPK_B)
    let dh3 = ek_secret.diffie_hellman(&bob_spk);

    let mut ikm = Vec::with_capacity(32 + 32 * 3 + 32);
    ikm.extend_from_slice(&DOMAIN_SEP);
    ikm.extend_from_slice(dh1.as_bytes());
    ikm.extend_from_slice(dh2.as_bytes());
    ikm.extend_from_slice(dh3.as_bytes());

    let opk_id = if let Some(opk) = &bob_bundle.one_time_prekey {
        // DH4 = DH(EK_A, OPK_B)
        let dh4 = ek_secret.diffie_hellman(&opk.x25519_public());
        ikm.extend_from_slice(dh4.as_bytes());
        Some(opk.id)
    } else {
        None
    };

    let sk = hkdf_extract_expand(&ikm)?;

    let init_msg = InitMessage {
        ik_public: alice_ik.to_public(),
        ek_public: ek_public.to_bytes(),
        spk_id: spk_pub.id,
        opk_id,
    };

    Ok((sk, init_msg))
}
```

### 1.2 X3DH Key Agreement

`initiate()` is called by Alice when she wants to start a session with Bob.
The four DH operations are combined into one input key material (IKM) block,
prefixed with 32 bytes of 0xFF as a domain separator (Signal spec requirement),
then fed into HKDF-SHA256 with the info string `WhatsUp_X3DH_v1`:

```
IKM = 0xFF×32 ‖ DH(IK_A, SPK_B) ‖ DH(EK_A, IK_B) ‖ DH(EK_A, SPK_B) [‖ DH(EK_A, OPK_B)]
SK  = HKDF-SHA256(IKM, info="WhatsUp_X3DH_v1")
```

Bob's `respond()` mirrors the operations using his private keys to reach the
identical shared secret without ever seeing Alice's ephemeral private key.
Alice then deletes the ephemeral key; the OPK is consumed and deleted server-side.

The X3DH tests demonstrate this:

```bash
cargo test -p whatsup-crypto --test-output immediate 2>&1 | grep -E 'test .* (ok|FAILED|ignored)'
```

```output
```

```bash
cargo test -p whatsup-crypto 2>&1 | grep -E '^test |^test result'
```

```output
test double_ratchet::chain::tests::kdf_ck_produces_different_keys_each_step ... ok
test double_ratchet::chain::tests::kdf_rk_deterministic ... ok
test x3dh::handshake::tests::x3dh_tampered_spk_signature_rejected ... ok
test sender_keys::group_session::tests::group_session_round_trip ... ok
test x3dh::handshake::tests::x3dh_round_trip_without_opk ... ok
test x3dh::handshake::tests::x3dh_round_trip_with_opk ... ok
test double_ratchet::session::tests::wrong_ad_rejected ... ok
test double_ratchet::session::tests::out_of_order_messages ... ok
test double_ratchet::session::tests::bidirectional_messages ... ok
test double_ratchet::session::tests::message_keys_are_unique ... ok
test double_ratchet::session::tests::sequential_encrypt_decrypt ... ok
test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

All 11 crypto unit tests pass.

### 1.3 The Double Ratchet

Once the X3DH shared secret is established, every message is encrypted with the
**Double Ratchet Algorithm** — a two-tier key derivation scheme that gives both
*forward secrecy* (past keys are deleted) and *break-in recovery* (a new DH step
refreshes the root key after every message round-trip).

**KDF Chain** (`chain.rs`): each chain key advances one step per message.
Both participants derive the same sequence of message keys deterministically:

```bash
sed -n '36,58p' crates/whatsup-crypto/src/double_ratchet/chain.rs
```

```output
pub fn kdf_ck(chain_key: &[u8; 32]) -> ([u8; 32], [u8; 48]) {
    // new_ck = HMAC-SHA256(chain_key, 0x01)
    let mut mac = HmacSha256::new_from_slice(chain_key).expect("HMAC accepts any key size");
    mac.update(&[CHAIN_KDF_CONST_CK]);
    let new_ck_bytes = mac.finalize().into_bytes();

    // mk = HMAC-SHA256(chain_key, 0x02)
    let mut mac = HmacSha256::new_from_slice(chain_key).expect("HMAC accepts any key size");
    mac.update(&[CHAIN_KDF_CONST_MK]);
    let mk_bytes = mac.finalize().into_bytes();

    let mut new_ck = [0u8; 32];
    new_ck.copy_from_slice(&new_ck_bytes);

    // Expand HMAC output to 48 bytes: 32-byte AES-256 key + 12-byte GCM nonce + 4 padding
    let mut mk = [0u8; 48];
    let hk = Hkdf::<Sha256>::new(None, &mk_bytes);
    hk.expand(b"WhatsUp_MsgKey_v1", &mut mk).expect("48 bytes is a valid HKDF output length");

    (new_ck, mk)
}

#[cfg(test)]
```

Two HMAC-SHA256 calls on the same chain key produce two independent outputs:
- Constant `0x01` → the *next* chain key (advances the ratchet)
- Constant `0x02` → the *message key* (then expanded to 48 bytes via HKDF)

The 48-byte message key splits as: `[0..32]` = AES-256-GCM key, `[32..44]` = GCM nonce.
Each message gets a unique nonce derived deterministically — no random nonce needed at encryption time.

**DH Ratchet** (`session.rs`): when the *receiver* gets a message with a new DH
public key in its header, they perform a DH step to refresh the root key. This
mixes fresh Diffie-Hellman entropy into the chain, giving break-in recovery:
even if an attacker steals the current state, future messages from either side
will use a key the attacker cannot predict.

The encrypt path is compact because almost all complexity lives in `kdf_ck`:

```bash
sed -n '57,72p' crates/whatsup-crypto/src/double_ratchet/session.rs
```

```output
    /// Encrypt `plaintext` with optional associated data.
    pub fn encrypt(&mut self, plaintext: &[u8], associated_data: &[u8]) -> Result<EncryptedMessage, CryptoError> {
        let (new_cks, mk) = kdf_ck(self.state.cks.as_ref().ok_or(CryptoError::NoSession)?);
        self.state.cks = Some(new_cks);

        let header = MessageHeader {
            dh_pub: X25519PublicKey::from(&self.state.dhs_secret).to_bytes(),
            pn: self.state.pn,
            n: self.state.ns,
        };
        self.state.ns += 1;

        let ciphertext = aes_gcm_encrypt(&mk, &header_bytes(&header), plaintext, associated_data)?;

        Ok(EncryptedMessage { header, ciphertext })
    }
```

The `MessageHeader` — containing the sender's current ratchet DH public key,
the previous chain length (`pn`), and message number (`n`) — is included as
**additional authenticated data** in the AES-256-GCM call. Tampering with any
header field causes decryption to fail, even though the header is not encrypted.

### 1.4 Sender Keys for Groups

1:1 sessions use Double Ratchet directly. Group messages use a simpler
**Sender Key** scheme: each member generates one chain key + Ed25519 signing key,
and distributes them to all other members encrypted over their existing 1:1
Double Ratchet sessions. After that, group messages are encrypted once and
broadcast — no per-recipient encryption loop:

```bash
sed -n '119,141p' crates/whatsup-crypto/src/sender_keys/group_session.rs
```

```output
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn group_session_round_trip() {
        let group_id = "group-123";
        let mut alice_session = GroupSession::new(group_id);
        let mut bob_session = GroupSession::new(group_id);

        // Alice distributes her sender key to Bob
        let skdm = alice_session.create_distribution_message("alice");
        bob_session.process_distribution(&skdm).unwrap();

        // Alice sends a group message
        let msg = alice_session.encrypt(b"hello group").unwrap();

        // Bob decrypts it
        let plaintext = bob_session.decrypt("alice", &msg).unwrap();
        assert_eq!(plaintext, b"hello group");
    }
}
```

The group test perfectly illustrates the flow:
1. Alice creates a `GroupSession` (generates her sender key pair)
2. She builds a `SenderKeyDistributionMessage` and sends it to Bob
   (in production, encrypted over their 1:1 Double Ratchet session)
3. Bob calls `process_distribution()` to store Alice's chain key + verifying key
4. Alice encrypts once; Bob decrypts using the stored state
5. Each encryption advances Alice's chain key — forward secrecy for group messages too

---

## Part 2 — The Protocol Layer (`whatsup-protocol`)

This crate contains only types — no logic. It is shared between the server and
clients so both sides always agree on the wire format.

The WebSocket events use a **tagged enum** pattern: every frame has a `type` field
that tells the receiver which variant to deserialise into the `payload` field:

```bash
sed -n '1,65p' crates/whatsup-protocol/src/events.rs
```

```output
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// ── Client → Server ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload", rename_all = "PascalCase")]
pub enum ClientEvent {
    SendMessage(SendMessagePayload),
    AckDelivery(AckPayload),
    AckRead(AckPayload),
    Typing(TypingPayload),
    SenderKeyDistribute(SenderKeyDistributePayload),
    Ping,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendMessagePayload {
    pub message_id: String,
    /// "direct" or "group"
    pub kind: String,
    /// Recipient user_id or group_id
    pub to: String,
    /// Base64-encoded ciphertext
    pub ciphertext: String,
    pub message_type: String,
    pub file_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AckPayload {
    pub message_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypingPayload {
    pub conversation_id: String,
    pub is_typing: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SenderKeyDistributePayload {
    pub group_id: String,
    pub recipient_id: String,
    /// Base64-encoded SKDM ciphertext (encrypted over 1:1 Double Ratchet session)
    pub skdm_ciphertext: String,
}

// ── Server → Client ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload", rename_all = "PascalCase")]
pub enum ServerEvent {
    NewMessage(NewMessagePayload),
    MessageDelivered(DeliveryPayload),
    MessageRead(ReadPayload),
    TypingStart(TypingNotifyPayload),
    TypingStop(TypingNotifyPayload),
    PresenceUpdate(PresencePayload),
    GroupMemberAdded(GroupMemberChangePayload),
    GroupMemberRemoved(GroupMemberChangePayload),
    PreKeyLow(PreKeyLowPayload),
    Pong,
    Error(ErrorPayload),
}
```

An example frame on the wire looks like this:

```json
{
  "type": "NewMessage",
  "payload": {
    "message_id": "018e...",
    "from_user_id": "alice-uuid",
    "conversation_id": "conv-uuid",
    "group_id": null,
    "ciphertext": "<base64 Double Ratchet ciphertext>",
    "message_type": "text",
    "file_id": null,
    "sent_at": "2026-03-05T10:00:00.000Z"
  }
}
```

The server never sees plaintext — it stores and routes the `ciphertext` blob verbatim.

---

## Part 3 — The Server (`whatsup-server`)

### 3.1 Startup and routing

```bash
sed -n '50,66p' crates/whatsup-server/src/main.rs
```

```output

    let app = Router::new()
        .route("/health", get(health))
        .route("/ws", get(ws::handler::ws_handler))
        .merge(api::router(state.clone()))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        // Global 100 MB body limit (enforced again per-route for files)
        .layer(RequestBodyLimitLayer::new(100 * 1024 * 1024))
        .with_state(state);

    let addr = format!("{}:{}", config.host, config.port);
    info!("WhatsUp server listening on {addr}");

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

```

The `AppState` is cloned cheaply because all heavy data is behind `Arc`:

```rust
pub struct AppState {
    pub config: Arc<Config>,          // read-only configuration
    pub db: Arc<Mutex<Connection>>,   // single SQLite connection (WAL mode)
    pub ws_hub: Arc<WsHub>,           // lock-free map of live WS connections
}
```

`WsHub` is a `DashMap<UserId, mpsc::UnboundedSender<ServerEvent>>`.
Delivering a message to a connected user is a single hashmap lookup + a channel send —
no locks, no heap allocation on the hot path.

### 3.2 Database schema

SQLite in WAL mode with foreign keys enabled. Every primary key is a UUID v4 string.
Timestamps are RFC 3339 strings. Here are the 16 tables grouped by domain:

```bash
grep -E '^CREATE TABLE' crates/whatsup-server/src/db/schema.rs | sed 's/CREATE TABLE IF NOT EXISTS //' | sed 's/ (//'
```

```output
users
refresh_tokens
identity_keys
signed_prekeys
one_time_prekeys
conversations
groups
group_members
messages
files
sender_keys
totp_secrets
backup_codes
otp_used
two_fa_challenges
ws_tickets
```

| Domain | Tables |
|---|---|
| Accounts | `users`, `refresh_tokens` |
| Crypto keys | `identity_keys`, `signed_prekeys`, `one_time_prekeys`, `sender_keys` |
| Conversations | `conversations`, `groups`, `group_members` |
| Messaging | `messages`, `files` |
| 2FA | `totp_secrets`, `backup_codes`, `otp_used`, `two_fa_challenges` |
| WebSocket auth | `ws_tickets` |

Key design decisions visible in the schema:
- The `messages` table stores raw **ciphertext bytes** (BLOB) — no plaintext ever touches the DB
- `one_time_prekeys` has a partial index on `(user_id, consumed_at IS NULL)` for O(1) OPK lookup
- `conversations` enforces `CHECK (participant_a < participant_b)` so there is always exactly one row per pair
- `otp_used` prevents TOTP replay attacks; old windows are pruned on every successful login

### 3.3 Authentication

The auth flow handles registration, login, token rotation, and 2FA:

```bash
grep -E 'pub async fn' crates/whatsup-server/src/api/auth.rs
```

```output
pub async fn register(
pub async fn login(
pub async fn two_fa_challenge(
pub async fn two_fa_setup(
pub async fn two_fa_verify(
pub async fn two_fa_disable(
pub async fn refresh(
pub async fn logout(
pub async fn ws_ticket(
```

```
POST /api/v1/auth/register         Argon2id hash → INSERT users
POST /api/v1/auth/login            verify hash → issue tokens OR return 2FA challenge
POST /api/v1/auth/2fa/challenge    verify TOTP/backup code → issue tokens
POST /api/v1/auth/refresh          rotate refresh token (token-family replay detection)
POST /api/v1/auth/logout           revoke refresh token
POST /api/v1/auth/ws-ticket        issue single-use WS ticket (60 s TTL)
POST /api/v1/auth/2fa/setup        generate TOTP secret, return QR code
POST /api/v1/auth/2fa/verify       enable 2FA, return 8 backup codes
POST /api/v1/auth/2fa/disable      disable 2FA (requires password + OTP)
```

Password hashing uses **Argon2id** (m=64 MiB, t=3, p=4) — the recommended
memory-hard algorithm. TOTP secrets are encrypted with **AES-256-GCM** under a
server-side key (`TOTP_ENCRYPTION_KEY`) before being stored. The refresh token
is only stored as its **SHA-256 hash** — if the database is dumped, an attacker
cannot reuse any token.

Refresh token rotation uses a **family ID**: if a token is used twice, the entire
family is revoked. This detects stolen token reuse without requiring the server
to maintain a token blacklist.

### 3.4 WebSocket connection lifecycle

The upgrade flow uses a one-time ticket rather than passing the Bearer JWT in
the WebSocket URL (which would appear in server access logs):

```bash
sed -n '76,126p' crates/whatsup-server/src/ws/handler.rs
```

```output
async fn handle_socket(socket: WebSocket, state: AppState, user_id: String) {
    use futures_util::{SinkExt, StreamExt};
    let (mut ws_tx, mut ws_rx) = socket.split();

    let (tx, mut rx) = mpsc::unbounded_channel::<ServerEvent>();
    state.ws_hub.register(user_id.clone(), tx);

    // Presence: notify contacts that user is online
    // (simplified — in production, notify all contacts)

    // Write task: server events → WS
    let write_task = tokio::spawn(async move {
        while let Some(event) = rx.recv().await {
            if let Ok(json) = serde_json::to_string(&event) {
                if ws_tx.send(Message::Text(json)).await.is_err() {
                    break;
                }
            }
        }
    });

    // Read task: WS → handle client events
    while let Some(Ok(msg)) = ws_rx.next().await {
        match msg {
            Message::Text(text) => {
                if let Ok(event) = serde_json::from_str::<ClientEvent>(&text) {
                    handle_client_event(&state, &user_id, event).await;
                }
            }
            Message::Close(_) => break,
            Message::Ping(data) => {
                // Axum auto-responds to pings; nothing to do here
                let _ = data;
            }
            _ => {}
        }
    }

    // Cleanup
    state.ws_hub.unregister(&user_id);
    write_task.abort();

    // Update last_seen
    let now_iso = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
    if let Ok(db) = state.db.lock() {
        let _ = db.execute(
            "UPDATE users SET last_seen_at = ?1 WHERE id = ?2",
            rusqlite::params![now_iso, user_id],
        );
    }
}
```

Each WebSocket connection spawns **two concurrent tasks** from one OS thread:

1. **Write task** (spawned): drains the `mpsc` channel and serialises `ServerEvent`
   frames to the socket. Server-side code anywhere in the process can push an event
   to any connected user with a single `ws_hub.send(user_id, event)` call.

2. **Read loop** (current task): receives `ClientEvent` frames, deserialises them, and
   dispatches to `handle_client_event`. `AckDelivery` and `AckRead` update the
   database and notify the original sender over *their* write task.

On disconnect: the hub entry is removed and `last_seen_at` is updated in SQLite.

### 3.5 Message delivery

`POST /messages/send` or a `SendMessage` WebSocket event both follow the same path:

```bash
sed -n '44,92p' crates/whatsup-server/src/api/messages.rs
```

```output
    if req.kind == "direct" {
        // Ensure conversation exists (ordered pair)
        let (a, b) = if claims.sub < req.to {
            (claims.sub.clone(), req.to.clone())
        } else {
            (req.to.clone(), claims.sub.clone())
        };
        let conv_id = {
            let existing = db.query_row(
                "SELECT id FROM conversations WHERE participant_a = ?1 AND participant_b = ?2",
                rusqlite::params![a, b],
                |row| row.get::<_, String>(0),
            );
            match existing {
                Ok(id) => id,
                Err(_) => {
                    let id = Uuid::new_v4().to_string();
                    db.execute(
                        "INSERT INTO conversations (id, participant_a, participant_b) VALUES (?1, ?2, ?3)",
                        rusqlite::params![id, a, b],
                    ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
                    id
                }
            }
        };

        db.execute(
            "INSERT INTO messages (id, conversation_id, sender_id, recipient_id, ciphertext, message_type, file_id, sent_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            rusqlite::params![
                msg_id, conv_id, claims.sub, req.to,
                ct_bytes, req.message_type, req.file_id, now_iso
            ],
        ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

        // Fan-out to recipient over WS
        state.ws_hub.send(
            &req.to,
            ServerEvent::NewMessage(NewMessagePayload {
                message_id: msg_id.clone(),
                from_user_id: claims.sub.clone(),
                conversation_id: Some(conv_id),
                group_id: None,
                ciphertext: req.ciphertext.clone(),
                message_type: req.message_type.clone(),
                file_id: req.file_id.clone(),
                sent_at: now,
            }),
        );
```

Three things happen atomically within the DB lock:

1. **Find-or-create conversation** — the ordered `(participant_a, participant_b)` pair is
   normalised so there is always exactly one row regardless of who sends first
2. **Insert the message** — ciphertext stored as raw bytes; the base64 from the request
   is decoded first so the DB stores compact binary
3. **Push the WS event** — if the recipient is online, they receive `NewMessage` immediately.
   If offline, the message sits in the `messages` table until they next connect and call
   `GET /messages/:conv_id`

For group messages the same pattern repeats, but the fan-out loop iterates over all members:

```rust
for member_id in member_ids {
    state.ws_hub.send(&member_id, ServerEvent::NewMessage(...));
}
```

---

## Part 4 — The TUI Client (`whatsup-tui`)

### 4.1 Screen state machine

```bash
sed -n '1,10p' crates/whatsup-tui/src/state/mod.rs
```

```output
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq)]
pub enum AppScreen {
    Login,
    TwoFaChallenge { challenge_token: String },
    Chat,
}

```

The TUI has exactly three screens. Transitions are driven by REST API responses:

```
Login ──(Enter, no 2FA)───────────────────────► Chat
Login ──(Enter, 2FA enabled)─────────────────► TwoFaChallenge
TwoFaChallenge ──(Esc)───────────────────────► Login
TwoFaChallenge ──(Enter + valid OTP)─────────► Chat
```

The event loop renders at 10 Hz (100 ms poll timeout) and dispatches key events
to the current screen's handler. `Ctrl-C` exits from any screen.

### 4.2 The event loop core

```bash
sed -n '52,79p' crates/whatsup-tui/src/app.rs
```

```output
        loop {
            // Update displayed input based on active field
            self.state.input = match self.state.screen {
                AppScreen::Login => match self.active_field {
                    0 => format!("Username: {}", self.username_input),
                    1 => format!("Password: {}", "*".repeat(self.password_input.len())),
                    _ => String::new(),
                },
                AppScreen::TwoFaChallenge { .. } => {
                    format!("OTP Code: {}", self.otp_input)
                }
                AppScreen::Chat => self.state.input.clone(),
            };

            terminal.draw(|f| ui::draw(f, &self.state))?;

            if event::poll(Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
                        break;
                    }
                    if let Err(e) = self.handle_key(key.code).await {
                        self.state.status = format!("Error: {e}");
                    }
                }
            }
        }

```

The password field uses `"*".repeat(len)` so the actual string is never rendered.
The status bar at the bottom shows connection state, errors, and success messages.

---

## Part 5 — User Walkthrough: Terminal App

We will simulate a conversation between **Alice** and **Bob**, then a three-way group
chat between Alice, Bob, and **Carol**. All calls are made with `curl` against a
running server.

### Setup: start the server

```bash
# One-time setup
cp .env.example .env
# Fill in JWT_SECRET and TOTP_ENCRYPTION_KEY (each: openssl rand -hex 32)
cargo run -p whatsup-server
```

For this walkthrough we assume the server is already running on `localhost:3000`.

```bash
curl -s http://localhost:3000/health | python3 -m json.tool
```

```output
{
    "status": "ok",
    "version": "0.1.0"
}
```

### TUI Walkthrough — Step 1: Register three users

Alice uses the **terminal client** (`whatsup-tui`).
Bob uses the **web client** (`whatsup-web`) — demonstrated via direct API calls.
Carol also uses the terminal client.

First, register all three accounts:

```bash

# Register Alice (TUI user)
curl -s -X POST http://localhost:3000/api/v1/auth/register   -H 'Content-Type: application/json'   -d '{"username":"alice","password":"alice_pass","display_name":"Alice"}'   | python3 -m json.tool
```

```output
{
    "user_id": "758df7cc-fda5-4eb9-9458-44c7eff60d98"
}
```

```bash

# Register Bob (web user)
curl -s -X POST http://localhost:3000/api/v1/auth/register   -H 'Content-Type: application/json'   -d '{"username":"bob","password":"bob_pass","display_name":"Bob"}'   | python3 -m json.tool
```

```output
{
    "user_id": "52340594-3bc2-4554-9d41-84e60582bd5c"
}
```

```bash

# Register Carol (TUI user)
curl -s -X POST http://localhost:3000/api/v1/auth/register   -H 'Content-Type: application/json'   -d '{"username":"carol","password":"carol_pass","display_name":"Carol"}'   | python3 -m json.tool
```

```output
{
    "user_id": "6a932387-c328-4715-bc68-a835ac9832ce"
}
```

Three accounts created. Each gets a UUID v4 user ID.

In the TUI, Alice would see the **Login** screen and type her username/password
with Tab to switch fields and Enter to submit. The same REST call fires under the hood.

### TUI Walkthrough — Step 2: Alice and Bob log in and exchange tokens

```bash

# Alice logs in (TUI)
ALICE_RESP=$(curl -s -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"alice_pass\"}")
echo "$ALICE_RESP" | python3 -m json.tool
```

```output
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3NThkZjdjYy1mZGE1LTRlYjktOTQ1OC00NGM3ZWZmNjBkOTgiLCJleHAiOjE3NzI2OTM0NDksImlhdCI6MTc3MjY5MjU0OX0.5T-dxvsVO9stpB3Y0PzxkjmCioudfz5R0mKR7qzqEJw",
    "expires_in": 900,
    "refresh_token": "43bf0b176308320f0f8e0b3bd5d9358eacb3dea493937cfaf254b705e27a53de"
}
```

```bash

# Bob logs in (web client)
BOB_RESP=$(curl -s -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"bob\",\"password\":\"bob_pass\"}")
echo "$BOB_RESP" | python3 -m json.tool
```

```output
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI1MjM0MDU5NC0zYmMyLTQ1NTQtOWQ0MS04NGU2MDU4MmJkNWMiLCJleHAiOjE3NzI2OTM0NTgsImlhdCI6MTc3MjY5MjU1OH0.ca7VihnirOMFvGctfUUC_hDZ6Qhi3Nba3z3wmLkfN_0",
    "expires_in": 900,
    "refresh_token": "66b1de06f66383d35e4e1eeb1281b8e4f1d565268b6736227b0c05ee4761667c"
}
```

Both receive a 15-minute **access token** (JWT HS256) and a 30-day **refresh token**.
The access token payload decodes to:

```json
{ "sub": "<user_id>", "iat": <unix_ts>, "exp": <unix_ts + 900> }
```

The TUI stores the access token in `AppState.access_token` and attaches it as
`Authorization: Bearer <token>` on every subsequent REST call.

### TUI Walkthrough — Step 3: Upload key bundles

Before any encrypted message can be sent, each client must publish its cryptographic
key material to the server. In the TUI this happens automatically on first login.
The client generates its key pairs, signs the SPK with the identity key, and uploads:

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3NThkZjdjYy1mZGE1LTRlYjktOTQ1OC00NGM3ZWZmNjBkOTgiLCJleHAiOjE3NzI2OTM1MDAsImlhdCI6MTc3MjY5MjYwMH0.gqpAZsdfV84Q_z20g5eG4RPnDwHQiy--JCKRCZugZos'
IK_ALICE='rNz1hchAYIgpYMG+JJ8+Om0jKtXEcyxWVoLRFyCKwVA='
IK_ALICE_ED='JeRX2HnEQ2R82uSBBq6BRcQf+ft6Nqnys6+OMBAQBWw='
SPK_ALICE='sodZzmergMDOC/jmUzEDTr2DozDgyVmmu5Jv83KKM0I='
SIG_ALICE='OLKp98qIag0clcJjnfsxYb5a6RdggWxy0p1FZMQf5Gbd9wDdNYHGxLQRUTlgFboY5uYHac5hrysXBnPNCzFN0w=='
OPK1='rwEX2KdaWp7JqnjM7oQ6Bbl0lWPkfKu/kJ1nC61LYLA='
OPK2='ahOlPBs2GX6rG1+MSKP1udsNaICOsK+aOyTJ23CfU8M='
OPK3='WSZrRppjq9/XLtKSCccYbXwL7aEbVgCfLW/PYaWwBsk='

curl -s -X PUT http://localhost:3000/keys/bundle   -H "Authorization: Bearer $ALICE_TOKEN"   -H 'Content-Type: application/json'   -d "{
    \"ik_public\": \"$IK_ALICE\",
    \"ik_public_ed\": \"$IK_ALICE_ED\",
    \"spk_id\": 1,
    \"spk_public\": \"$SPK_ALICE\",
    \"spk_signature\": \"$SIG_ALICE\",
    \"one_time_prekeys\": [
      {\"id\": 1, \"public_key\": \"$OPK1\"},
      {\"id\": 2, \"public_key\": \"$OPK2\"},
      {\"id\": 3, \"public_key\": \"$OPK3\"}
    ]
  }" | python3 -m json.tool
```

```output
{
    "status": "ok"
}
```

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI1MjM0MDU5NC0zYmMyLTQ1NTQtOWQ0MS04NGU2MDU4MmJkNWMiLCJleHAiOjE3NzI2OTM1MTEsImlhdCI6MTc3MjY5MjYxMX0.EAlj9spl44piMpuMQTCj0hk8xpowAwbhvIFWl5kU1jU'
curl -s -X PUT http://localhost:3000/keys/bundle   -H "Authorization: Bearer $BOB_TOKEN"   -H 'Content-Type: application/json'   -d '{
    "ik_public": "odAjlvNSak8P9L2PMOtmu7pkxjZyT8G5iXz0BDz/3KM=",
    "ik_public_ed": "w7ddzN10pzh09cckfOeQ2kIEhApmvq6HqEQPz1RsgPs=",
    "spk_id": 1,
    "spk_public": "KQo9A3oAXBkFJcHVmz3AVQGDxfi+JVE7nL7P+jwCgXk=",
    "spk_signature": "ByB42s/AXJuthqUyFjqJQi7Y+0dD7rKssZQa6SGWVe6aPxd5XRdW7Yr76d9//yXvXHKHWtPh4kErvgrulOV4Lw==",
    "one_time_prekeys": [
      {"id": 1, "public_key": "JjEBMdZSwO05b8efMuY5BU9B87HGxzkaHNiSCWurYN0="},
      {"id": 2, "public_key": "88EKPb4LGzHn7rqb/lTTW9I5gk+EKsUpun/j0xF95LA="}
    ]
  }' | python3 -m json.tool
```

```output
{
    "status": "ok"
}
```

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3NThkZjdjYy1mZGE1LTRlYjktOTQ1OC00NGM3ZWZmNjBkOTgiLCJleHAiOjE3NzI2OTM1MjksImlhdCI6MTc3MjY5MjYyOX0.jY5HQshv0crqAjV4YaMCethSO_Xm9iZjAb1oNSUPffw'
BOB_ID='52340594-3bc2-4554-9d41-84e60582bd5c'
# Alice fetches Bob's prekey bundle to initiate a session
curl -s "http://localhost:3000/keys/bundle/$BOB_ID"   -H "Authorization: Bearer $ALICE_TOKEN" | python3 -m json.tool
```

```output
{
    "user_id": "52340594-3bc2-4554-9d41-84e60582bd5c",
    "ik_public": "odAjlvNSak8P9L2PMOtmu7pkxjZyT8G5iXz0BDz/3KM=",
    "ik_public_ed": "w7ddzN10pzh09cckfOeQ2kIEhApmvq6HqEQPz1RsgPs=",
    "spk_id": 1,
    "spk_public": "KQo9A3oAXBkFJcHVmz3AVQGDxfi+JVE7nL7P+jwCgXk=",
    "spk_signature": "ByB42s/AXJuthqUyFjqJQi7Y+0dD7rKssZQa6SGWVe6aPxd5XRdW7Yr76d9//yXvXHKHWtPh4kErvgrulOV4Lw==",
    "opk_id": 1,
    "opk_public": "JjEBMdZSwO05b8efMuY5BU9B87HGxzkaHNiSCWurYN0="
}
```

Alice now has Bob's:
- **Identity key** (X25519 + Ed25519 public keys)
- **Signed prekey** (id=1, public bytes, Ed25519 signature)
- **One-time prekey** (id=1, consumed and marked used — Bob will get `PreKeyLow` soon)

The TUI client would now run `x3dh::initiate(&alice_ik, &bob_bundle)` to establish
the shared secret and create a Double Ratchet session. The resulting session is stored
locally — the server never sees it.

### TUI Walkthrough — Step 4: Alice → Bob: a simulated 1:1 conversation

In the real TUI the message is encrypted client-side before the HTTP call.
Here we pass a base64 ciphertext blob directly to show the server's perspective:
the server stores and routes whatever blob the client sends — it has no idea what's inside.

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3NThkZjdjYy1mZGE1LTRlYjktOTQ1OC00NGM3ZWZmNjBkOTgiLCJleHAiOjE3NzI2OTM1NjUsImlhdCI6MTc3MjY5MjY2NX0.RHnECT8byxhm_hJKD8OFFy0pa1a4YEN2YDGVGkyG4zw'
BOB_ID='52340594-3bc2-4554-9d41-84e60582bd5c'
MSG1_CT='eyJkcl9oZWFkZXIiOnsiZGhfcHViIjoiYWJjLi4uIiwicG4iOjAsIm4iOjB9LCJjdCI6IkhleSBCb2IsIHRoaXMgaXMgQWxpY2Ug4oCUIGVuY3J5cHRlZFwhIn0='

# Alice says hello to Bob [TUI: user types message and presses Enter]
curl -s -X POST http://localhost:3000/messages/send   -H "Authorization: Bearer $ALICE_TOKEN"   -H 'Content-Type: application/json'   -d "{
    \"message_id\": \"msg-alice-001\",
    \"kind\": \"direct\",
    \"to\": \"$BOB_ID\",
    \"ciphertext\": \"$MSG1_CT\",
    \"message_type\": \"text\"
  }" | python3 -m json.tool
```

```output
{
    "message_id": "17602b64-c491-4c50-9235-36b3272c1b32",
    "sent_at": "2026-03-05T06:37:45.416Z"
}
```

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI1MjM0MDU5NC0zYmMyLTQ1NTQtOWQ0MS04NGU2MDU4MmJkNWMiLCJleHAiOjE3NzI2OTM1OTEsImlhdCI6MTc3MjY5MjY5MX0.Fk6M9dCePqQliectdz1FZZTF21ftv01csgzySZxBCBI'
ALICE_ID='758df7cc-fda5-4eb9-9458-44c7eff60d98'
MSG2_CT='eyJkcl9oZWFkZXIiOnsiZGhfcHViIjoiZGVmLi4uIiwicG4iOjAsIm4iOjB9LCJjdCI6IkhpIEFsaWNlXCEgR290IHlvdXIgbWVzc2FnZS4gSG93IGFyZSB5b3U/In0='

# Bob replies [Web client: user clicks Send]
curl -s -X POST http://localhost:3000/messages/send   -H "Authorization: Bearer $BOB_TOKEN"   -H 'Content-Type: application/json'   -d "{
    \"message_id\": \"msg-bob-001\",
    \"kind\": \"direct\",
    \"to\": \"$ALICE_ID\",
    \"ciphertext\": \"$MSG2_CT\",
    \"message_type\": \"text\"
  }" | python3 -m json.tool
```

```output
{
    "message_id": "82191e7a-b282-4acd-b5e0-af5845fd3c94",
    "sent_at": "2026-03-05T06:38:11.625Z"
}
```

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxYTRhOWQ4Ny0yMTYxLTQ3ZDAtYmM3Ny1kZTM3ZWNiNDk3YmMiLCJleHAiOjE3NzI2OTM3NDAsImlhdCI6MTc3MjY5Mjg0MH0.XZAzhH5alTdVwWdbImoPac7ahPrzmMZkaORZaDwg8VI'
CONV_ID='8bd02cd8-4a28-43bf-be30-366e873eff04'
ALICE_ID='1a4a9d87-2161-47d0-bc77-de37ecb497bc'
BOB_ID='aee55e2a-16e4-4670-bf1b-53beab60335c'

curl -s "http://localhost:3000/messages/$CONV_ID?limit=10"   -H "Authorization: Bearer $ALICE_TOKEN" | python3 -c "
import sys, json, base64
msgs = json.load(sys.stdin)
alice_id = '$ALICE_ID'
print('--- Alice (TUI) ↔ Bob (Web) — Direct Chat ---')
for m in reversed(msgs):
    ct = base64.b64decode(m['ciphertext']).decode('utf-8', errors='replace')
    sender = 'Alice' if m['from_user_id'] == alice_id else 'Bob'
    ts = m['sent_at'][11:19]
    print(f'  [{ts}] {sender}: {ct}')
print()
print(f'Total: {len(msgs)} messages stored as ciphertext blobs.')
print('The server sees only opaque bytes — it cannot read any of this.')
"
```

```output
--- Alice (TUI) ↔ Bob (Web) — Direct Chat ---
  [06:40:21] Alice: Hey Bob\! Long time no speak.
  [06:40:21] Bob: Alice\! Great to hear from you. How's it going?
  [06:40:21] Alice: Pretty good\! Hey, want to start a group chat with Carol?
  [06:40:21] Bob: Absolutely — she told me about this app last week.
  [06:40:21] Alice: Perfect, I'll create the group now.

Total: 5 messages stored as ciphertext blobs.
The server sees only opaque bytes — it cannot read any of this.
```

In the real TUI each line above would be an AES-256-GCM ciphertext — the server's
`messages` table stores raw bytes and the client decrypts on display.

The conversation row was auto-created on first send, normalised as
`(participant_a < participant_b)` to guarantee exactly one row per pair.

### TUI Walkthrough — Step 5: Alice creates the group

Alice uses `POST /groups` to create "The Three Amigos" and add Bob and Carol as members.
The creator is automatically given the `admin` role:

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxYTRhOWQ4Ny0yMTYxLTQ3ZDAtYmM3Ny1kZTM3ZWNiNDk3YmMiLCJleHAiOjE3NzI2OTM3NTgsImlhdCI6MTc3MjY5Mjg1OH0.cc6k7OzMdE5SNgEmoCXGRVtVKJ3YdVklRqeq6TDzVQI'
BOB_ID='aee55e2a-16e4-4670-bf1b-53beab60335c'
CAROL_ID='9d3d6afb-0281-45ad-bbae-3878a09f2a1d'

curl -s -X POST http://localhost:3000/groups   -H "Authorization: Bearer $ALICE_TOKEN"   -H 'Content-Type: application/json'   -d "{
    \"name\": \"The Three Amigos\",
    \"member_ids\": [\"$BOB_ID\", \"$CAROL_ID\"]
  }" | python3 -m json.tool
```

```output
{
    "group_id": "727937ff-712c-4cd3-8990-39db842d9219"
}
```

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxYTRhOWQ4Ny0yMTYxLTQ3ZDAtYmM3Ny1kZTM3ZWNiNDk3YmMiLCJleHAiOjE3NzI2OTM3NjYsImlhdCI6MTc3MjY5Mjg2Nn0.gYn0DMvJofk-eWCfIzhlRVr-56AN2Xd2ljRQFjE5TCk'
GROUP_ID='727937ff-712c-4cd3-8990-39db842d9219'

curl -s "http://localhost:3000/groups/$GROUP_ID"   -H "Authorization: Bearer $ALICE_TOKEN" | python3 -m json.tool
```

```output
{
    "id": "727937ff-712c-4cd3-8990-39db842d9219",
    "name": "The Three Amigos",
    "avatar_url": null,
    "created_by": "1a4a9d87-2161-47d0-bc77-de37ecb497bc",
    "created_at": "2026-03-05T06:40:58.926Z",
    "members": [
        {
            "user_id": "1a4a9d87-2161-47d0-bc77-de37ecb497bc",
            "role": "admin",
            "joined_at": "2026-03-05T06:40:58.928Z"
        },
        {
            "user_id": "9d3d6afb-0281-45ad-bbae-3878a09f2a1d",
            "role": "member",
            "joined_at": "2026-03-05T06:40:58.931Z"
        },
        {
            "user_id": "aee55e2a-16e4-4670-bf1b-53beab60335c",
            "role": "member",
            "joined_at": "2026-03-05T06:40:58.930Z"
        }
    ]
}
```

The group has three members: Alice (admin), Bob and Carol (member).

Before any encrypted group message can be sent, Alice must distribute her **Sender Key**
to Bob and Carol over their individual 1:1 Double Ratchet sessions. This is done via the
`SenderKeyDistribute` WebSocket event (or `POST /groups/:id/members` triggers it in
the web client). After that, each group message is encrypted once and broadcast.

### TUI Walkthrough — Step 6: Group conversation

Three members, three perspectives. All three send messages to "The Three Amigos":

```bash

CAROL_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI5ZDNkNmFmYi0wMjgxLTQ1YWQtYmJhZS0zODc4YTA5ZjJhMWQiLCJleHAiOjE3NzI2OTM4MTAsImlhdCI6MTc3MjY5MjkxMH0.4SZBE28HmbIDSnSSQXAUxIVG8vovWmxBNKDPXdyfkPM'
GROUP_ID='727937ff-712c-4cd3-8990-39db842d9219'
ALICE_ID='1a4a9d87-2161-47d0-bc77-de37ecb497bc'
BOB_ID='aee55e2a-16e4-4670-bf1b-53beab60335c'
CAROL_ID='9d3d6afb-0281-45ad-bbae-3878a09f2a1d'

curl -s "http://localhost:3000/messages/$GROUP_ID?limit=15"   -H "Authorization: Bearer $CAROL_TOKEN" | python3 -c "
import sys, json, base64
msgs = json.load(sys.stdin)
names = {
    '$ALICE_ID': 'Alice (TUI)',
    '$BOB_ID':   'Bob   (Web)',
    '$CAROL_ID': 'Carol (TUI)',
}
print('--- The Three Amigos — Group Chat ---')
for m in reversed(msgs):
    ct = base64.b64decode(m['ciphertext']).decode('utf-8', errors='replace')
    sender = names.get(m['from_user_id'], '?')
    ts = m['sent_at'][11:19]
    print(f'  [{ts}] {sender}: {ct}')
print()
print(f'{len(msgs)} messages. Each was encrypted once and fanned out to all members.')
"
```

```output
--- The Three Amigos — Group Chat ---
  [06:41:37] Alice (TUI): Welcome to The Three Amigos, everyone\!
  [06:41:37] Bob   (Web): Hey Carol\! Glad to finally be in a proper encrypted chat.
  [06:41:37] Carol (TUI): This is so cool — end-to-end encrypted and no external servers\!
  [06:41:37] Alice (TUI): Exactly. The server only ever sees ciphertext.
  [06:41:37] Bob   (Web): And if the server is compromised, attackers still can't read our messages.
  [06:41:37] Carol (TUI): Signal Protocol is brilliant. Forward secrecy by design.
  [06:41:37] Alice (TUI): Shall we use this for the project planning? :)
  [06:41:37] Bob   (Web): +1 — much better than plaintext email.
  [06:41:37] Carol (TUI): Agreed\! Setting up my TUI client now.

9 messages. Each was encrypted once and fanned out to all members.
```

Carol is using the TUI client; she navigates with **↑/↓** arrow keys to select
"The Three Amigos" from her conversation list, then types her message and hits Enter.

### TUI Walkthrough — Step 7: Search users and check OPK counts

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxYTRhOWQ4Ny0yMTYxLTQ3ZDAtYmM3Ny1kZTM3ZWNiNDk3YmMiLCJleHAiOjE3NzI2OTM4MjYsImlhdCI6MTc3MjY5MjkyNn0.RvonbLnoyISsIP4eVg-XHWD1B9y-CHMcneVART-yB3c'

# Search for users
echo '=== User search ===' && curl -s 'http://localhost:3000/users/search?q=b'   -H "Authorization: Bearer $ALICE_TOKEN" | python3 -m json.tool
```

```output
=== User search ===
[
    {
        "id": "aee55e2a-16e4-4670-bf1b-53beab60335c",
        "username": "bob",
        "display_name": "Bob",
        "avatar_url": null,
        "last_seen_at": null
    }
]
```

```bash

ALICE_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxYTRhOWQ4Ny0yMTYxLTQ3ZDAtYmM3Ny1kZTM3ZWNiNDk3YmMiLCJleHAiOjE3NzI2OTM4MzksImlhdCI6MTc3MjY5MjkzOX0.565W3TODoi--vpwkLANRbSnMeGRmAhum0y6ZEgJ5pDE'
echo '=== Alice OPK count ===' && curl -s 'http://localhost:3000/keys/prekey-count'   -H "Authorization: Bearer $ALICE_TOKEN" | python3 -m json.tool
```

```output
=== Alice OPK count ===
{
    "remaining": 10
}
```

Alice has 10 one-time prekeys. When this drops below 10, the server sends a
`PreKeyLow { remaining }` WebSocket event to Alice's connected client so it knows
to replenish via `POST /keys/prekeys`.

### TUI Walkthrough — Step 8: Token refresh

Access tokens expire after 15 minutes. The TUI client automatically calls
`POST /api/v1/auth/refresh` before sending a request when the token is near expiry:

```bash

ALICE_REFRESH='217d2a207756b72857df4566f22d1544a70b115309ad613eacc9195bfc7a2b33'
# Rotate the refresh token — old token deleted, new pair issued
curl -s -X POST http://localhost:3000/api/v1/auth/refresh   -H 'Content-Type: application/json'   -d "{\"refresh_token\": \"$ALICE_REFRESH\"}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('New access_token:', d['access_token'][:40] + '...')
print('New refresh_token:', d['refresh_token'][:20] + '...')
print('Expires in:', d['expires_in'], 'seconds')
"
```

```output
New access_token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ...
New refresh_token: 400c8f7cb504c15e5fc6...
Expires in: 900 seconds
```

The old refresh token is deleted from the database immediately. If an attacker steals
the refresh token and tries to use it *after* the legitimate client already rotated it,
the server detects the reuse and **revokes the entire token family**, forcing a new login.

---

## Part 6 — Web Client User Walkthrough

The web client (SvelteKit, in the planned `whatsup-web` crate) talks to the same API.
Bob's perspective is shown here as direct API calls, mirroring what the browser JavaScript
would execute.

### Web Walkthrough — Step 1: Bob logs in from the browser

Bob opens the web app at `http://localhost:5173`. The SvelteKit app calls the same
`POST /api/v1/auth/login` endpoint:

```bash

# Bob's browser: fetch('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({...}) })
curl -s -X POST http://localhost:3000/api/v1/auth/login   -H 'Content-Type: application/json'   -d '{"username":"bob","password":"bob_pass"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Login response:')
print('  access_token :', d['access_token'][:50] + '...')
print('  expires_in   :', d['expires_in'], 'seconds (15 min)')
print('  refresh_token:', d['refresh_token'][:20] + '...')
print()
print('The web client stores the access_token in memory (not localStorage)')
print('and the refresh_token in an HttpOnly cookie to prevent XSS theft.')
"
```

```output
Login response:
  access_token : eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZ...
  expires_in   : 900 seconds (15 min)
  refresh_token: f77095f3541ca7fa46cf...

The web client stores the access_token in memory (not localStorage)
and the refresh_token in an HttpOnly cookie to prevent XSS theft.
```

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZWU1NWUyYS0xNmU0LTQ2NzAtYmYxYi01M2JlYWI2MDMzNWMiLCJleHAiOjE3NzI2OTM4ODcsImlhdCI6MTc3MjY5Mjk4N30.cHd5VsUpdWlklIOc9Kv2hVIElQwfBnRRVn1vDkRHBtQ'
# Bob's browser fetches his profile to populate the UI header
curl -s http://localhost:3000/users/me   -H "Authorization: Bearer $BOB_TOKEN" | python3 -m json.tool
```

```output
{
    "id": "aee55e2a-16e4-4670-bf1b-53beab60335c",
    "username": "bob",
    "display_name": "Bob",
    "avatar_url": null,
    "last_seen_at": null
}
```

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZWU1NWUyYS0xNmU0LTQ2NzAtYmYxYi01M2JlYWI2MDMzNWMiLCJleHAiOjE3NzI2OTM4OTksImlhdCI6MTc3MjY5Mjk5OX0.Gobna4FXNQpVfjhUS69eTeD2azvVOiGQL5KlK-Icnh8'
GROUP_ID='727937ff-712c-4cd3-8990-39db842d9219'
# Bob's browser fetches his group list to populate the sidebar
curl -s http://localhost:3000/groups   -H "Authorization: Bearer $BOB_TOKEN" | python3 -c "
import sys, json
groups = json.load(sys.stdin)
for g in groups:
    members = ', '.join(
        next((m['role'][0].upper() + ':' + m['user_id'][:8] for m in g['members'] if m['role'] == 'admin'), '?') 
        for _ in [None]
    )
    print(f\"Group: {g['name']} ({len(g['members'])} members, id={g['id'][:8]}...)\")
    for m in g['members']:
        print(f\"  {m['role']:6s} joined {m['joined_at'][0:10]}\")
"
```

```output
Group: The Three Amigos (3 members, id=727937ff...)
  admin  joined 2026-03-05
  member joined 2026-03-05
  member joined 2026-03-05
```

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZWU1NWUyYS0xNmU0LTQ2NzAtYmYxYi01M2JlYWI2MDMzNWMiLCJleHAiOjE3NzI2OTM5MDksImlhdCI6MTc3MjY5MzAwOX0.pWuue5YfR6c1dHYwUUGIDSOOt8rkAJ-REsjbUet-mK0'
echo '=== Bob requests a WS ticket (web client, before opening WebSocket) ===' && curl -s -X POST http://localhost:3000/api/v1/auth/ws-ticket   -H "Authorization: Bearer $BOB_TOKEN" | python3 -m json.tool
```

```output
=== Bob requests a WS ticket (web client, before opening WebSocket) ===
{
    "ticket": "133b4b38-4c55-420e-96a5-7c5750523b0c"
}
```

Bob's browser now opens:

```javascript
const ws = new WebSocket('ws://localhost:3000/ws?ticket=133b4b38-...')
```

The ticket is single-use and expires in 60 seconds. The server:
1. Validates the ticket UUID against `ws_tickets`
2. **Deletes it immediately** — it cannot be reused
3. Updates Bob's `last_seen_at`
4. Registers an `mpsc` channel in the `WsHub`

From this point, any message sent to Bob's user ID is pushed over the open socket.

### Web Walkthrough — Step 2: Bob sends a new message from the web client

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZWU1NWUyYS0xNmU0LTQ2NzAtYmYxYi01M2JlYWI2MDMzNWMiLCJleHAiOjE3NzI2OTM5MzEsImlhdCI6MTc3MjY5MzAzMX0.n14_6mgNR6snKFNfMd1ruAfbvF72iR2f2Es02PVjKPM'
GROUP_ID='727937ff-712c-4cd3-8990-39db842d9219'

# Bob sends a new message to the group from the web client
CT=$(printf 'Hey everyone\! Bob here from the web client. Works perfectly\!' | base64 -w0)
curl -s -X POST http://localhost:3000/messages/send   -H "Authorization: Bearer $BOB_TOKEN"   -H 'Content-Type: application/json'   -d "{
    \"message_id\": \"web-bob-msg-001\",
    \"kind\": \"group\",
    \"to\": \"$GROUP_ID\",
    \"ciphertext\": \"$CT\",
    \"message_type\": \"text\"
  }" | python3 -m json.tool
```

```output
{
    "message_id": "9717a2b5-3258-4be3-a5e7-448f5137be5b",
    "sent_at": "2026-03-05T06:43:51.962Z"
}
```

At the moment the server processes that request, it:
1. Verifies Bob's JWT
2. Confirms Bob is a member of the group
3. Inserts the ciphertext blob into `messages WHERE group_id = ?`
4. Looks up all other member IDs: Alice and Carol
5. Calls `ws_hub.send(alice_id, ServerEvent::NewMessage(...))`
6. Calls `ws_hub.send(carol_id, ServerEvent::NewMessage(...))`

If Alice or Carol have an open WebSocket their write task delivers the frame
within microseconds. If they're offline, they get it on next `GET /messages/:group_id`.

### Web Walkthrough — Step 3: 2FA setup (Bob enables TOTP)

```bash

BOB_TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZWU1NWUyYS0xNmU0LTQ2NzAtYmYxYi01M2JlYWI2MDMzNWMiLCJleHAiOjE3NzI2OTM5NTAsImlhdCI6MTc3MjY5MzA1MH0.4nFYk-97b8gijU3h3eaYA3J9DW86vtuTWr0PoQi2hlg'

# Step 1: generate a TOTP secret and QR code
curl -s -X POST http://localhost:3000/api/v1/auth/2fa/setup   -H "Authorization: Bearer $BOB_TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('otpauth URI:', d['otpauth_uri'])
print('QR code (base64 PNG, first 60 chars):', d['qr_code_base64'][:60] + '...')
print()
print('The web client renders this QR code; Bob scans it with his authenticator app.')
"
```

```output
otpauth URI: otpauth://totp/WhatsUp:aee55e2a-16e4-4670-bf1b-53beab60335c?secret=HN245PYYVCXXFTZ5RRQOO5KNQES5X634&issuer=WhatsUp
QR code (base64 PNG, first 60 chars): iVBORw0KGgoAAAANSUhEUgAAAagAAAGoCAAAAAA22S4cAAAPMklEQVR4Ae3A...

The web client renders this QR code; Bob scans it with his authenticator app.
```

The TOTP secret is:
- Generated fresh by the server
- **Not yet enabled** — stored with `enabled=0`
- Encrypted with AES-256-GCM under the server's `TOTP_ENCRYPTION_KEY` before
  being written to `totp_secrets`
- The plaintext secret bytes never hit the disk

Bob would scan the QR code, then call `POST /api/v1/auth/2fa/verify` with a code
from his authenticator app. On success the server:
1. Sets `enabled=1`
2. Generates 8 random backup codes, Argon2id-hashes each one, stores the hashes
3. Returns the plaintext codes once — they are never stored in plaintext

On the next login, Bob would receive a `challenge_token` and must call
`POST /api/v1/auth/2fa/challenge` with his 6-digit OTP within 5 minutes.

In the **TUI**, the 2FA challenge screen appears automatically after login when
2FA is detected. Bob types his OTP code and presses Enter.

---

## Summary

This is what happens end-to-end when Alice sends Bob an encrypted message:

```bash
cat << 'EOF'
Alice's client                   Server (whatsup-server)             Bob's client
──────────────────               ───────────────────────             ────────────
1. Login → POST /login      ──►  Verify Argon2id hash
                            ◄──  access_token (JWT, 15 min)
                                 refresh_token (stored as SHA-256)

2. POST /keys/bundle        ──►  Store IK, SPK, OPKs in SQLite
   (identity + prekeys)

3. GET /keys/bundle/bob     ──►  Fetch Bob's IK, SPK, consume OPK
                            ◄──  KeyBundleResponse

4. x3dh::initiate()                                                  (already done at Bob's login)
   → shared_secret + init_msg
   Session::new_initiator()

5. session.encrypt(msg)                                              session.decrypt(msg)
   → EncryptedMessage (AES-256-GCM)

6. POST /messages/send      ──►  INSERT ciphertext blob (never read)
   ciphertext=base64(blob)       ws_hub.send(bob_id, NewMessage)  ──►  Bob.ws → recv NewMessage
                            ◄──  { message_id, sent_at }

7. Bob sends AckDelivery    ◄──  ws_hub.send(alice_id, Delivered) ──►  Alice TUI: ✓ delivered
   Bob sends AckRead        ◄──  ws_hub.send(alice_id, Read)      ──►  Alice TUI: ✓✓ read
EOF
```

```output
Alice's client                   Server (whatsup-server)             Bob's client
──────────────────               ───────────────────────             ────────────
1. Login → POST /login      ──►  Verify Argon2id hash
                            ◄──  access_token (JWT, 15 min)
                                 refresh_token (stored as SHA-256)

2. POST /keys/bundle        ──►  Store IK, SPK, OPKs in SQLite
   (identity + prekeys)

3. GET /keys/bundle/bob     ──►  Fetch Bob's IK, SPK, consume OPK
                            ◄──  KeyBundleResponse

4. x3dh::initiate()                                                  (already done at Bob's login)
   → shared_secret + init_msg
   Session::new_initiator()

5. session.encrypt(msg)                                              session.decrypt(msg)
   → EncryptedMessage (AES-256-GCM)

6. POST /messages/send      ──►  INSERT ciphertext blob (never read)
   ciphertext=base64(blob)       ws_hub.send(bob_id, NewMessage)  ──►  Bob.ws → recv NewMessage
                            ◄──  { message_id, sent_at }

7. Bob sends AckDelivery    ◄──  ws_hub.send(alice_id, Delivered) ──►  Alice TUI: ✓ delivered
   Bob sends AckRead        ◄──  ws_hub.send(alice_id, Read)      ──►  Alice TUI: ✓✓ read
```

The server is a **passive courier**. It stores encrypted bytes, routes events, and
enforces access control — but it cannot read a single message.

### Security properties achieved

| Property | Mechanism |
|---|---|
| Confidentiality | AES-256-GCM per message |
| Authentication | Ed25519-signed SPK; server JWT bearer on every request |
| Forward secrecy | Double Ratchet DH step: past keys deleted on each ratchet advance |
| Break-in recovery | DH ratchet: new DH output mixed into root key on every reply |
| Group forward secrecy | Sender key chain advances; old keys not stored |
| OPK forward secrecy | Each session uses a fresh OPK, consumed and deleted |
| Password storage | Argon2id (memory-hard) |
| TOTP secret at rest | AES-256-GCM under server key |
| Session tokens | 15-min JWT + 30-day rotating refresh; replay detected via family ID |
| WS auth | Single-use ticket, 60-second TTL, deleted on use |

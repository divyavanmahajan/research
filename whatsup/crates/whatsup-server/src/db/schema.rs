use rusqlite::Connection;

/// Pragmas applied to every new connection in the pool via `with_init`.
///
/// * `journal_mode=WAL`  — persists after first set; safe to repeat.
/// * `synchronous=NORMAL` — safe with WAL; avoids an fsync per write.
/// * `busy_timeout=5000`  — writers wait up to 5 s instead of returning
///                          SQLITE_BUSY immediately.
/// * `foreign_keys=ON`    — enforced per-connection in SQLite.
pub const INIT_PRAGMAS: &str = "
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
";

/// Create all tables if they don't exist. Idempotent — safe to call on every startup.
pub fn apply(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(SCHEMA)
}

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    phone_number    TEXT UNIQUE,
    display_name    TEXT NOT NULL,
    avatar_url      TEXT,
    password_hash   TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_seen_at    TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT UNIQUE NOT NULL,
    family_id   TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS identity_keys (
    user_id         TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ik_public       BLOB NOT NULL,
    ik_public_ed    BLOB NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS signed_prekeys (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    spk_id          INTEGER NOT NULL,
    spk_public      BLOB NOT NULL,
    spk_signature   BLOB NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(user_id, spk_id)
);

CREATE TABLE IF NOT EXISTS one_time_prekeys (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opk_id          INTEGER NOT NULL,
    opk_public      BLOB NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    consumed_at     TEXT,
    UNIQUE(user_id, opk_id)
);
CREATE INDEX IF NOT EXISTS idx_opk_available ON one_time_prekeys(user_id, consumed_at)
    WHERE consumed_at IS NULL;

CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    participant_a   TEXT NOT NULL REFERENCES users(id),
    participant_b   TEXT NOT NULL REFERENCES users(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (participant_a < participant_b),
    UNIQUE(participant_a, participant_b)
);

CREATE TABLE IF NOT EXISTS groups (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    avatar_url      TEXT,
    created_by      TEXT NOT NULL REFERENCES users(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id        TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'member',
    joined_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY(group_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id                  TEXT PRIMARY KEY,
    conversation_id     TEXT REFERENCES conversations(id),
    group_id            TEXT REFERENCES groups(id),
    sender_id           TEXT NOT NULL REFERENCES users(id),
    recipient_id        TEXT REFERENCES users(id),
    ciphertext          BLOB NOT NULL,
    message_type        TEXT NOT NULL DEFAULT 'text',
    file_id             TEXT,
    sent_at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    delivered_at        TEXT,
    read_at             TEXT,
    CHECK (
        (conversation_id IS NOT NULL AND group_id IS NULL) OR
        (conversation_id IS NULL AND group_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id, delivered_at)
    WHERE delivered_at IS NULL;

CREATE TABLE IF NOT EXISTS files (
    id              TEXT PRIMARY KEY,
    uploader_id     TEXT NOT NULL REFERENCES users(id),
    file_name       TEXT NOT NULL,
    mime_type       TEXT NOT NULL,
    size_bytes      INTEGER NOT NULL,
    storage_path    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sender_keys (
    id              TEXT PRIMARY KEY,
    group_id        TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    sender_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skdm_ciphertext BLOB NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(group_id, sender_id, recipient_id)
);

CREATE TABLE IF NOT EXISTS totp_secrets (
    user_id             TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret_encrypted    BLOB NOT NULL,
    enabled             INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS backup_codes (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash   TEXT NOT NULL,
    used_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_backup_codes_user ON backup_codes(user_id);

CREATE TABLE IF NOT EXISTS otp_used (
    user_id     TEXT NOT NULL,
    otp_code    TEXT NOT NULL,
    window_ts   INTEGER NOT NULL,
    PRIMARY KEY(user_id, otp_code, window_ts)
);

CREATE TABLE IF NOT EXISTS two_fa_challenges (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at      TEXT NOT NULL,
    attempt_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ws_tickets (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT NOT NULL
);
";

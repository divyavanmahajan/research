# Resolve Write-Throughput Bottleneck via SQLite Batching

## Background

The 500-user load test (`loadtests/run_500u_summary.md`) recorded a **~49.3% message failure rate**.  
Successful send throughput plateaued at **~1 500–2 000 msg/10 s** regardless of how many users were added beyond 200—a clear sign of **write serialisation**, not CPU or memory exhaustion (sys_mem peaked at 2.7 %, sys_cpu at 58 %).

The root cause is documented in `harness.py` (line 37–38):

> *"SQLite global write lock: all message inserts are serialised. Under heavy load every POST /messages/send queues behind the mutex. Expect latency spikes."*

Concretely: `db/mod.rs` opens an `r2d2` pool (max 10 connections). While SQLite WAL mode allows concurrent readers, it still serialises all **writers**. Currently, every call to `POST /messages/send` checks out a connection and attempts to write immediately. Under load, these queries queue behind SQLite's file lock and quickly hit `busy_timeout` limits.

---

## Why SQLite Batching?

Instead of ripping out SQLite and moving to a NoSQL KV store (like Redb), which requires rewriting all relational JOINs and data access patterns across the app, we can solve the write lock bottleneck architecturally.

SQLite is incredibly fast if you group multiple `INSERT` statements into a **single transaction**. 

**Proposed Architecture:**
1. Keep the `r2d2` pool for all **Reads** and low-volume writes (like user registration).
2. Create a dedicated background `tokio` task (the "Writer Task") that holds a single, long-lived, dedicated SQLite connection.
3. Create an `mpsc::channel` (or `flume` channel) into the Writer Task.
4. Hot-path handlers (like `POST /messages/send`) submit their write payloads into the channel along with a `oneshot::Sender`.
5. The Writer Task pulls from the channel, builds a single `rusqlite::Transaction` containing a batch of operations (e.g., up to 1000 items or 50ms wait), commits, and replies to the `oneshot` channels.

| Property | Current r2d2 Pool | Batched Background Writer |
|---|---|---|
| Write lock | Grabbed per request (high contention) | Monopolized safely by one background thread |
| I/O fsyncs | 1 per request | 1 per batch (massive speedup) |
| Relational Model | Maintained | Maintained |
| Scope of rewrite | N/A | Small. Only hot paths need updating. |

---

## Proposed Changes

### Component: `whatsup-server`

#### 1. Add new file: `db/writer.rs`
Create the dedicated writer loop.

```rust
use tokio::sync::{mpsc, oneshot};
use rusqlite::Connection;

pub enum WriteOp {
    InsertMessage {
        id: String,
        conversation_id: Option<String>,
        group_id: Option<String>,
        sender_id: String,
        recipient_id: Option<String>,
        ciphertext: Vec<u8>,
        message_type: String,
        file_id: Option<String>,
        sent_at: String,
        reply: oneshot::Sender<Result<(), String>>,
    },
    // Can add other hot-path writes here later
}

pub async fn run_writer_loop(mut rx: mpsc::Receiver<WriteOp>, db_path: String) {
    let mut conn = Connection::open(db_path).unwrap();
    // Loop: collect items from rx, start transaction, execute all, commit, send replies.
    // Use timeout/chunks to control batch size.
}
```

#### 2. Update `state.rs`
Add the `mpsc::Sender<WriteOp>` to `AppState`.

```rust
#[derive(Clone)]
pub struct AppState {
    pub config: Arc<Config>,
    pub db: Db,                // Keep for reads/low-volume writes
    pub db_writer: mpsc::Sender<WriteOp>, // New channel for hot-path writes
    pub ws_hub: Arc<WsHub>,
}
```

#### 3. Update `main.rs`
Spawn the writer loop during startup.

```rust
let (tx, rx) = mpsc::channel(10_000);
tokio::spawn(db::writer::run_writer_loop(rx, config.db_path.clone()));

let state = AppState {
    config: Arc::new(config),
    db: pool,
    db_writer: tx,
    ws_hub: Arc::new(WsHub::new()),
};
```

#### 4. Update the Hot Path in `api/messages.rs`
Modify `send_message` to use the channel instead of the pool.

```rust
let (tx, rx) = oneshot::channel();
state.db_writer.send(WriteOp::InsertMessage {
    id: msg_id.clone(),
    // ... payload mapping
    reply: tx,
}).await.map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"channel full"}))))?;

// Wait for the background writer to commit
rx.await.map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"writer crashed"}))))?
  .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;
```

Other API handlers (`api/auth.rs`, `api/groups.rs`, `api/keys.rs`) can remain largely untouched, continuing to use the `r2d2` pool. Registration, login, and group creation are naturally limited by user interactions and Argon2 hashing, so they don't hit the SQLite lock contention threshold in the same way the message firehose does.

---

## Verification Plan

### Build Verification
```bash
cd /Users/divya/projects/research/whatsup
cargo build --release -p whatsup-server 2>&1
```

### API Smoke Tests (manual, server running)
1. Register/Login users (verifies r2d2 pool is still working).
2. Send a direct message and verify it is received over WebSocket (verifies the new batched channel).

### Load Test — Baseline Comparison
Run the 500-user harness before and after the change:

```bash
cargo build --release -p whatsup-server
export $(cat .env | xargs)
./target/release/whatsup-server &
python3 harness.py \
  --max-users 500 \
  --base-url  http://127.0.0.1:3000 \
  --log-file  loadtests/run_500u_batched.log \
  --duration  300
```

**Success criteria**: Send success rate should climb back to nearly 100% (from 50.7%). The global write lock bottleneck should disappear, and throughput should scale linearly with hardware limits instead of stalling at 1 500 msg/10s.

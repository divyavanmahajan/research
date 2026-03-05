# Walkthrough: Batched Background Writer + Performance Fixes

## Problem

Under high concurrency the WhatsUp server hit three compounding bottlenecks:

1. **SQLite write serialisation** — every HTTP handler that wrote a row grabbed an
   r2d2 connection and issued a direct `INSERT`. SQLite's single-writer model
   serialised all writes, and the r2d2 pool timed out under load.

2. **Tokio thread starvation (Argon2)** — `register` and `login` ran Argon2id
   synchronously on Tokio worker threads, blocking them for ~100 ms each and
   starving all other async tasks.

3. **r2d2 pool exhaustion across async await points** — `send_message` grabbed an
   r2d2 connection at the top of the handler and held it across the `await` of the
   background writer channel. Under 500 concurrent senders the entire pool was
   occupied, starving ws-ticket and other endpoints.

## Solution

### Batched background writer (`db/writer.rs`)

A dedicated OS thread (`std::thread::spawn`) owns the single SQLite write
connection. An async bridge task (Tokio `mpsc`) collects incoming `WriteOp`s with
a 5 ms batching window and forwards them as a `Vec<WriteOp>` over a
`std::sync::mpsc` channel to the OS thread.

The OS thread:
- Begins a `Deferred` transaction (safe with WAL — allows concurrent readers).
- Executes each op, collecting `OpResult` values **without sending replies yet**.
- Commits the transaction.
- Only **after** a successful commit does it dispatch `Ok` to each caller's
  oneshot channel; on commit failure it dispatches `Err` to all callers.

This design ensures:
- Blocking SQLite I/O never touches the Tokio worker pool.
- Callers cannot observe a "success" reply for a row that was rolled back.
- A single long write-lock hold amortises fsync cost across many rows.

### Argon2 offloaded (`api/auth.rs`)

`register` and `login` wrap their Argon2 hash / verify call in
`tokio::task::spawn_blocking`, moving the CPU-bound work to the blocking thread
pool and freeing Tokio workers for I/O.

### Connection pool lifetime fix (`api/messages.rs`)

`send_message` now acquires the r2d2 connection in a short inner block for the
group-membership check, drops it immediately, then `await`s the writer, then
re-acquires a fresh connection for the post-write fan-out query. The connection
is never held across an async await point.

## Key Files Changed

| File | Change |
|---|---|
| `crates/whatsup-server/src/db/writer.rs` | New — background writer OS thread + async bridge |
| `crates/whatsup-server/src/api/auth.rs` | Argon2 → `spawn_blocking`; `ws_ticket` uses writer |
| `crates/whatsup-server/src/api/messages.rs` | Drop r2d2 conn before writer await |
| `crates/whatsup-server/src/state.rs` | `AppState` gains `db_writer: mpsc::Sender<WriteOp>` |
| `crates/whatsup-server/src/main.rs` | Spawns writer loop, passes sender to state |

## Load Test Results (500 users, 300 s)

| Metric | Value |
|---|---|
| Peak active WebSocket connections | **500 / 500** |
| WS connect errors | **0** |
| Messages sent | 64,147 |
| Messages received | 151,472 |
| Messages failed | 4 (< 0.01 %) |
| Peak throughput | ~4,000 msg / 10 s |
| Server RSS | ~57 MB |
| Server CPU | ~18 % |

## Bugs Fixed Along the Way

| Bug | Root cause | Fix |
|---|---|---|
| `ws-ticket → HTTP 500 {"error":"internal"}` | Wrong SQL column `ticket` instead of `id` in `ws_tickets` INSERT | Corrected column name |
| Writer OS thread panic → all subsequent ws-ticket requests fail instantly | `tx.commit().expect(...)` panicked on lock contention, silently killing the thread | Replaced `expect` with graceful error handling; switched to `Deferred` transactions |
| Reply-before-commit race | `Ok` sent to caller inside open transaction; commit failure rolled back row but caller already got success | Deferred all replies until after `tx.commit()` |
| r2d2 pool exhaustion | `send_message` held pool connection across `await`-ing the writer | Scoped connection to just the read block; dropped before `await` |

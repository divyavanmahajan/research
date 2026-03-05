# Issue 4: Replace SQLite with Batched Background Writer

- [x] Create `db/writer.rs` module for the background writer task.
- [x] Define the `WriteOp` enum and the channel structure.
- [x] Implement the batching loop `run_writer_loop` in `db/writer.rs`.
- [x] Update `AppState` with `mpsc::Sender<WriteOp>`.
- [x] Spawn writer loop in `main.rs`.
- [x] Refactor `api/messages.rs` to send writes through the writer.
- [x] Refactor `api/auth.rs` (`ws_ticket`) to use the writer.
- [x] Wrap Argon2 hashing in `spawn_blocking` to prevent Tokio thread starvation.
- [x] Fix SQL column name bug (`ticket` → `id` in `ws_tickets` INSERT).
- [x] Move writer to dedicated OS thread to avoid blocking Tokio worker pool.
- [x] Fix reply-before-commit race: defer sending `Ok` replies until after `tx.commit()`.
- [x] Release r2d2 pool connection before `await`-ing the writer channel in `send_message`.
- [x] Run manual API smoke tests.
- [x] 500-user load test: 500/500 WS connections, 0 WS errors, 64 K+ messages sent, < 0.01% failure rate.

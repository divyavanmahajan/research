use std::time::Duration;
use rusqlite::Connection;
use tokio::sync::{mpsc, oneshot};
use uuid::Uuid;

pub enum WriteOp {
    InsertDirectMessage {
        msg_id: String,
        sender_id: String,
        recipient_id: String,
        ciphertext: Vec<u8>,
        message_type: String,
        file_id: Option<String>,
        sent_at: String,
        /// Returns the `conv_id` on success.
        reply: oneshot::Sender<Result<String, String>>,
    },
    InsertGroupMessage {
        msg_id: String,
        group_id: String,
        sender_id: String,
        ciphertext: Vec<u8>,
        message_type: String,
        file_id: Option<String>,
        sent_at: String,
        reply: oneshot::Sender<Result<(), String>>,
    },
    InsertWsTicket {
        ticket: String,
        user_id: String,
        expires_at: String,
        reply: oneshot::Sender<Result<(), String>>,
    },
}

/// Internal result collected per-op during the transaction, before commit.
enum OpResult {
    DirectMessage {
        reply: oneshot::Sender<Result<String, String>>,
        result: Result<String, String>,
    },
    Unit {
        reply: oneshot::Sender<Result<(), String>>,
        result: Result<(), String>,
    },
}

/// Spawn a dedicated OS thread that owns the SQLite connection and processes
/// write batches, plus an async bridge task that forwards from the Tokio
/// mpsc channel to the OS thread's std channel.
///
/// Using a real OS thread means SQLite's blocking I/O never touches the
/// Tokio worker pool.
///
/// Replies are sent to callers **only after** the transaction commits.
/// This avoids a race where a caller receives `Ok` but the row was rolled back.
pub async fn run_writer_loop(mut rx: mpsc::Receiver<WriteOp>, db_path: String) {
    // Pipe between the async bridge and the OS writer thread.
    let (thread_tx, thread_rx) = std::sync::mpsc::channel::<Vec<WriteOp>>();

    // Spawn the blocking SQLite writer on its own OS thread.
    std::thread::spawn(move || {
        let mut conn = match Connection::open(&db_path) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("writer: failed to open db: {e}");
                return;
            }
        };
        if let Err(e) = conn.execute_batch(crate::db::schema::INIT_PRAGMAS) {
            eprintln!("writer: pragmas failed: {e}");
            return;
        }

        loop {
            // Wait for the first batch from the bridge.
            let ops = match thread_rx.recv() {
                Ok(ops) => ops,
                Err(_) => break, // Sender dropped, we're done.
            };

            if ops.is_empty() {
                continue;
            }

            // Drain any additional batches that arrived while we were
            // processing the last one (but don't wait for them).
            let mut all_ops = ops;
            while let Ok(more) = thread_rx.try_recv() {
                all_ops.extend(more);
                if all_ops.len() >= 2000 {
                    break;
                }
            }

            // Use Deferred transactions — safe in WAL mode (concurrent readers fine).
            let tx = match conn.transaction_with_behavior(rusqlite::TransactionBehavior::Deferred) {
                Ok(t) => t,
                Err(e) => {
                    eprintln!("writer: begin transaction failed: {e}");
                    for op in all_ops {
                        send_error(op, format!("begin failed: {e}"));
                    }
                    continue;
                }
            };

            // Execute each op and collect pending results (without sending yet).
            let mut pending: Vec<OpResult> = Vec::with_capacity(all_ops.len());
            for op in all_ops {
                let r = execute_op_collect(&tx, op);
                pending.push(r);
            }

            // Commit. If commit succeeds, dispatch all pending results.
            // If commit fails, send Error to all callers.
            match tx.commit() {
                Ok(()) => {
                    for r in pending {
                        dispatch(r);
                    }
                }
                Err(e) => {
                    eprintln!("writer: commit failed: {e}");
                    for r in pending {
                        send_pending_error(r, format!("commit failed: {e}"));
                    }
                }
            }
        }
    });

    // Async bridge: collect ops with a 5ms batching window, then push to
    // the OS thread.  This loop runs as a normal Tokio task and never
    // touches SQLite, so it never blocks the Tokio runtime.
    loop {
        // Wait for at least one op.
        let first = match rx.recv().await {
            Some(op) => op,
            None => break,
        };

        let mut batch = vec![first];

        // Collect more ops that arrive within the next 5 ms.
        let deadline = tokio::time::sleep(Duration::from_millis(5));
        tokio::pin!(deadline);

        loop {
            if batch.len() >= 1000 {
                break;
            }
            tokio::select! {
                biased;
                _ = &mut deadline => break,
                res = rx.recv() => match res {
                    Some(op) => batch.push(op),
                    None => {
                        // Channel closed; send what we have and exit.
                        let _ = thread_tx.send(batch);
                        return;
                    }
                },
            }
        }

        // If the OS thread panicked and the channel is broken, give up.
        if thread_tx.send(batch).is_err() {
            eprintln!("writer: OS thread died, giving up");
            break;
        }
    }
}

fn send_error(op: WriteOp, msg: String) {
    match op {
        WriteOp::InsertDirectMessage { reply, .. } => { let _ = reply.send(Err(msg)); }
        WriteOp::InsertGroupMessage  { reply, .. } => { let _ = reply.send(Err(msg)); }
        WriteOp::InsertWsTicket      { reply, .. } => { let _ = reply.send(Err(msg)); }
    }
}

fn dispatch(r: OpResult) {
    match r {
        OpResult::DirectMessage { reply, result } => { let _ = reply.send(result); }
        OpResult::Unit { reply, result }           => { let _ = reply.send(result); }
    }
}

fn send_pending_error(r: OpResult, msg: String) {
    match r {
        OpResult::DirectMessage { reply, .. } => { let _ = reply.send(Err(msg)); }
        OpResult::Unit { reply, .. }           => { let _ = reply.send(Err(msg)); }
    }
}

/// Execute one op within the given transaction, returning a pending result
/// that will be dispatched to the caller once the transaction commits.
fn execute_op_collect(tx: &rusqlite::Transaction, op: WriteOp) -> OpResult {
    match op {
        WriteOp::InsertDirectMessage {
            msg_id, sender_id, recipient_id, ciphertext,
            message_type, file_id, sent_at, reply,
        } => {
            let (a, b) = if sender_id < recipient_id {
                (&sender_id, &recipient_id)
            } else {
                (&recipient_id, &sender_id)
            };

            // Find or create the conversation.
            let existing = tx.query_row(
                "SELECT id FROM conversations WHERE participant_a = ?1 AND participant_b = ?2",
                rusqlite::params![a, b],
                |row| row.get::<_, String>(0),
            );

            let conv_id = match existing {
                Ok(id) => id,
                Err(_) => {
                    let id = Uuid::new_v4().to_string();
                    if let Err(e) = tx.execute(
                        "INSERT INTO conversations (id, participant_a, participant_b) VALUES (?1, ?2, ?3)",
                        rusqlite::params![id, a, b],
                    ) {
                        return OpResult::DirectMessage { reply, result: Err(e.to_string()) };
                    }
                    id
                }
            };

            let res = tx.execute(
                "INSERT INTO messages \
                 (id, conversation_id, sender_id, recipient_id, ciphertext, message_type, file_id, sent_at) \
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                rusqlite::params![msg_id, conv_id, sender_id, recipient_id, ciphertext, message_type, file_id, sent_at],
            );
            let result = res.map(|_| conv_id).map_err(|e| e.to_string());
            OpResult::DirectMessage { reply, result }
        }

        WriteOp::InsertGroupMessage {
            msg_id, group_id, sender_id, ciphertext,
            message_type, file_id, sent_at, reply,
        } => {
            let res = tx.execute(
                "INSERT INTO messages \
                 (id, group_id, sender_id, ciphertext, message_type, file_id, sent_at) \
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                rusqlite::params![msg_id, group_id, sender_id, ciphertext, message_type, file_id, sent_at],
            );
            let result = res.map(|_| ()).map_err(|e| e.to_string());
            OpResult::Unit { reply, result }
        }

        WriteOp::InsertWsTicket { ticket, user_id, expires_at, reply } => {
            let res = tx.execute(
                "INSERT INTO ws_tickets (id, user_id, expires_at) VALUES (?1, ?2, ?3)",
                rusqlite::params![ticket, user_id, expires_at],
            );
            let result = res.map(|_| ()).map_err(|e| e.to_string());
            OpResult::Unit { reply, result }
        }
    }
}

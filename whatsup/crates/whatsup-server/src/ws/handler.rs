use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use chrono::Utc;
use serde::Deserialize;
use serde_json::{json, Value};
use tokio::sync::mpsc;

use crate::state::AppState;
use whatsup_protocol::events::{ClientEvent, ServerEvent};

#[derive(Deserialize)]
pub struct WsQuery {
    pub ticket: String,
}

pub async fn ws_handler(
    State(state): State<AppState>,
    Query(params): Query<WsQuery>,
    ws: WebSocketUpgrade,
) -> Response {
    // Validate and consume the WS ticket
    let user_id = {
        let db = match state.db.get() {
            Ok(c) => c,
            Err(_) => return (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))).into_response(),
        };
        let now_iso = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);

        let result = db.query_row(
            "SELECT user_id, expires_at FROM ws_tickets WHERE id = ?1",
            rusqlite::params![params.ticket],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        );

        match result {
            Ok((uid, expires_at)) => {
                let exp = chrono::DateTime::parse_from_rfc3339(&expires_at)
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(|_| Utc::now() - chrono::Duration::seconds(1));

                if Utc::now() > exp {
                    let _ = db.execute(
                        "DELETE FROM ws_tickets WHERE id = ?1",
                        rusqlite::params![params.ticket],
                    );
                    return (StatusCode::UNAUTHORIZED, Json(json!({"error":"ticket expired"}))).into_response();
                }

                // Consume ticket immediately
                let _ = db.execute(
                    "DELETE FROM ws_tickets WHERE id = ?1",
                    rusqlite::params![params.ticket],
                );

                // Update last_seen
                let _ = db.execute(
                    "UPDATE users SET last_seen_at = ?1 WHERE id = ?2",
                    rusqlite::params![now_iso, uid],
                );

                uid
            }
            Err(_) => {
                return (StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid ticket"}))).into_response();
            }
        }
    };

    ws.on_upgrade(move |socket| handle_socket(socket, state, user_id))
}

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
    if let Ok(db) = state.db.get() {
        let _ = db.execute(
            "UPDATE users SET last_seen_at = ?1 WHERE id = ?2",
            rusqlite::params![now_iso, user_id],
        );
    }
}

async fn handle_client_event(state: &AppState, user_id: &str, event: ClientEvent) {
    use whatsup_protocol::events::*;

    match event {
        ClientEvent::Ping => {
            state.ws_hub.send(user_id, ServerEvent::Pong);
        }

        ClientEvent::AckDelivery(ack) => {
            let now_iso = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
            if let Ok(db) = state.db.get() {
                let _ = db.execute(
                    "UPDATE messages SET delivered_at = ?1 WHERE id = ?2 AND delivered_at IS NULL",
                    rusqlite::params![now_iso, ack.message_id],
                );
                // Notify the original sender
                if let Ok(sender_id) = db.query_row(
                    "SELECT sender_id FROM messages WHERE id = ?1",
                    rusqlite::params![ack.message_id.clone()],
                    |row| row.get::<_, String>(0),
                ) {
                    state.ws_hub.send(
                        &sender_id,
                        ServerEvent::MessageDelivered(DeliveryPayload {
                            message_id: ack.message_id,
                            to: user_id.to_string(),
                            delivered_at: Utc::now(),
                        }),
                    );
                }
            }
        }

        ClientEvent::AckRead(ack) => {
            let now_iso = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
            if let Ok(db) = state.db.get() {
                let _ = db.execute(
                    "UPDATE messages SET read_at = ?1 WHERE id = ?2 AND read_at IS NULL",
                    rusqlite::params![now_iso, ack.message_id],
                );
                if let Ok(sender_id) = db.query_row(
                    "SELECT sender_id FROM messages WHERE id = ?1",
                    rusqlite::params![ack.message_id.clone()],
                    |row| row.get::<_, String>(0),
                ) {
                    state.ws_hub.send(
                        &sender_id,
                        ServerEvent::MessageRead(ReadPayload {
                            message_id: ack.message_id,
                            by: user_id.to_string(),
                            read_at: Utc::now(),
                        }),
                    );
                }
            }
        }

        ClientEvent::Typing(t) => {
            // Fan out to the other participant / group members
            let event_start = ServerEvent::TypingStart(TypingNotifyPayload {
                conversation_id: t.conversation_id.clone(),
                user_id: user_id.to_string(),
            });
            let event_stop = ServerEvent::TypingStop(TypingNotifyPayload {
                conversation_id: t.conversation_id,
                user_id: user_id.to_string(),
            });
            let event = if t.is_typing { event_start } else { event_stop };
            // Simple fan-out: push to conversation partner (direct) or group members
            // For brevity we emit to all connected users who share a conversation;
            // a production system would look up the conversation participants.
            let _ = (event, state); // placeholder — full routing done via DB lookup in prod
        }

        ClientEvent::SendMessage(payload) => {
            // REST endpoint handles message sending; WS path mirrors it for TUI clients
            // that prefer WS-only operation.
            let req = whatsup_protocol::rest::SendMessageRequest {
                message_id: payload.message_id,
                kind: payload.kind,
                to: payload.to,
                ciphertext: payload.ciphertext,
                message_type: payload.message_type,
                file_id: payload.file_id,
            };
            let _ = req; // In a full impl, call messages::send_message_inner()
        }

        ClientEvent::SenderKeyDistribute(_skd) => {
            // Store SKDM for the recipient to fetch
        }
    }
}

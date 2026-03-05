use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Extension, Json,
};
use base64::{engine::general_purpose::STANDARD as B64, Engine};
use chrono::Utc;
use serde::Deserialize;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::{middleware::auth::Claims, state::AppState};
use whatsup_protocol::{
    events::{NewMessagePayload, ServerEvent},
    rest::{MessageRecord, SendMessageRequest},
};

const MAX_CIPHERTEXT_BYTES: usize = 65_536; // 64 KB

#[derive(Deserialize)]
pub struct PageQuery {
    pub before: Option<String>,
    pub limit: Option<i64>,
}

pub async fn send_message(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(req): Json<SendMessageRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Enforce ciphertext size limit
    let ct_bytes = B64.decode(&req.ciphertext)
        .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid ciphertext"}))))?;
    if ct_bytes.len() > MAX_CIPHERTEXT_BYTES {
        return Err((StatusCode::PAYLOAD_TOO_LARGE, Json(json!({"error":"message too large"}))));
    }

    let msg_id = Uuid::new_v4().to_string();
    let now = Utc::now();
    let now_iso = now.to_rfc3339_opts(chrono::SecondsFormat::Millis, true);

    let db = state.db.lock().unwrap();

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
    } else {
        // Group message
        let group_id = &req.to;
        // Verify sender is a member
        let is_member: bool = db
            .query_row(
                "SELECT 1 FROM group_members WHERE group_id = ?1 AND user_id = ?2",
                rusqlite::params![group_id, claims.sub],
                |_| Ok(true),
            )
            .unwrap_or(false);
        if !is_member {
            return Err((StatusCode::FORBIDDEN, Json(json!({"error":"not a group member"}))));
        }

        db.execute(
            "INSERT INTO messages (id, group_id, sender_id, ciphertext, message_type, file_id, sent_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            rusqlite::params![
                msg_id, group_id, claims.sub,
                ct_bytes, req.message_type, req.file_id, now_iso
            ],
        ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

        // Fan-out to all group members
        let member_ids: Vec<String> = {
            let mut stmt = db.prepare(
                "SELECT user_id FROM group_members WHERE group_id = ?1 AND user_id != ?2",
            ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
            let x = stmt.query_map(rusqlite::params![group_id, claims.sub], |row| row.get(0))
                .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?
                .filter_map(|r| r.ok())
                .collect();
            x
        };

        for member_id in member_ids {
            state.ws_hub.send(
                &member_id,
                ServerEvent::NewMessage(NewMessagePayload {
                    message_id: msg_id.clone(),
                    from_user_id: claims.sub.clone(),
                    conversation_id: None,
                    group_id: Some(group_id.clone()),
                    ciphertext: req.ciphertext.clone(),
                    message_type: req.message_type.clone(),
                    file_id: req.file_id.clone(),
                    sent_at: now,
                }),
            );
        }
    }

    Ok(Json(json!({"message_id": msg_id, "sent_at": now_iso})))
}

pub async fn get_messages(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Path(conv_id): Path<String>,
    Query(params): Query<PageQuery>,
) -> Result<Json<Vec<MessageRecord>>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();
    let limit = params.limit.unwrap_or(50).min(100);

    // Authorisation: must be a participant or group member
    let is_participant = db
        .query_row(
            "SELECT 1 FROM conversations WHERE id = ?1 AND (participant_a = ?2 OR participant_b = ?2)",
            rusqlite::params![conv_id, claims.sub],
            |_| Ok(true),
        )
        .unwrap_or(false);

    let is_group_member = db
        .query_row(
            "SELECT 1 FROM group_members WHERE group_id = ?1 AND user_id = ?2",
            rusqlite::params![conv_id, claims.sub],
            |_| Ok(true),
        )
        .unwrap_or(false);

    if !is_participant && !is_group_member {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error":"access denied"}))));
    }

    let base_query = if is_participant {
        "SELECT id, sender_id, ciphertext, message_type, file_id, sent_at, delivered_at, read_at
         FROM messages WHERE conversation_id = ?1"
    } else {
        "SELECT id, sender_id, ciphertext, message_type, file_id, sent_at, delivered_at, read_at
         FROM messages WHERE group_id = ?1"
    };

    let (sql, params_vec): (String, Vec<Box<dyn rusqlite::ToSql>>) = if let Some(before) = params.before {
        (
            format!("{base_query} AND sent_at < ?2 ORDER BY sent_at DESC LIMIT ?3"),
            vec![Box::new(conv_id.clone()), Box::new(before), Box::new(limit)],
        )
    } else {
        (
            format!("{base_query} ORDER BY sent_at DESC LIMIT ?2"),
            vec![Box::new(conv_id.clone()), Box::new(limit)],
        )
    };

    let mut stmt = db.prepare(&sql)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    let rows = stmt
        .query_map(rusqlite::params_from_iter(params_vec.iter().map(|p| p.as_ref())), |row| {
            let ct: Vec<u8> = row.get(2)?;
            Ok(MessageRecord {
                id: row.get(0)?,
                from_user_id: row.get(1)?,
                ciphertext: B64.encode(&ct),
                message_type: row.get(3)?,
                file_id: row.get(4)?,
                sent_at: row
                    .get::<_, String>(5)
                    .ok()
                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(Utc::now),
                delivered_at: row
                    .get::<_, Option<String>>(6)?
                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                    .map(|dt| dt.with_timezone(&Utc)),
                read_at: row
                    .get::<_, Option<String>>(7)?
                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                    .map(|dt| dt.with_timezone(&Utc)),
            })
        })
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?
        .filter_map(|r| r.ok())
        .collect();

    Ok(Json(rows))
}

use axum::{
    extract::{Path, State},
    http::StatusCode,
    Extension, Json,
};
use base64::{engine::general_purpose::STANDARD as B64, Engine};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::{middleware::auth::Claims, state::AppState};
use whatsup_protocol::rest::{KeyBundleResponse, OtpkUpload, UploadKeyBundleRequest};

pub async fn upload_bundle(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(req): Json<UploadKeyBundleRequest>,
) -> Result<(StatusCode, Json<Value>), (StatusCode, Json<Value>)> {
    let ik_pub = B64.decode(&req.ik_public)
        .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid ik_public"}))))?;
    let ik_pub_ed = B64.decode(&req.ik_public_ed)
        .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid ik_public_ed"}))))?;
    let spk_pub = B64.decode(&req.spk_public)
        .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid spk_public"}))))?;
    let spk_sig = B64.decode(&req.spk_signature)
        .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid spk_signature"}))))?;

    // Decode all OPK public keys up-front so we can report bad input before touching the DB
    let opk_pairs: Vec<(u32, Vec<u8>)> = req.one_time_prekeys.iter()
        .map(|opk| {
            B64.decode(&opk.public_key)
                .map(|bytes| (opk.id, bytes))
                .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid opk"}))))
        })
        .collect::<Result<_, _>>()?;

    let mut db = state.db.lock().unwrap();
    let tx = db.transaction()
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    tx.execute(
        "INSERT OR REPLACE INTO identity_keys (user_id, ik_public, ik_public_ed) VALUES (?1, ?2, ?3)",
        rusqlite::params![claims.sub, ik_pub, ik_pub_ed],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    tx.execute(
        "INSERT OR REPLACE INTO signed_prekeys (id, user_id, spk_id, spk_public, spk_signature) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![Uuid::new_v4().to_string(), claims.sub, req.spk_id, spk_pub, spk_sig],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    {
        let mut stmt = tx.prepare(
            "INSERT OR IGNORE INTO one_time_prekeys (id, user_id, opk_id, opk_public) VALUES (?1, ?2, ?3, ?4)",
        )
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
        for (opk_id, opk_pub) in &opk_pairs {
            stmt.execute(rusqlite::params![Uuid::new_v4().to_string(), claims.sub, opk_id, opk_pub])
                .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
        }
    }

    tx.commit()
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    Ok((StatusCode::OK, Json(json!({"status":"ok"}))))
}

pub async fn get_bundle(
    State(state): State<AppState>,
    Path(user_id): Path<String>,
) -> Result<Json<KeyBundleResponse>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();

    let (ik_pub, ik_pub_ed): (Vec<u8>, Vec<u8>) = db
        .query_row(
            "SELECT ik_public, ik_public_ed FROM identity_keys WHERE user_id = ?1",
            rusqlite::params![user_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .map_err(|_| (StatusCode::NOT_FOUND, Json(json!({"error":"key bundle not found"}))))?;

    let (spk_id, spk_pub, spk_sig): (u32, Vec<u8>, Vec<u8>) = db
        .query_row(
            "SELECT spk_id, spk_public, spk_signature FROM signed_prekeys WHERE user_id = ?1 ORDER BY spk_id DESC LIMIT 1",
            rusqlite::params![user_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .map_err(|_| (StatusCode::NOT_FOUND, Json(json!({"error":"signed prekey not found"}))))?;

    // Atomically consume one OPK using UPDATE...RETURNING (SQLite 3.35+, bundled is 3.46+)
    let now_iso = chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
    let opk = db.query_row(
        "UPDATE one_time_prekeys
         SET consumed_at = ?1
         WHERE id = (
             SELECT id FROM one_time_prekeys
             WHERE user_id = ?2 AND consumed_at IS NULL
             ORDER BY opk_id ASC LIMIT 1
         )
         RETURNING opk_id, opk_public",
        rusqlite::params![now_iso, user_id],
        |row| Ok((row.get::<_, u32>(0)?, row.get::<_, Vec<u8>>(1)?)),
    ).ok();

    let (opk_id, opk_public) = if let Some((id, pub_bytes)) = opk {
        (Some(id), Some(B64.encode(&pub_bytes)))
    } else {
        (None, None)
    };

    // Notify client if OPK count is low
    let remaining: i64 = db
        .query_row(
            "SELECT COUNT(*) FROM one_time_prekeys WHERE user_id = ?1 AND consumed_at IS NULL",
            rusqlite::params![user_id],
            |row| row.get(0),
        )
        .unwrap_or(0);
    if remaining < 10 {
        use crate::state::AppState;
        use whatsup_protocol::events::{PreKeyLowPayload, ServerEvent};
        state.ws_hub.send(
            &user_id,
            ServerEvent::PreKeyLow(PreKeyLowPayload { remaining: remaining as u32 }),
        );
    }

    Ok(Json(KeyBundleResponse {
        user_id,
        ik_public: B64.encode(&ik_pub),
        ik_public_ed: B64.encode(&ik_pub_ed),
        spk_id,
        spk_public: B64.encode(&spk_pub),
        spk_signature: B64.encode(&spk_sig),
        opk_id,
        opk_public,
    }))
}

pub async fn replenish_prekeys(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(keys): Json<Vec<OtpkUpload>>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let opk_pairs: Vec<(u32, Vec<u8>)> = keys.iter()
        .map(|opk| {
            B64.decode(&opk.public_key)
                .map(|bytes| (opk.id, bytes))
                .map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"invalid opk"}))))
        })
        .collect::<Result<_, _>>()?;

    let mut db = state.db.lock().unwrap();
    let tx = db.transaction()
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    {
        let mut stmt = tx.prepare(
            "INSERT OR IGNORE INTO one_time_prekeys (id, user_id, opk_id, opk_public) VALUES (?1, ?2, ?3, ?4)",
        )
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
        for (opk_id, opk_pub) in &opk_pairs {
            stmt.execute(rusqlite::params![Uuid::new_v4().to_string(), claims.sub, opk_id, opk_pub])
                .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
        }
    }
    tx.commit()
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    Ok(Json(json!({"status":"ok", "added": keys.len()})))
}

pub async fn prekey_count(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();
    let count: i64 = db
        .query_row(
            "SELECT COUNT(*) FROM one_time_prekeys WHERE user_id = ?1 AND consumed_at IS NULL",
            rusqlite::params![claims.sub],
            |row| row.get(0),
        )
        .unwrap_or(0);
    Ok(Json(json!({"remaining": count})))
}

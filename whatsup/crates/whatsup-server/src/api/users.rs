use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Extension, Json,
};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::{middleware::auth::Claims, state::AppState};
use whatsup_protocol::rest::{UpdateProfileRequest, UserProfile};

pub async fn get_me(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
) -> Result<Json<UserProfile>, (StatusCode, Json<Value>)> {
    get_user_by_id_inner(&state, &claims.sub)
}

pub async fn update_me(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(req): Json<UpdateProfileRequest>,
) -> Result<Json<UserProfile>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    if let Some(name) = &req.display_name {
        db.execute(
            "UPDATE users SET display_name = ?1 WHERE id = ?2",
            rusqlite::params![name, claims.sub],
        )
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    }
    if let Some(url) = &req.avatar_url {
        db.execute(
            "UPDATE users SET avatar_url = ?1 WHERE id = ?2",
            rusqlite::params![url, claims.sub],
        )
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    }
    drop(db);
    get_user_by_id_inner(&state, &claims.sub)
}

#[derive(Deserialize)]
pub struct SearchQuery {
    pub q: String,
}

pub async fn search(
    State(state): State<AppState>,
    Query(params): Query<SearchQuery>,
) -> Result<Json<Vec<UserProfile>>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let pattern = format!("%{}%", params.q.replace('%', "\\%").replace('_', "\\_"));
    let mut stmt = db
        .prepare("SELECT id, username, display_name, avatar_url, last_seen_at FROM users WHERE username LIKE ?1 LIMIT 20")
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let users = stmt
        .query_map(rusqlite::params![pattern], |row| {
            Ok(UserProfile {
                id: row.get(0)?,
                username: row.get(1)?,
                display_name: row.get(2)?,
                avatar_url: row.get(3)?,
                last_seen_at: row
                    .get::<_, Option<String>>(4)?
                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                    .map(|dt| dt.with_timezone(&chrono::Utc)),
            })
        })
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?
        .filter_map(|r| r.ok())
        .collect();
    Ok(Json(users))
}

pub async fn get_user(
    State(state): State<AppState>,
    Path(user_id): Path<String>,
) -> Result<Json<UserProfile>, (StatusCode, Json<Value>)> {
    get_user_by_id_inner(&state, &user_id)
}

fn get_user_by_id_inner(
    state: &AppState,
    user_id: &str,
) -> Result<Json<UserProfile>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let result = db.query_row(
        "SELECT id, username, display_name, avatar_url, last_seen_at FROM users WHERE id = ?1",
        rusqlite::params![user_id],
        |row| {
            Ok(UserProfile {
                id: row.get(0)?,
                username: row.get(1)?,
                display_name: row.get(2)?,
                avatar_url: row.get(3)?,
                last_seen_at: row
                    .get::<_, Option<String>>(4)?
                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                    .map(|dt| dt.with_timezone(&chrono::Utc)),
            })
        },
    );
    result
        .map(Json)
        .map_err(|_| (StatusCode::NOT_FOUND, Json(json!({"error":"user not found"}))))
}

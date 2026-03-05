use axum::{
    extract::{Path, State},
    http::StatusCode,
    Extension, Json,
};
use chrono::Utc;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::{middleware::auth::Claims, state::AppState};
use whatsup_protocol::{
    events::{GroupMemberChangePayload, ServerEvent},
    rest::{AddMemberRequest, CreateGroupRequest, GroupInfo, GroupMember},
};

pub async fn create_group(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(req): Json<CreateGroupRequest>,
) -> Result<(StatusCode, Json<Value>), (StatusCode, Json<Value>)> {
    let group_id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
    let db = state.db.lock().unwrap();

    db.execute(
        "INSERT INTO groups (id, name, created_by) VALUES (?1, ?2, ?3)",
        rusqlite::params![group_id, req.name, claims.sub],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    // Add creator as admin
    db.execute(
        "INSERT INTO group_members (group_id, user_id, role) VALUES (?1, ?2, 'admin')",
        rusqlite::params![group_id, claims.sub],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    // Add other members
    for member_id in &req.member_ids {
        if member_id == &claims.sub { continue; }
        db.execute(
            "INSERT OR IGNORE INTO group_members (group_id, user_id, role) VALUES (?1, ?2, 'member')",
            rusqlite::params![group_id, member_id],
        )
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    }

    Ok((StatusCode::CREATED, Json(json!({"group_id": group_id}))))
}

pub async fn get_group(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Path(group_id): Path<String>,
) -> Result<Json<GroupInfo>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();

    // Check membership
    let is_member = db
        .query_row(
            "SELECT 1 FROM group_members WHERE group_id = ?1 AND user_id = ?2",
            rusqlite::params![group_id, claims.sub],
            |_| Ok(true),
        )
        .unwrap_or(false);
    if !is_member {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error":"not a member"}))));
    }

    let (name, avatar_url, created_by, created_at_str): (String, Option<String>, String, String) = db
        .query_row(
            "SELECT name, avatar_url, created_by, created_at FROM groups WHERE id = ?1",
            rusqlite::params![group_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
        )
        .map_err(|_| (StatusCode::NOT_FOUND, Json(json!({"error":"group not found"}))))?;

    let created_at = chrono::DateTime::parse_from_rfc3339(&created_at_str)
        .map(|dt| dt.with_timezone(&Utc))
        .unwrap_or_else(|_| Utc::now());

    let mut stmt = db
        .prepare("SELECT user_id, role, joined_at FROM group_members WHERE group_id = ?1")
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let members: Vec<GroupMember> = stmt
        .query_map(rusqlite::params![group_id], |row| {
            Ok(GroupMember {
                user_id: row.get(0)?,
                role: row.get(1)?,
                joined_at: row
                    .get::<_, String>(2)
                    .ok()
                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(Utc::now),
            })
        })
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?
        .filter_map(|r| r.ok())
        .collect();

    Ok(Json(GroupInfo { id: group_id, name, avatar_url, created_by, created_at, members }))
}

pub async fn list_groups(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
) -> Result<Json<Vec<GroupInfo>>, (StatusCode, Json<Value>)> {
    let group_ids: Vec<String> = {
        let db = state.db.lock().unwrap();
        let mut stmt = db
            .prepare(
                "SELECT g.id FROM groups g
                 JOIN group_members gm ON g.id = gm.group_id
                 WHERE gm.user_id = ?1",
            )
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
        let x = stmt
            .query_map(rusqlite::params![claims.sub], |row| row.get(0))
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?
            .filter_map(|r| r.ok())
            .collect();
        x
    };

    let mut groups = Vec::new();
    for gid in group_ids {
        if let Ok(Json(info)) = get_group(
            State(state.clone()),
            Extension(claims.clone()),
            Path(gid),
        )
        .await
        {
            groups.push(info);
        }
    }
    Ok(Json(groups))
}

pub async fn add_member(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Path(group_id): Path<String>,
    Json(req): Json<AddMemberRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();

    // Only admins may add members
    let role: Option<String> = db
        .query_row(
            "SELECT role FROM group_members WHERE group_id = ?1 AND user_id = ?2",
            rusqlite::params![group_id, claims.sub],
            |row| row.get(0),
        )
        .ok();
    if role.as_deref() != Some("admin") {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error":"only admins can add members"}))));
    }

    db.execute(
        "INSERT OR IGNORE INTO group_members (group_id, user_id, role) VALUES (?1, ?2, 'member')",
        rusqlite::params![group_id, req.user_id],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    state.ws_hub.send(
        &req.user_id,
        ServerEvent::GroupMemberAdded(GroupMemberChangePayload {
            group_id: group_id.clone(),
            changed_user_id: req.user_id.clone(),
            by_user_id: claims.sub.clone(),
        }),
    );

    Ok(Json(json!({"status":"ok"})))
}

pub async fn remove_member(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Path((group_id, user_id)): Path<(String, String)>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();

    // Only admins may remove members; anyone may remove themselves
    let caller_role: Option<String> = db
        .query_row(
            "SELECT role FROM group_members WHERE group_id = ?1 AND user_id = ?2",
            rusqlite::params![group_id, claims.sub],
            |row| row.get(0),
        )
        .ok();

    let is_self = claims.sub == user_id;
    let is_admin = caller_role.as_deref() == Some("admin");

    if !is_self && !is_admin {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error":"only admins can remove members"}))));
    }

    db.execute(
        "DELETE FROM group_members WHERE group_id = ?1 AND user_id = ?2",
        rusqlite::params![group_id, user_id],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    state.ws_hub.send(
        &user_id,
        ServerEvent::GroupMemberRemoved(GroupMemberChangePayload {
            group_id,
            changed_user_id: user_id.clone(),
            by_user_id: claims.sub,
        }),
    );

    Ok(Json(json!({"status":"ok"})))
}

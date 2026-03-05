use axum::{
    body::Body,
    extract::{Multipart, Path, State},
    http::{header, StatusCode},
    response::Response,
    Extension, Json,
};
use serde_json::{json, Value};
use std::{fs, io::Write};
use uuid::Uuid;

use crate::{middleware::auth::Claims, state::AppState};
use whatsup_protocol::rest::UploadFileResponse;

const MAX_FILE_BYTES: u64 = 100 * 1024 * 1024; // 100 MB

pub async fn upload_file(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    mut multipart: Multipart,
) -> Result<Json<UploadFileResponse>, (StatusCode, Json<Value>)> {
    fs::create_dir_all(&state.config.upload_dir)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"upload dir"}))))?;

    while let Some(mut field) = multipart.next_field().await.map_err(|_| {
        (StatusCode::BAD_REQUEST, Json(json!({"error":"multipart error"})))
    })? {
        let original_name = field
            .file_name()
            .unwrap_or("upload")
            .to_string();
        let mime = field
            .content_type()
            .unwrap_or("application/octet-stream")
            .to_string();

        let file_id = Uuid::new_v4().to_string();
        // storage_path is UUID-based — never derived from user input
        let storage_path = format!("{}/{}", state.config.upload_dir, file_id);

        let mut file = fs::File::create(&storage_path)
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"file create"}))))?;

        let mut total_bytes: u64 = 0;
        while let Some(chunk) = field.chunk().await.map_err(|_| {
            (StatusCode::BAD_REQUEST, Json(json!({"error":"read error"})))
        })? {
            total_bytes += chunk.len() as u64;
            if total_bytes > MAX_FILE_BYTES {
                drop(file);
                let _ = fs::remove_file(&storage_path);
                return Err((
                    StatusCode::PAYLOAD_TOO_LARGE,
                    Json(json!({"error":"file too large (max 100 MB)"})),
                ));
            }
            file.write_all(&chunk)
                .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"write error"}))))?;
        }

        let db = state.db.lock().unwrap();
        db.execute(
            "INSERT INTO files (id, uploader_id, file_name, mime_type, size_bytes, storage_path) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            rusqlite::params![file_id, claims.sub, original_name, mime, total_bytes as i64, storage_path],
        )
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

        return Ok(Json(UploadFileResponse { file_id }));
    }

    Err((StatusCode::BAD_REQUEST, Json(json!({"error":"no file provided"}))))
}

pub async fn download_file(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Path(file_id): Path<String>,
) -> Result<Response, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();

    let (uploader_id, file_name, mime_type, storage_path): (String, String, String, String) = db
        .query_row(
            "SELECT uploader_id, file_name, mime_type, storage_path FROM files WHERE id = ?1",
            rusqlite::params![file_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
        )
        .map_err(|_| (StatusCode::NOT_FOUND, Json(json!({"error":"file not found"}))))?;

    // Check authorisation: uploader or recipient of a message referencing this file
    let is_uploader = uploader_id == claims.sub;
    let is_recipient = db
        .query_row(
            "SELECT 1 FROM messages WHERE file_id = ?1 AND recipient_id = ?2",
            rusqlite::params![file_id, claims.sub],
            |_| Ok(true),
        )
        .unwrap_or(false);

    if !is_uploader && !is_recipient {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error":"access denied"}))));
    }

    let contents = fs::read(&storage_path)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"read failed"}))))?;

    // Escape file_name for Content-Disposition (strip non-ASCII chars to prevent header injection)
    let safe_name: String = file_name.chars().filter(|c| c.is_ascii_graphic() && *c != '"' && *c != '\\').collect();

    Ok(Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, mime_type)
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename=\"{safe_name}\""),
        )
        .body(Body::from(contents))
        .unwrap())
}

pub async fn delete_file(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Path(file_id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.lock().unwrap();

    let (uploader_id, storage_path): (String, String) = db
        .query_row(
            "SELECT uploader_id, storage_path FROM files WHERE id = ?1",
            rusqlite::params![file_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .map_err(|_| (StatusCode::NOT_FOUND, Json(json!({"error":"file not found"}))))?;

    if uploader_id != claims.sub {
        return Err((StatusCode::FORBIDDEN, Json(json!({"error":"access denied"}))));
    }

    db.execute("DELETE FROM files WHERE id = ?1", rusqlite::params![file_id])
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;

    let _ = fs::remove_file(&storage_path);

    Ok(Json(json!({"status":"deleted"})))
}

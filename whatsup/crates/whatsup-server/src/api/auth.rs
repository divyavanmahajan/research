use std::time::{SystemTime, UNIX_EPOCH};

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Key, Nonce,
};
use argon2::{
    password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2, Params,
};
use axum::{extract::State, http::StatusCode, Extension, Json};
use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
use rand::{rngs::OsRng, RngCore};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use totp_rs::{Algorithm as TotpAlgorithm, Secret, TOTP};
use uuid::Uuid;

use crate::{middleware::auth::Claims, state::AppState};
use whatsup_protocol::rest::*;

const ACCESS_TOKEN_SECS: u64 = 900;
const REFRESH_TOKEN_SECS: i64 = 2_592_000;
const CHALLENGE_TTL_SECS: i64 = 300;
const MAX_2FA_ATTEMPTS: i64 = 5;

fn argon2() -> Argon2<'static> {
    let params = Params::new(65536, 3, 4, None).expect("valid argon2 params");
    Argon2::new(argon2::Algorithm::Argon2id, argon2::Version::V0x13, params)
}

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

fn now_iso() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true)
}

fn make_access_token(user_id: &str, secret: &[u8]) -> Result<String, StatusCode> {
    let now = now_secs();
    let claims = Claims { sub: user_id.to_string(), iat: now, exp: now + ACCESS_TOKEN_SECS };
    encode(&Header::new(Algorithm::HS256), &claims, &EncodingKey::from_secret(secret))
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

fn sha256_hex(data: &[u8]) -> String {
    Sha256::digest(data).iter().map(|b| format!("{b:02x}")).collect()
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn encrypt_totp_secret(secret: &[u8], key: &[u8]) -> Result<Vec<u8>, aes_gcm::Error> {
    let aes_key = Key::<Aes256Gcm>::from_slice(&key[..32]);
    let cipher = Aes256Gcm::new(aes_key);
    let mut nonce_bytes = [0u8; 12];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);
    let mut ct = cipher.encrypt(nonce, secret)?;
    let mut out = nonce_bytes.to_vec();
    out.append(&mut ct);
    Ok(out)
}

fn decrypt_totp_secret(data: &[u8], key: &[u8]) -> Result<Vec<u8>, aes_gcm::Error> {
    let aes_key = Key::<Aes256Gcm>::from_slice(&key[..32]);
    let cipher = Aes256Gcm::new(aes_key);
    let nonce = Nonce::from_slice(&data[..12]);
    cipher.decrypt(nonce, &data[12..])
}

fn build_totp(user_id: &str, secret_bytes: &[u8]) -> Result<TOTP, String> {
    TOTP::new(
        TotpAlgorithm::SHA1,
        6,
        1,
        30,
        secret_bytes.to_vec(),
        Some("WhatsUp".to_string()),
        user_id.to_string(),
    )
    .map_err(|e| e.to_string())
}

fn generate_backup_codes(
    db: &rusqlite::Connection,
    user_id: &str,
) -> Result<Vec<String>, rusqlite::Error> {
    db.execute("DELETE FROM backup_codes WHERE user_id = ?1", rusqlite::params![user_id])?;
    let argon = argon2();
    let mut codes = Vec::with_capacity(8);
    for _ in 0..8 {
        let mut raw = [0u8; 8];
        OsRng.fill_bytes(&mut raw);
        let code = hex_encode(&raw);
        let salt = SaltString::generate(&mut OsRng);
        let hash = argon.hash_password(code.as_bytes(), &salt).unwrap().to_string();
        db.execute(
            "INSERT INTO backup_codes (id, user_id, code_hash) VALUES (?1, ?2, ?3)",
            rusqlite::params![Uuid::new_v4().to_string(), user_id, hash],
        )?;
        codes.push(code);
    }
    Ok(codes)
}

fn verify_backup_code(
    db: &rusqlite::Connection,
    user_id: &str,
    code: &str,
) -> Result<bool, (StatusCode, Json<Value>)> {
    let rows: Vec<(String, String)> = {
        let mut stmt = db
            .prepare(
                "SELECT id, code_hash FROM backup_codes WHERE user_id = ?1 AND used_at IS NULL",
            )
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
        let x = stmt.query_map(rusqlite::params![user_id], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?
        .filter_map(|r| r.ok())
        .collect();
        x
    };
    let argon = argon2();
    for (id, hash) in rows {
        if let Ok(parsed) = PasswordHash::new(&hash) {
            if argon.verify_password(code.as_bytes(), &parsed).is_ok() {
                let now = now_iso();
                let _ = db.execute(
                    "UPDATE backup_codes SET used_at = ?1 WHERE id = ?2",
                    rusqlite::params![now, id],
                );
                return Ok(true);
            }
        }
    }
    Ok(false)
}

fn issue_tokens(
    user_id: &str,
    state: &AppState,
    db: &rusqlite::Connection,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let access_token = make_access_token(user_id, &state.config.jwt_secret)
        .map_err(|e| (e, Json(json!({"error":"token creation failed"}))))?;
    let mut refresh_raw_bytes = [0u8; 32];
    OsRng.fill_bytes(&mut refresh_raw_bytes);
    let refresh_raw = hex_encode(&refresh_raw_bytes);
    let token_hash = sha256_hex(refresh_raw.as_bytes());
    let family_id = Uuid::new_v4().to_string();
    let token_id = Uuid::new_v4().to_string();
    let expires_at = chrono::Utc::now() + chrono::Duration::seconds(REFRESH_TOKEN_SECS);
    let expires_iso = expires_at.to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
    db.execute(
        "INSERT INTO refresh_tokens (id, user_id, token_hash, family_id, expires_at) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![token_id, user_id, token_hash, family_id, expires_iso],
    )
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"token storage failed"}))))?;
    Ok(Json(json!({"access_token": access_token, "refresh_token": refresh_raw, "expires_in": ACCESS_TOKEN_SECS})))
}

pub async fn register(
    State(state): State<AppState>,
    Json(req): Json<RegisterRequest>,
) -> Result<(StatusCode, Json<Value>), (StatusCode, Json<Value>)> {
    let password = req.password.clone();
    let hash = tokio::task::spawn_blocking(move || {
        let salt = SaltString::generate(&mut OsRng);
        argon2()
            .hash_password(password.as_bytes(), &salt)
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"hash failed"}))))
            .map(|val| val.to_string())
    })
    .await
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"join error"}))))??;

    let user_id = Uuid::new_v4().to_string();
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    db.execute(
        "INSERT INTO users (id, username, phone_number, display_name, password_hash) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![user_id, req.username, req.phone_number, req.display_name, hash],
    )
    .map_err(|e| {
        if e.to_string().contains("UNIQUE") {
            (StatusCode::CONFLICT, Json(json!({"error":"username already taken"})))
        } else {
            (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":e.to_string()})))
        }
    })?;
    Ok((StatusCode::CREATED, Json(json!({"user_id": user_id}))))
}

pub async fn login(
    State(state): State<AppState>,
    Json(req): Json<LoginRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let result = db.query_row(
        "SELECT id, password_hash FROM users WHERE username = ?1 AND is_active = 1",
        rusqlite::params![req.username],
        |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
    );
    let (user_id, stored_hash) = result.map_err(|_| {
        (StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid credentials"})))
    })?;
    let parsed_hash_str = stored_hash.clone();
    let password = req.password.clone();
    tokio::task::spawn_blocking(move || {
        let parsed = PasswordHash::new(&parsed_hash_str)
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
        argon2().verify_password(password.as_bytes(), &parsed)
            .map_err(|_| (StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid credentials"}))))
    })
    .await
    .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"join error"}))))??;
    let two_fa_enabled: bool = db
        .query_row(
            "SELECT enabled FROM totp_secrets WHERE user_id = ?1",
            rusqlite::params![user_id],
            |row| row.get::<_, i64>(0),
        )
        .map(|v| v == 1)
        .unwrap_or(false);
    if two_fa_enabled {
        let challenge_id = Uuid::new_v4().to_string();
        let expires_at = chrono::Utc::now() + chrono::Duration::seconds(CHALLENGE_TTL_SECS);
        let expires_iso = expires_at.to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
        db.execute(
            "INSERT INTO two_fa_challenges (id, user_id, expires_at) VALUES (?1, ?2, ?3)",
            rusqlite::params![challenge_id, user_id, expires_iso],
        ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
        return Ok(Json(json!({"status":"2fa_required","challenge_token":challenge_id})));
    }
    issue_tokens(&user_id, &state, &db)
}

pub async fn two_fa_challenge(
    State(state): State<AppState>,
    Json(req): Json<TwoFaChallengeRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let result = db.query_row(
        "SELECT user_id, expires_at, attempt_count FROM two_fa_challenges WHERE id = ?1",
        rusqlite::params![req.challenge_token],
        |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, i64>(2)?)),
    );
    let (user_id, expires_at, attempt_count) = result
        .map_err(|_| (StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid challenge token"}))))?;
    let expires = chrono::DateTime::parse_from_rfc3339(&expires_at)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    if chrono::Utc::now() > expires {
        let _ = db.execute("DELETE FROM two_fa_challenges WHERE id = ?1", rusqlite::params![req.challenge_token]);
        return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"challenge expired"}))));
    }
    if attempt_count >= MAX_2FA_ATTEMPTS {
        let _ = db.execute("DELETE FROM two_fa_challenges WHERE id = ?1", rusqlite::params![req.challenge_token]);
        return Err((StatusCode::TOO_MANY_REQUESTS, Json(json!({"error":"too many attempts"}))));
    }
    let secret_enc: Vec<u8> = db
        .query_row("SELECT secret_encrypted FROM totp_secrets WHERE user_id = ?1 AND enabled = 1", rusqlite::params![user_id], |row| row.get(0))
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    let secret_bytes = decrypt_totp_secret(&secret_enc, &state.config.totp_encryption_key)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    let totp = build_totp(&user_id, &secret_bytes)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    let window_ts = now_secs() / 30;
    let already_used: bool = db.query_row(
        "SELECT 1 FROM otp_used WHERE user_id=?1 AND otp_code=?2 AND window_ts=?3",
        rusqlite::params![user_id, req.otp_code, window_ts as i64],
        |_| Ok(true),
    ).unwrap_or(false);
    if already_used {
        let _ = db.execute("UPDATE two_fa_challenges SET attempt_count = attempt_count + 1 WHERE id = ?1", rusqlite::params![req.challenge_token]);
        return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"OTP already used"}))));
    }
    let otp_valid = totp.check_current(&req.otp_code).unwrap_or(false);
    if !otp_valid {
        let backup_ok = verify_backup_code(&db, &user_id, &req.otp_code)?;
        if !backup_ok {
            let _ = db.execute("UPDATE two_fa_challenges SET attempt_count = attempt_count + 1 WHERE id = ?1", rusqlite::params![req.challenge_token]);
            return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid OTP"}))));
        }
    } else {
        let _ = db.execute("INSERT OR IGNORE INTO otp_used (user_id, otp_code, window_ts) VALUES (?1, ?2, ?3)", rusqlite::params![user_id, req.otp_code, window_ts as i64]);
        let old_ts = (now_secs() / 30).saturating_sub(3) as i64;
        let _ = db.execute("DELETE FROM otp_used WHERE window_ts < ?1", rusqlite::params![old_ts]);
    }
    let _ = db.execute("DELETE FROM two_fa_challenges WHERE id = ?1", rusqlite::params![req.challenge_token]);
    issue_tokens(&user_id, &state, &db)
}

pub async fn two_fa_setup(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
) -> Result<Json<TwoFaSetupResponse>, (StatusCode, Json<Value>)> {
    let secret = Secret::generate_secret();
    let secret_bytes = secret.to_bytes()
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"secret gen failed"}))))?;
    let totp = build_totp(&claims.sub, &secret_bytes)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"totp build failed"}))))?;
    let otpauth_uri = totp.get_url();
    let qr_code_base64 = totp.get_qr_base64()
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"qr failed"}))))?;
    let encrypted = encrypt_totp_secret(&secret_bytes, &state.config.totp_encryption_key)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"encrypt failed"}))))?;
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    db.execute(
        "INSERT OR REPLACE INTO totp_secrets (user_id, secret_encrypted, enabled) VALUES (?1, ?2, 0)",
        rusqlite::params![claims.sub, encrypted],
    ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    Ok(Json(TwoFaSetupResponse { otpauth_uri, qr_code_base64 }))
}

pub async fn two_fa_verify(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(req): Json<TwoFaVerifyRequest>,
) -> Result<Json<BackupCodesResponse>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let secret_enc: Vec<u8> = db.query_row(
        "SELECT secret_encrypted FROM totp_secrets WHERE user_id = ?1",
        rusqlite::params![claims.sub], |row| row.get(0),
    ).map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"2FA not set up yet"}))))?;
    let secret_bytes = decrypt_totp_secret(&secret_enc, &state.config.totp_encryption_key)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"decrypt failed"}))))?;
    let totp = build_totp(&claims.sub, &secret_bytes)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    if !totp.check_current(&req.otp_code).unwrap_or(false) {
        return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid OTP"}))));
    }
    db.execute("UPDATE totp_secrets SET enabled = 1 WHERE user_id = ?1", rusqlite::params![claims.sub])
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let codes = generate_backup_codes(&db, &claims.sub)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"backup codes"}))))?;
    Ok(Json(BackupCodesResponse { codes }))
}

pub async fn two_fa_disable(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
    Json(req): Json<TwoFaDisableRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let stored_hash: String = db.query_row(
        "SELECT password_hash FROM users WHERE id = ?1", rusqlite::params![claims.sub], |row| row.get(0),
    ).map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    let parsed = PasswordHash::new(&stored_hash)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    argon2().verify_password(req.password.as_bytes(), &parsed)
        .map_err(|_| (StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid password"}))))?;
    let secret_enc: Vec<u8> = db.query_row(
        "SELECT secret_encrypted FROM totp_secrets WHERE user_id = ?1 AND enabled = 1",
        rusqlite::params![claims.sub], |row| row.get(0),
    ).map_err(|_| (StatusCode::BAD_REQUEST, Json(json!({"error":"2FA not enabled"}))))?;
    let secret_bytes = decrypt_totp_secret(&secret_enc, &state.config.totp_encryption_key)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    let totp = build_totp(&claims.sub, &secret_bytes)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    let backup_ok = verify_backup_code(&db, &claims.sub, &req.otp_code).unwrap_or(false);
    if !backup_ok && !totp.check_current(&req.otp_code).unwrap_or(false) {
        return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid OTP"}))));
    }
    db.execute("DELETE FROM totp_secrets WHERE user_id = ?1", rusqlite::params![claims.sub])
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    db.execute("DELETE FROM backup_codes WHERE user_id = ?1", rusqlite::params![claims.sub])
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    Ok(Json(json!({"status":"2fa_disabled"})))
}

pub async fn refresh(
    State(state): State<AppState>,
    Json(req): Json<RefreshRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let token_hash = sha256_hex(req.refresh_token.as_bytes());
    let result = db.query_row(
        "SELECT id, user_id, family_id, expires_at FROM refresh_tokens WHERE token_hash = ?1",
        rusqlite::params![token_hash],
        |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, String>(2)?, row.get::<_, String>(3)?)),
    );
    let (token_id, user_id, family_id, expires_at) = result
        .map_err(|_| (StatusCode::UNAUTHORIZED, Json(json!({"error":"invalid refresh token"}))))?;
    let exp = chrono::DateTime::parse_from_rfc3339(&expires_at)
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"internal"}))))?;
    if chrono::Utc::now() > exp {
        let _ = db.execute("DELETE FROM refresh_tokens WHERE id = ?1", rusqlite::params![token_id]);
        return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"refresh token expired"}))));
    }
    let deleted = db.execute("DELETE FROM refresh_tokens WHERE id = ?1", rusqlite::params![token_id]).unwrap_or(0);
    if deleted == 0 {
        let _ = db.execute("DELETE FROM refresh_tokens WHERE family_id = ?1", rusqlite::params![family_id]);
        return Err((StatusCode::UNAUTHORIZED, Json(json!({"error":"token reuse detected"}))));
    }
    issue_tokens(&user_id, &state, &db)
}

pub async fn logout(
    State(state): State<AppState>,
    Json(req): Json<RefreshRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let db = state.db.get().map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error":"db error"}))))?;
    let token_hash = sha256_hex(req.refresh_token.as_bytes());
    let _ = db.execute("DELETE FROM refresh_tokens WHERE token_hash = ?1", rusqlite::params![token_hash]);
    Ok(Json(json!({"status":"logged_out"})))
}

pub async fn ws_ticket(
    State(state): State<AppState>,
    Extension(claims): Extension<Claims>,
) -> Result<Json<WsTicketResponse>, (StatusCode, Json<Value>)> {
    let ticket = Uuid::new_v4().to_string();
    let expires_at = chrono::Utc::now() + chrono::Duration::seconds(60);
    let expires_iso = expires_at.to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
    
    let (tx, rx) = tokio::sync::oneshot::channel();
    state.db_writer.send(crate::db::writer::WriteOp::InsertWsTicket {
        ticket: ticket.clone(),
        user_id: claims.sub,
        expires_at: expires_iso,
        reply: tx,
    }).await.map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "channel full"}))))?;

    rx.await
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "writer crashed"}))))?
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    Ok(Json(WsTicketResponse { ticket }))
}

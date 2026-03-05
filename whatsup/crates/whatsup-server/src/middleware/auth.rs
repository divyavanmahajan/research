use axum::{
    extract::{Request, State},
    http::{header, StatusCode},
    middleware::Next,
    response::Response,
    Json,
};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::state::AppState;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String, // user_id
    pub exp: u64,
    pub iat: u64,
}

/// Axum middleware that extracts and validates the JWT from `Authorization: Bearer <token>`.
/// Stores the validated `Claims` in request extensions.
pub async fn require_auth(
    State(state): State<AppState>,
    mut req: Request,
    next: Next,
) -> Result<Response, (StatusCode, Json<serde_json::Value>)> {
    let token = req
        .headers()
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
        .ok_or_else(|| {
            (
                StatusCode::UNAUTHORIZED,
                Json(json!({"error": "missing authorization header"})),
            )
        })?;

    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = true;

    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(&state.config.jwt_secret),
        &validation,
    )
    .map_err(|_| {
        (StatusCode::UNAUTHORIZED, Json(json!({"error": "invalid or expired token"})))
    })?;

    req.extensions_mut().insert(token_data.claims);
    Ok(next.run(req).await)
}

pub fn extract_claims(req: &Request) -> Option<&Claims> {
    req.extensions().get::<Claims>()
}

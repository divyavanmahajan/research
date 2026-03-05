mod api;
mod config;
mod db;
mod middleware;
mod state;
mod ws;

use anyhow::Result;
use axum::{
    extract::State,
    http::{Method, StatusCode},
    response::Json,
    routing::get,
    Router,
};
use serde_json::json;
use tower_http::{
    cors::{AllowHeaders, AllowMethods, AllowOrigin, CorsLayer},
    limit::RequestBodyLimitLayer,
    trace::TraceLayer,
};
use tracing::info;
use tracing_subscriber::EnvFilter;

use crate::{config::Config, db::open, state::AppState};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let config = Config::from_env()?;
    let db = open(&config.database_path)?;
    let state = AppState::new(config.clone(), db);

    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::exact(
            config.cors_origin.parse().expect("valid cors origin"),
        ))
        .allow_methods(AllowMethods::list([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::PATCH,
            Method::DELETE,
        ]))
        .allow_headers(AllowHeaders::any())
        .allow_credentials(true);

    let app = Router::new()
        .route("/health", get(health))
        .route("/ws", get(ws::handler::ws_handler))
        .merge(api::router(state.clone()))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        // Global 100 MB body limit (enforced again per-route for files)
        .layer(RequestBodyLimitLayer::new(100 * 1024 * 1024))
        .with_state(state);

    let addr = format!("{}:{}", config.host, config.port);
    info!("WhatsUp server listening on {addr}");

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({"status": "ok", "version": env!("CARGO_PKG_VERSION")}))
}

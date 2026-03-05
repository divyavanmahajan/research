use thiserror::Error;

#[derive(Debug, Error)]
pub enum ProtocolError {
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("unknown event type: {0}")]
    UnknownEvent(String),
}

use std::sync::Arc;

use dashmap::DashMap;
use tokio::sync::mpsc;

use crate::{config::Config, db::Db};
use whatsup_protocol::events::ServerEvent;

pub type UserId = String;
pub type WsSender = mpsc::UnboundedSender<ServerEvent>;

/// Shared application state injected into every handler via Axum extractors.
#[derive(Clone)]
pub struct AppState {
    pub config: Arc<Config>,
    pub db: Db,
    pub db_writer: mpsc::Sender<crate::db::writer::WriteOp>,
    /// Live WebSocket connections: user_id → event sender
    pub ws_hub: Arc<WsHub>,
}

pub struct WsHub {
    pub connections: DashMap<UserId, WsSender>,
}

impl WsHub {
    pub fn new() -> Self {
        Self { connections: DashMap::new() }
    }

    pub fn send(&self, user_id: &str, event: ServerEvent) {
        if let Some(tx) = self.connections.get(user_id) {
            let _ = tx.send(event);
        }
    }

    pub fn register(&self, user_id: UserId, tx: WsSender) {
        self.connections.insert(user_id, tx);
    }

    pub fn unregister(&self, user_id: &str) {
        self.connections.remove(user_id);
    }

    pub fn is_online(&self, user_id: &str) -> bool {
        self.connections.contains_key(user_id)
    }
}

impl AppState {
    pub fn new(config: Config, db: Db, db_writer: mpsc::Sender<crate::db::writer::WriteOp>) -> Self {
        Self {
            config: Arc::new(config),
            db,
            db_writer,
            ws_hub: Arc::new(WsHub::new()),
        }
    }
}

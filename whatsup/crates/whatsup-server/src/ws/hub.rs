// Re-export from state — the hub lives in AppState
// This module documents the WS hub design for the code walkthrough.

/// The WebSocket hub is defined in `crate::state::WsHub`.
///
/// Architecture:
/// - `WsHub::connections: DashMap<UserId, UnboundedSender<ServerEvent>>`
///   maps each connected user to the write-half of their WebSocket channel.
/// - `WsHub::send(user_id, event)` delivers an event instantly if the user
///   is connected; silently drops it otherwise (messages are persisted in DB
///   for later retrieval).
/// - `WsHub::register(user_id, tx)` is called on WebSocket upgrade.
/// - `WsHub::unregister(user_id)` is called when the connection closes.
pub use crate::state::WsHub;

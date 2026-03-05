use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// ── Client → Server ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload", rename_all = "PascalCase")]
pub enum ClientEvent {
    SendMessage(SendMessagePayload),
    AckDelivery(AckPayload),
    AckRead(AckPayload),
    Typing(TypingPayload),
    SenderKeyDistribute(SenderKeyDistributePayload),
    Ping,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendMessagePayload {
    pub message_id: String,
    /// "direct" or "group"
    pub kind: String,
    /// Recipient user_id or group_id
    pub to: String,
    /// Base64-encoded ciphertext
    pub ciphertext: String,
    pub message_type: String,
    pub file_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AckPayload {
    pub message_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypingPayload {
    pub conversation_id: String,
    pub is_typing: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SenderKeyDistributePayload {
    pub group_id: String,
    pub recipient_id: String,
    /// Base64-encoded SKDM ciphertext (encrypted over 1:1 Double Ratchet session)
    pub skdm_ciphertext: String,
}

// ── Server → Client ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload", rename_all = "PascalCase")]
pub enum ServerEvent {
    NewMessage(NewMessagePayload),
    MessageDelivered(DeliveryPayload),
    MessageRead(ReadPayload),
    TypingStart(TypingNotifyPayload),
    TypingStop(TypingNotifyPayload),
    PresenceUpdate(PresencePayload),
    GroupMemberAdded(GroupMemberChangePayload),
    GroupMemberRemoved(GroupMemberChangePayload),
    PreKeyLow(PreKeyLowPayload),
    Pong,
    Error(ErrorPayload),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewMessagePayload {
    pub message_id: String,
    pub from_user_id: String,
    pub conversation_id: Option<String>,
    pub group_id: Option<String>,
    pub ciphertext: String,
    pub message_type: String,
    pub file_id: Option<String>,
    pub sent_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeliveryPayload {
    pub message_id: String,
    pub to: String,
    pub delivered_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReadPayload {
    pub message_id: String,
    pub by: String,
    pub read_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypingNotifyPayload {
    pub conversation_id: String,
    pub user_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PresencePayload {
    pub user_id: String,
    pub status: String,
    pub last_seen: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupMemberChangePayload {
    pub group_id: String,
    pub changed_user_id: String,
    pub by_user_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreKeyLowPayload {
    pub remaining: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorPayload {
    pub code: String,
    pub message: String,
}

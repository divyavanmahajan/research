use serde::{Deserialize, Serialize};

/// Kind of conversation a message belongs to.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConversationKind {
    Direct,
    Group,
}

/// Envelope wrapping a ciphertext for transmission.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope {
    /// Base64-encoded Double Ratchet `EncryptedMessage` (JSON-serialised)
    pub ciphertext: String,
    /// "direct" or "group"
    pub kind: ConversationKind,
    /// Recipient user_id (direct) or group_id (group)
    pub to: String,
}

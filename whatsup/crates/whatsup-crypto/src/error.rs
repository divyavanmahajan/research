use thiserror::Error;

#[derive(Debug, Error)]
pub enum CryptoError {
    #[error("invalid key length: expected {expected}, got {got}")]
    InvalidKeyLength { expected: usize, got: usize },

    #[error("signature verification failed")]
    SignatureVerification,

    #[error("decryption failed")]
    DecryptionFailed,

    #[error("no session established")]
    NoSession,

    #[error("message key not found for ratchet step")]
    MessageKeyNotFound,

    #[error("skipped message cache full (max 2000 entries)")]
    SkippedMessageCacheFull,

    #[error("invalid prekey bundle")]
    InvalidPreKeyBundle,

    #[error("serialization error: {0}")]
    Serialization(String),

    #[error("base64 decode error: {0}")]
    Base64(#[from] base64::DecodeError),

    #[error("sender key not found for group {group_id}")]
    SenderKeyNotFound { group_id: String },
}

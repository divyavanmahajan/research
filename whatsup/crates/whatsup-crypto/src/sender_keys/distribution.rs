use serde::{Deserialize, Serialize};

/// SenderKeyDistributionMessage — sent pairwise to each group member,
/// encrypted over their 1:1 Double Ratchet session.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SenderKeyDistributionMessage {
    pub group_id: String,
    pub sender_id: String,
    pub iteration: u32,
    /// Current chain key bytes
    pub chain_key: Vec<u8>,
    /// Ed25519 verifying key bytes
    pub signing_key_pub: Vec<u8>,
}

use serde::{Deserialize, Serialize};

use super::{
    identity_key::IdentityKeyPublic, one_time_prekey::OneTimePreKeyPublic,
    signed_prekey::SignedPreKeyPublic,
};

/// Key bundle uploaded by each user to the server.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreKeyBundle {
    pub user_id: String,
    pub identity_key: IdentityKeyPublic,
    pub signed_prekey: SignedPreKeyPublic,
    /// Absent when the server has run out of one-time prekeys for this user.
    pub one_time_prekey: Option<OneTimePreKeyPublic>,
}

use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret};
use zeroize::ZeroizeOnDrop;

/// One-Time PreKey: X25519 key pair, consumed once during X3DH.
#[derive(ZeroizeOnDrop)]
pub struct OneTimePreKey {
    pub id: u32,
    pub secret: StaticSecret,
}

impl OneTimePreKey {
    pub fn generate(id: u32) -> Self {
        Self { id, secret: StaticSecret::random_from_rng(OsRng) }
    }

    pub fn public_key(&self) -> X25519PublicKey {
        X25519PublicKey::from(&self.secret)
    }

    pub fn to_public(&self) -> OneTimePreKeyPublic {
        OneTimePreKeyPublic { id: self.id, public_key: self.public_key().to_bytes() }
    }
}

/// Serialisable one-time prekey (uploaded to server in bulk).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OneTimePreKeyPublic {
    pub id: u32,
    pub public_key: [u8; 32],
}

impl OneTimePreKeyPublic {
    pub fn x25519_public(&self) -> X25519PublicKey {
        X25519PublicKey::from(self.public_key)
    }
}

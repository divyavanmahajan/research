use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret};
use zeroize::ZeroizeOnDrop;

use super::identity_key::IdentityKeyPair;

/// Signed PreKey: X25519 key pair with an Ed25519 signature by the identity key.
#[derive(ZeroizeOnDrop)]
pub struct SignedPreKey {
    pub id: u32,
    pub secret: StaticSecret,
}

impl SignedPreKey {
    pub fn generate(id: u32) -> Self {
        Self { id, secret: StaticSecret::random_from_rng(OsRng) }
    }

    pub fn public_key(&self) -> X25519PublicKey {
        X25519PublicKey::from(&self.secret)
    }

    /// Sign the public key bytes with the identity signing key.
    pub fn sign(&self, identity: &IdentityKeyPair) -> Vec<u8> {
        identity.sign(self.public_key().as_bytes()).to_bytes().to_vec()
    }

    pub fn to_public(&self, identity: &IdentityKeyPair) -> SignedPreKeyPublic {
        SignedPreKeyPublic {
            id: self.id,
            public_key: self.public_key().to_bytes(),
            signature: self.sign(identity),
        }
    }
}

/// Serialisable signed prekey (sent to server in key bundle).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignedPreKeyPublic {
    pub id: u32,
    pub public_key: [u8; 32],
    /// Ed25519 signature over `public_key` by the identity Ed25519 key
    pub signature: Vec<u8>,
}

impl SignedPreKeyPublic {
    pub fn x25519_public(&self) -> X25519PublicKey {
        X25519PublicKey::from(self.public_key)
    }
}

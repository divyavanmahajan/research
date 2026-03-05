use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret};
use zeroize::ZeroizeOnDrop;

use crate::error::CryptoError;

/// Identity Key pair: X25519 for DH, Ed25519 for signing.
#[derive(ZeroizeOnDrop)]
pub struct IdentityKeyPair {
    /// X25519 secret for DH operations
    pub dh_secret: StaticSecret,
    /// Ed25519 signing key (also used to derive verifying key)
    #[zeroize(skip)]
    pub signing_key: SigningKey,
}

impl IdentityKeyPair {
    pub fn generate() -> Self {
        let dh_secret = StaticSecret::random_from_rng(OsRng);
        let signing_key = SigningKey::generate(&mut OsRng);
        Self { dh_secret, signing_key }
    }

    pub fn dh_public(&self) -> X25519PublicKey {
        X25519PublicKey::from(&self.dh_secret)
    }

    pub fn verifying_key(&self) -> VerifyingKey {
        self.signing_key.verifying_key()
    }

    pub fn sign(&self, message: &[u8]) -> Signature {
        self.signing_key.sign(message)
    }

    pub fn to_public(&self) -> IdentityKeyPublic {
        IdentityKeyPublic {
            dh_public: self.dh_public().to_bytes(),
            ed_public: self.verifying_key().to_bytes(),
        }
    }
}

/// Serialisable public identity key (sent to server in key bundle).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityKeyPublic {
    /// X25519 public key bytes
    pub dh_public: [u8; 32],
    /// Ed25519 verifying key bytes
    pub ed_public: [u8; 32],
}

impl IdentityKeyPublic {
    pub fn dh_public_key(&self) -> X25519PublicKey {
        X25519PublicKey::from(self.dh_public)
    }

    pub fn verifying_key(&self) -> Result<VerifyingKey, CryptoError> {
        VerifyingKey::from_bytes(&self.ed_public)
            .map_err(|_| CryptoError::InvalidKeyLength { expected: 32, got: 32 })
    }

    pub fn verify(&self, message: &[u8], signature: &[u8]) -> Result<(), CryptoError> {
        let vk = self.verifying_key()?;
        let sig = Signature::from_slice(signature)
            .map_err(|_| CryptoError::SignatureVerification)?;
        vk.verify(message, &sig).map_err(|_| CryptoError::SignatureVerification)
    }
}

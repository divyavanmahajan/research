use aes_gcm::{
    aead::{Aead, KeyInit, Payload},
    Aes256Gcm, Key, Nonce,
};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use zeroize::ZeroizeOnDrop;

use crate::{double_ratchet::chain::kdf_ck, error::CryptoError};

/// Sender Key state for a single `(group_id, sender_id)` pair.
#[derive(ZeroizeOnDrop)]
pub struct SenderKeyState {
    pub chain_key: [u8; 32],
    pub iteration: u32,
    #[zeroize(skip)]
    pub signing_key: SigningKey,
}

impl SenderKeyState {
    pub fn generate() -> Self {
        use rand::RngCore;
        let mut chain_key = [0u8; 32];
        OsRng.fill_bytes(&mut chain_key);
        Self {
            chain_key,
            iteration: 0,
            signing_key: SigningKey::generate(&mut OsRng),
        }
    }

    pub fn verifying_key(&self) -> VerifyingKey {
        self.signing_key.verifying_key()
    }

    /// Encrypt a plaintext for group broadcast.
    ///
    /// Returns `(SenderKeyMessage, new_state)`.
    pub fn encrypt(&mut self, plaintext: &[u8]) -> Result<SenderKeyMessage, CryptoError> {
        let (new_ck, mk) = kdf_ck(&self.chain_key);
        self.chain_key = new_ck;
        let iteration = self.iteration;
        self.iteration += 1;

        let key = Key::<Aes256Gcm>::from_slice(&mk[..32]);
        let nonce = Nonce::from_slice(&mk[32..44]);
        let cipher = Aes256Gcm::new(key);

        let ciphertext = cipher
            .encrypt(nonce, Payload { msg: plaintext, aad: b"sender-key-msg" })
            .map_err(|_| CryptoError::DecryptionFailed)?;

        let mut to_sign = iteration.to_le_bytes().to_vec();
        to_sign.extend_from_slice(&ciphertext);
        let signature = self.signing_key.sign(&to_sign).to_bytes().to_vec();

        Ok(SenderKeyMessage { iteration, ciphertext, signature })
    }

    /// Decrypt a `SenderKeyMessage`.
    pub fn decrypt(
        &mut self,
        msg: &SenderKeyMessage,
        verifying_key: &VerifyingKey,
    ) -> Result<Vec<u8>, CryptoError> {
        // Verify signature
        let mut to_verify = msg.iteration.to_le_bytes().to_vec();
        to_verify.extend_from_slice(&msg.ciphertext);
        let sig = Signature::from_slice(&msg.signature)
            .map_err(|_| CryptoError::SignatureVerification)?;
        verifying_key.verify(&to_verify, &sig).map_err(|_| CryptoError::SignatureVerification)?;

        // Advance chain to msg.iteration
        while self.iteration < msg.iteration {
            let (new_ck, _) = kdf_ck(&self.chain_key);
            self.chain_key = new_ck;
            self.iteration += 1;
        }

        let (new_ck, mk) = kdf_ck(&self.chain_key);
        self.chain_key = new_ck;
        self.iteration += 1;

        let key = Key::<Aes256Gcm>::from_slice(&mk[..32]);
        let nonce = Nonce::from_slice(&mk[32..44]);
        let cipher = Aes256Gcm::new(key);

        cipher
            .decrypt(nonce, Payload { msg: &msg.ciphertext, aad: b"sender-key-msg" })
            .map_err(|_| CryptoError::DecryptionFailed)
    }
}

/// An encrypted group message produced by the Sender Key ratchet.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SenderKeyMessage {
    pub iteration: u32,
    pub ciphertext: Vec<u8>,
    pub signature: Vec<u8>,
}

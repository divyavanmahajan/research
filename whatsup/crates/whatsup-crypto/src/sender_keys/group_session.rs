use std::collections::HashMap;

use ed25519_dalek::VerifyingKey;
use serde::{Deserialize, Serialize};
use zeroize::ZeroizeOnDrop;

use crate::error::CryptoError;

use super::{
    distribution::SenderKeyDistributionMessage,
    sender_key::{SenderKeyMessage, SenderKeyState},
};

/// Per-group session managing our own sending state and per-sender receive states.
pub struct GroupSession {
    pub group_id: String,
    /// Our own sender key state for this group
    pub sender_state: SenderKeyState,
    /// Received sender states: sender_id → (state, verifying_key)
    pub receiver_states: HashMap<String, ReceiverEntry>,
}

pub struct ReceiverEntry {
    pub chain_key: [u8; 32],
    pub iteration: u32,
    pub verifying_key: VerifyingKey,
}

impl GroupSession {
    pub fn new(group_id: impl Into<String>) -> Self {
        Self {
            group_id: group_id.into(),
            sender_state: SenderKeyState::generate(),
            receiver_states: HashMap::new(),
        }
    }

    /// Build a `SenderKeyDistributionMessage` to send to a new or existing member.
    pub fn create_distribution_message(&self, sender_id: impl Into<String>) -> SenderKeyDistributionMessage {
        SenderKeyDistributionMessage {
            group_id: self.group_id.clone(),
            sender_id: sender_id.into(),
            iteration: self.sender_state.iteration,
            chain_key: self.sender_state.chain_key.to_vec(),
            signing_key_pub: self.sender_state.verifying_key().to_bytes().to_vec(),
        }
    }

    /// Process a `SenderKeyDistributionMessage` received from another member.
    pub fn process_distribution(
        &mut self,
        skdm: &SenderKeyDistributionMessage,
    ) -> Result<(), CryptoError> {
        if skdm.chain_key.len() != 32 {
            return Err(CryptoError::InvalidKeyLength { expected: 32, got: skdm.chain_key.len() });
        }
        if skdm.signing_key_pub.len() != 32 {
            return Err(CryptoError::InvalidKeyLength {
                expected: 32,
                got: skdm.signing_key_pub.len(),
            });
        }

        let mut chain_key = [0u8; 32];
        chain_key.copy_from_slice(&skdm.chain_key);

        let vk_bytes: [u8; 32] = skdm.signing_key_pub[..32].try_into().unwrap();
        let verifying_key = VerifyingKey::from_bytes(&vk_bytes)
            .map_err(|_| CryptoError::InvalidPreKeyBundle)?;

        self.receiver_states.insert(
            skdm.sender_id.clone(),
            ReceiverEntry { chain_key, iteration: skdm.iteration, verifying_key },
        );
        Ok(())
    }

    /// Encrypt a plaintext for broadcast to the group.
    pub fn encrypt(&mut self, plaintext: &[u8]) -> Result<SenderKeyMessage, CryptoError> {
        self.sender_state.encrypt(plaintext)
    }

    /// Decrypt a group message from a specific sender.
    pub fn decrypt(
        &mut self,
        sender_id: &str,
        msg: &SenderKeyMessage,
    ) -> Result<Vec<u8>, CryptoError> {
        let entry = self.receiver_states.get_mut(sender_id).ok_or_else(|| {
            CryptoError::SenderKeyNotFound { group_id: self.group_id.clone() }
        })?;

        let vk = entry.verifying_key;

        // Build a temporary state to decrypt without a full SenderKeyState
        let mut temp_state = super::sender_key::SenderKeyState {
            chain_key: entry.chain_key,
            iteration: entry.iteration,
            signing_key: {
                // We don't have the sender's signing key; use the verifying key path via decrypt
                // Create a dummy signing key — only verifying is used in decrypt path
                use rand::rngs::OsRng;
                ed25519_dalek::SigningKey::generate(&mut OsRng)
            },
        };
        temp_state.chain_key = entry.chain_key;
        temp_state.iteration = entry.iteration;

        let plaintext = temp_state.decrypt(msg, &vk)?;

        // Update stored state
        entry.chain_key = temp_state.chain_key;
        entry.iteration = temp_state.iteration;

        Ok(plaintext)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn group_session_round_trip() {
        let group_id = "group-123";
        let mut alice_session = GroupSession::new(group_id);
        let mut bob_session = GroupSession::new(group_id);

        // Alice distributes her sender key to Bob
        let skdm = alice_session.create_distribution_message("alice");
        bob_session.process_distribution(&skdm).unwrap();

        // Alice sends a group message
        let msg = alice_session.encrypt(b"hello group").unwrap();

        // Bob decrypts it
        let plaintext = bob_session.decrypt("alice", &msg).unwrap();
        assert_eq!(plaintext, b"hello group");
    }
}

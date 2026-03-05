//! Double Ratchet session: encrypt and decrypt messages.
//!
//! Reference: <https://signal.org/docs/specifications/doubleratchet/>

use aes_gcm::{
    aead::{Aead, KeyInit, Payload},
    Aes256Gcm, Key, Nonce,
};
use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret};

use crate::error::CryptoError;

use super::{
    chain::{kdf_ck, kdf_rk},
    state::{RatchetState, SkipKey, MAX_SKIP},
};

/// Header prepended to every encrypted message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageHeader {
    /// Sender's current ratchet public key
    pub dh_pub: [u8; 32],
    /// Previous sending chain length
    pub pn: u32,
    /// Message number in current sending chain
    pub n: u32,
}

/// An encrypted Double Ratchet message (header + ciphertext).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedMessage {
    pub header: MessageHeader,
    /// AES-256-GCM ciphertext (includes 16-byte authentication tag)
    pub ciphertext: Vec<u8>,
}

/// A complete Double Ratchet session wrapping a `RatchetState`.
pub struct Session {
    state: RatchetState,
}

impl Session {
    /// Create for the **initiator** (Alice), using the X3DH shared secret and
    /// Bob's first ratchet public key (his signed prekey public key).
    pub fn new_initiator(shared_secret: &[u8; 32], bob_spk_pub: X25519PublicKey) -> Self {
        Self { state: RatchetState::init_sender(shared_secret, bob_spk_pub) }
    }

    /// Create for the **responder** (Bob), using the X3DH shared secret and
    /// his own signed prekey secret (which becomes the initial ratchet key).
    pub fn new_responder(shared_secret: &[u8; 32], our_ratchet_secret: StaticSecret) -> Self {
        Self { state: RatchetState::init_receiver(shared_secret, our_ratchet_secret) }
    }

    /// Encrypt `plaintext` with optional associated data.
    pub fn encrypt(&mut self, plaintext: &[u8], associated_data: &[u8]) -> Result<EncryptedMessage, CryptoError> {
        let (new_cks, mk) = kdf_ck(self.state.cks.as_ref().ok_or(CryptoError::NoSession)?);
        self.state.cks = Some(new_cks);

        let header = MessageHeader {
            dh_pub: X25519PublicKey::from(&self.state.dhs_secret).to_bytes(),
            pn: self.state.pn,
            n: self.state.ns,
        };
        self.state.ns += 1;

        let ciphertext = aes_gcm_encrypt(&mk, &header_bytes(&header), plaintext, associated_data)?;

        Ok(EncryptedMessage { header, ciphertext })
    }

    /// Decrypt an `EncryptedMessage`. Handles out-of-order delivery by
    /// buffering skipped message keys (up to MAX_SKIP).
    pub fn decrypt(&mut self, msg: &EncryptedMessage, associated_data: &[u8]) -> Result<Vec<u8>, CryptoError> {
        let header = &msg.header;
        let ad = associated_data;

        // Try skipped keys first
        let skip_key = SkipKey { dhr_pub: header.dh_pub, n: header.n };
        if let Some(mk) = self.state.take_skipped(&skip_key) {
            return aes_gcm_decrypt(&mk, &header_bytes(header), &msg.ciphertext, ad);
        }

        let their_dh = X25519PublicKey::from(header.dh_pub);

        // Check if we need a DH ratchet step
        let need_dh_step = self
            .state
            .dhr_pub
            .as_ref()
            .map(|dhr| dhr.as_bytes() != &header.dh_pub)
            .unwrap_or(true);

        if need_dh_step {
            // Skip remaining messages in current receiving chain
            self.skip_message_keys(header.pn)?;
            // Perform DH ratchet step
            self.dh_ratchet(their_dh)?;
        }

        // Skip any skipped messages in the new chain
        self.skip_message_keys(header.n)?;

        // Derive this message's key
        let (new_ckr, mk) = kdf_ck(self.state.ckr.as_ref().ok_or(CryptoError::NoSession)?);
        self.state.ckr = Some(new_ckr);
        self.state.nr += 1;

        aes_gcm_decrypt(&mk, &header_bytes(header), &msg.ciphertext, ad)
    }

    fn skip_message_keys(&mut self, until: u32) -> Result<(), CryptoError> {
        if self.state.nr + (MAX_SKIP as u32) < until {
            return Err(CryptoError::SkippedMessageCacheFull);
        }
        if let Some(mut ckr) = self.state.ckr {
            while self.state.nr < until {
                let (new_ckr, mk) = kdf_ck(&ckr);
                ckr = new_ckr;
                let key = SkipKey { dhr_pub: self.state.dhr_pub.unwrap().to_bytes(), n: self.state.nr };
                self.state.store_skipped(key, mk);
                self.state.nr += 1;
            }
            self.state.ckr = Some(ckr);
        }
        Ok(())
    }

    fn dh_ratchet(&mut self, their_dh: X25519PublicKey) -> Result<(), CryptoError> {
        self.state.pn = self.state.ns;
        self.state.ns = 0;
        self.state.nr = 0;
        self.state.dhr_pub = Some(their_dh);

        // Receiving chain
        let dh_out = self.state.dhs_secret.diffie_hellman(&their_dh);
        let (new_rk, new_ckr) = kdf_rk(&self.state.root_key, dh_out.as_bytes())?;
        self.state.root_key = new_rk;
        self.state.ckr = Some(new_ckr);

        // New sending key pair
        self.state.dhs_secret = StaticSecret::random_from_rng(OsRng);
        let dh_out2 = self.state.dhs_secret.diffie_hellman(&their_dh);
        let (new_rk2, new_cks) = kdf_rk(&self.state.root_key, dh_out2.as_bytes())?;
        self.state.root_key = new_rk2;
        self.state.cks = Some(new_cks);

        Ok(())
    }
}

fn header_bytes(h: &MessageHeader) -> Vec<u8> {
    let mut b = Vec::with_capacity(32 + 4 + 4);
    b.extend_from_slice(&h.dh_pub);
    b.extend_from_slice(&h.pn.to_le_bytes());
    b.extend_from_slice(&h.n.to_le_bytes());
    b
}

fn aes_gcm_encrypt(mk: &[u8; 48], header: &[u8], plaintext: &[u8], ad: &[u8]) -> Result<Vec<u8>, CryptoError> {
    let key = Key::<Aes256Gcm>::from_slice(&mk[..32]);
    let nonce = Nonce::from_slice(&mk[32..44]);
    let cipher = Aes256Gcm::new(key);

    let mut combined_ad = header.to_vec();
    combined_ad.extend_from_slice(ad);

    cipher
        .encrypt(nonce, Payload { msg: plaintext, aad: &combined_ad })
        .map_err(|_| CryptoError::DecryptionFailed)
}

fn aes_gcm_decrypt(mk: &[u8; 48], header: &[u8], ciphertext: &[u8], ad: &[u8]) -> Result<Vec<u8>, CryptoError> {
    let key = Key::<Aes256Gcm>::from_slice(&mk[..32]);
    let nonce = Nonce::from_slice(&mk[32..44]);
    let cipher = Aes256Gcm::new(key);

    let mut combined_ad = header.to_vec();
    combined_ad.extend_from_slice(ad);

    cipher
        .decrypt(nonce, Payload { msg: ciphertext, aad: &combined_ad })
        .map_err(|_| CryptoError::DecryptionFailed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::x3dh::{
        handshake::{initiate, respond},
        identity_key::IdentityKeyPair,
        key_bundle::PreKeyBundle,
        one_time_prekey::OneTimePreKey,
        signed_prekey::SignedPreKey,
    };

    fn make_sessions() -> (Session, Session) {
        let alice_ik = IdentityKeyPair::generate();
        let bob_ik = IdentityKeyPair::generate();
        let bob_spk = SignedPreKey::generate(1);
        let bob_opk = OneTimePreKey::generate(1);

        let bundle = PreKeyBundle {
            user_id: "bob".into(),
            identity_key: bob_ik.to_public(),
            signed_prekey: bob_spk.to_public(&bob_ik),
            one_time_prekey: Some(bob_opk.to_public()),
        };

        let (alice_sk, init_msg) = initiate(&alice_ik, &bundle).unwrap();
        let bob_sk = respond(&bob_ik, &bob_spk, Some(&bob_opk), &init_msg).unwrap();

        let bob_ratchet_pub = X25519PublicKey::from(bob_spk.public_key().to_bytes());
        let bob_ratchet_secret = StaticSecret::from(bob_spk.secret.to_bytes());

        let alice = Session::new_initiator(&alice_sk, bob_ratchet_pub);
        let bob = Session::new_responder(&bob_sk, bob_ratchet_secret);

        (alice, bob)
    }

    #[test]
    fn sequential_encrypt_decrypt() {
        let (mut alice, mut bob) = make_sessions();
        let ad = b"session-id-1234";

        for i in 0..10u32 {
            let pt = format!("message {i}");
            let enc = alice.encrypt(pt.as_bytes(), ad).unwrap();
            let dec = bob.decrypt(&enc, ad).unwrap();
            assert_eq!(dec, pt.as_bytes());
        }
    }

    #[test]
    fn bidirectional_messages() {
        let (mut alice, mut bob) = make_sessions();
        let ad = b"test";

        let e1 = alice.encrypt(b"hello from alice", ad).unwrap();
        let d1 = bob.decrypt(&e1, ad).unwrap();
        assert_eq!(d1, b"hello from alice");

        let e2 = bob.encrypt(b"hello from bob", ad).unwrap();
        let d2 = alice.decrypt(&e2, ad).unwrap();
        assert_eq!(d2, b"hello from bob");
    }

    #[test]
    fn out_of_order_messages() {
        let (mut alice, mut bob) = make_sessions();
        let ad = b"ooo";

        let e1 = alice.encrypt(b"msg 1", ad).unwrap();
        let e2 = alice.encrypt(b"msg 2", ad).unwrap();
        let e3 = alice.encrypt(b"msg 3", ad).unwrap();

        // Deliver out of order: 3, 1, 2
        let d3 = bob.decrypt(&e3, ad).unwrap();
        let d1 = bob.decrypt(&e1, ad).unwrap();
        let d2 = bob.decrypt(&e2, ad).unwrap();

        assert_eq!(d1, b"msg 1");
        assert_eq!(d2, b"msg 2");
        assert_eq!(d3, b"msg 3");
    }

    #[test]
    fn message_keys_are_unique() {
        let (mut alice, _bob) = make_sessions();
        let ad = b"unique";

        let e1 = alice.encrypt(b"a", ad).unwrap();
        let e2 = alice.encrypt(b"b", ad).unwrap();

        assert_ne!(e1.ciphertext, e2.ciphertext, "same plaintext length but different keys");
    }

    #[test]
    fn wrong_ad_rejected() {
        let (mut alice, mut bob) = make_sessions();

        let enc = alice.encrypt(b"secret", b"correct-ad").unwrap();
        assert!(bob.decrypt(&enc, b"wrong-ad").is_err());
    }
}

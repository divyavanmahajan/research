use std::collections::HashMap;

use serde::{Deserialize, Serialize};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret};
use zeroize::ZeroizeOnDrop;

/// Maximum number of skipped message keys stored per session.
/// Exceeding this cap drops the oldest entry (FIFO eviction).
pub const MAX_SKIP: usize = 2000;

/// Key used to look up a skipped message key.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SkipKey {
    /// Remote ratchet public key (bytes)
    pub dhr_pub: [u8; 32],
    /// Message counter in that chain
    pub n: u32,
}

/// Serialisable Double Ratchet session state.
///
/// The private ratchet key (`dhs_secret`) is stored as raw bytes and should
/// be kept in encrypted storage by the caller.
#[derive(ZeroizeOnDrop)]
pub struct RatchetState {
    /// Sending ratchet key pair secret
    pub dhs_secret: StaticSecret,
    /// Remote ratchet public key (None until first message received)
    pub dhr_pub: Option<X25519PublicKey>,
    /// Root key
    pub root_key: [u8; 32],
    /// Sending chain key
    pub cks: Option<[u8; 32]>,
    /// Receiving chain key
    pub ckr: Option<[u8; 32]>,
    /// Send message counter
    pub ns: u32,
    /// Receive message counter
    pub nr: u32,
    /// Previous sending chain message count
    pub pn: u32,
    /// Skipped message keys (capped at MAX_SKIP)
    #[zeroize(skip)]
    pub mkskipped: HashMap<SkipKey, [u8; 48]>,
    /// Insertion-order tracking for FIFO eviction
    #[zeroize(skip)]
    pub skip_order: Vec<SkipKey>,
}

impl RatchetState {
    /// Initialise state for the **sender** (initiator) side.
    pub fn init_sender(shared_secret: &[u8; 32], bob_ratchet_pub: X25519PublicKey) -> Self {
        use rand::rngs::OsRng;
        use super::chain::kdf_rk;

        let dhs_secret = StaticSecret::random_from_rng(OsRng);
        let dh_out = dhs_secret.diffie_hellman(&bob_ratchet_pub);
        let (root_key, cks) = kdf_rk(shared_secret, dh_out.as_bytes()).unwrap();

        Self {
            dhs_secret,
            dhr_pub: Some(bob_ratchet_pub),
            root_key,
            cks: Some(cks),
            ckr: None,
            ns: 0,
            nr: 0,
            pn: 0,
            mkskipped: HashMap::new(),
            skip_order: Vec::new(),
        }
    }

    /// Initialise state for the **receiver** (responder) side.
    pub fn init_receiver(shared_secret: &[u8; 32], our_ratchet_secret: StaticSecret) -> Self {
        Self {
            dhs_secret: our_ratchet_secret,
            dhr_pub: None,
            root_key: *shared_secret,
            cks: None,
            ckr: None,
            ns: 0,
            nr: 0,
            pn: 0,
            mkskipped: HashMap::new(),
            skip_order: Vec::new(),
        }
    }

    /// Store a skipped message key, enforcing the MAX_SKIP cap (FIFO eviction).
    pub fn store_skipped(&mut self, key: SkipKey, mk: [u8; 48]) {
        if self.mkskipped.len() >= MAX_SKIP {
            if let Some(oldest) = self.skip_order.first().cloned() {
                self.skip_order.remove(0);
                self.mkskipped.remove(&oldest);
            }
        }
        self.skip_order.push(key.clone());
        self.mkskipped.insert(key, mk);
    }

    pub fn take_skipped(&mut self, key: &SkipKey) -> Option<[u8; 48]> {
        if let Some(mk) = self.mkskipped.remove(key) {
            self.skip_order.retain(|k| k != key);
            Some(mk)
        } else {
            None
        }
    }
}

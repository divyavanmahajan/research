//! X3DH key agreement.
//!
//! Reference: <https://signal.org/docs/specifications/x3dh/>
//!
//! Key agreement produces a 32-byte shared secret `SK` and an `InitMessage`
//! that the initiator sends to the responder so they can reconstruct the same
//! secret without the initiator's ephemeral private key.

use hkdf::Hkdf;
use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret};

use crate::error::CryptoError;

use super::{
    identity_key::{IdentityKeyPair, IdentityKeyPublic},
    key_bundle::PreKeyBundle,
    signed_prekey::SignedPreKey,
    one_time_prekey::OneTimePreKey,
};

const X3DH_INFO: &[u8] = b"WhatsUp_X3DH_v1";
/// Domain separator: 32 bytes of 0xFF, prepended before DH outputs in HKDF.
const DOMAIN_SEP: [u8; 32] = [0xFF; 32];

pub type SharedSecret = [u8; 32];

/// Message sent by the initiator to the responder so they can derive the same SK.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InitMessage {
    /// Initiator's identity public key
    pub ik_public: IdentityKeyPublic,
    /// Initiator's ephemeral public key
    pub ek_public: [u8; 32],
    /// Which signed prekey was used
    pub spk_id: u32,
    /// Which one-time prekey was used (if any)
    pub opk_id: Option<u32>,
}

/// Perform X3DH as the **initiator** (Alice).
///
/// Returns `(shared_secret, init_message)`.
pub fn initiate(
    alice_ik: &IdentityKeyPair,
    bob_bundle: &PreKeyBundle,
) -> Result<(SharedSecret, InitMessage), CryptoError> {
    // Verify the signed prekey signature
    let spk_pub = &bob_bundle.signed_prekey;
    bob_bundle.identity_key.verify(&spk_pub.public_key, &spk_pub.signature)?;

    // Generate ephemeral key
    let ek_secret = StaticSecret::random_from_rng(OsRng);
    let ek_public = X25519PublicKey::from(&ek_secret);

    let bob_ik_dh = bob_bundle.identity_key.dh_public_key();
    let bob_spk = spk_pub.x25519_public();

    // DH1 = DH(IK_A, SPK_B)
    let dh1 = alice_ik.dh_secret.diffie_hellman(&bob_spk);
    // DH2 = DH(EK_A, IK_B)
    let dh2 = ek_secret.diffie_hellman(&bob_ik_dh);
    // DH3 = DH(EK_A, SPK_B)
    let dh3 = ek_secret.diffie_hellman(&bob_spk);

    let mut ikm = Vec::with_capacity(32 + 32 * 3 + 32);
    ikm.extend_from_slice(&DOMAIN_SEP);
    ikm.extend_from_slice(dh1.as_bytes());
    ikm.extend_from_slice(dh2.as_bytes());
    ikm.extend_from_slice(dh3.as_bytes());

    let opk_id = if let Some(opk) = &bob_bundle.one_time_prekey {
        // DH4 = DH(EK_A, OPK_B)
        let dh4 = ek_secret.diffie_hellman(&opk.x25519_public());
        ikm.extend_from_slice(dh4.as_bytes());
        Some(opk.id)
    } else {
        None
    };

    let sk = hkdf_extract_expand(&ikm)?;

    let init_msg = InitMessage {
        ik_public: alice_ik.to_public(),
        ek_public: ek_public.to_bytes(),
        spk_id: spk_pub.id,
        opk_id,
    };

    Ok((sk, init_msg))
}

/// Perform X3DH as the **responder** (Bob).
///
/// Bob reconstructs the same shared secret from the `InitMessage` and his
/// private keys. The matching OPK is identified by `opk_id`; after calling
/// this function the caller **must** delete the used OPK private key.
pub fn respond(
    bob_ik: &IdentityKeyPair,
    bob_spk: &SignedPreKey,
    bob_opk: Option<&OneTimePreKey>,
    init_msg: &InitMessage,
) -> Result<SharedSecret, CryptoError> {
    let alice_ik_dh = init_msg.ik_public.dh_public_key();
    let alice_ek = X25519PublicKey::from(init_msg.ek_public);

    // DH1 = DH(SPK_B, IK_A)
    let dh1 = bob_spk.secret.diffie_hellman(&alice_ik_dh);
    // DH2 = DH(IK_B, EK_A)
    let dh2 = bob_ik.dh_secret.diffie_hellman(&alice_ek);
    // DH3 = DH(SPK_B, EK_A)
    let dh3 = bob_spk.secret.diffie_hellman(&alice_ek);

    let mut ikm = Vec::with_capacity(32 + 32 * 3 + 32);
    ikm.extend_from_slice(&DOMAIN_SEP);
    ikm.extend_from_slice(dh1.as_bytes());
    ikm.extend_from_slice(dh2.as_bytes());
    ikm.extend_from_slice(dh3.as_bytes());

    if let Some(opk) = bob_opk {
        // DH4 = DH(OPK_B, EK_A)
        let dh4 = opk.secret.diffie_hellman(&alice_ek);
        ikm.extend_from_slice(dh4.as_bytes());
    }

    hkdf_extract_expand(&ikm)
}

fn hkdf_extract_expand(ikm: &[u8]) -> Result<SharedSecret, CryptoError> {
    let hk = Hkdf::<Sha256>::new(None, ikm);
    let mut sk = [0u8; 32];
    hk.expand(X3DH_INFO, &mut sk)
        .map_err(|e| CryptoError::Serialization(e.to_string()))?;
    Ok(sk)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::x3dh::{
        identity_key::IdentityKeyPair,
        key_bundle::PreKeyBundle,
        one_time_prekey::OneTimePreKey,
        signed_prekey::SignedPreKey,
    };

    #[test]
    fn x3dh_round_trip_with_opk() {
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

        assert_eq!(alice_sk, bob_sk, "shared secrets must match");
    }

    #[test]
    fn x3dh_round_trip_without_opk() {
        let alice_ik = IdentityKeyPair::generate();
        let bob_ik = IdentityKeyPair::generate();
        let bob_spk = SignedPreKey::generate(1);

        let bundle = PreKeyBundle {
            user_id: "bob".into(),
            identity_key: bob_ik.to_public(),
            signed_prekey: bob_spk.to_public(&bob_ik),
            one_time_prekey: None,
        };

        let (alice_sk, init_msg) = initiate(&alice_ik, &bundle).unwrap();
        let bob_sk = respond(&bob_ik, &bob_spk, None, &init_msg).unwrap();

        assert_eq!(alice_sk, bob_sk);
    }

    #[test]
    fn x3dh_tampered_spk_signature_rejected() {
        let alice_ik = IdentityKeyPair::generate();
        let bob_ik = IdentityKeyPair::generate();
        let bob_spk = SignedPreKey::generate(1);

        let mut bad_bundle = PreKeyBundle {
            user_id: "bob".into(),
            identity_key: bob_ik.to_public(),
            signed_prekey: bob_spk.to_public(&bob_ik),
            one_time_prekey: None,
        };
        // Corrupt the signature
        bad_bundle.signed_prekey.signature[0] ^= 0xFF;

        assert!(initiate(&alice_ik, &bad_bundle).is_err());
    }
}

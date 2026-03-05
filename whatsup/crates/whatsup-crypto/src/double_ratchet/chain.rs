//! KDF chain functions for the Double Ratchet Algorithm.
//!
//! Reference: <https://signal.org/docs/specifications/doubleratchet/>

use hkdf::Hkdf;
use hmac::{Hmac, Mac};
use sha2::Sha256;

use crate::error::CryptoError;

type HmacSha256 = Hmac<Sha256>;

pub const ROOT_KDF_INFO: &[u8] = b"WhatsUp_RootKDF_v1";
pub const CHAIN_KDF_CONST_CK: u8 = 0x01;
pub const CHAIN_KDF_CONST_MK: u8 = 0x02;

/// KDF_RK — derive a new root key and chain key from the current root key
/// and a Diffie-Hellman output.
///
/// Returns `(new_root_key, new_chain_key)`.
pub fn kdf_rk(root_key: &[u8; 32], dh_output: &[u8; 32]) -> Result<([u8; 32], [u8; 32]), CryptoError> {
    let hk = Hkdf::<Sha256>::new(Some(root_key), dh_output);
    let mut out = [0u8; 64];
    hk.expand(ROOT_KDF_INFO, &mut out)
        .map_err(|e| CryptoError::Serialization(e.to_string()))?;
    let mut new_rk = [0u8; 32];
    let mut new_ck = [0u8; 32];
    new_rk.copy_from_slice(&out[..32]);
    new_ck.copy_from_slice(&out[32..]);
    Ok((new_rk, new_ck))
}

/// KDF_CK — advance a chain key and derive a message key.
///
/// Returns `(new_chain_key, message_key)`.
pub fn kdf_ck(chain_key: &[u8; 32]) -> ([u8; 32], [u8; 48]) {
    // new_ck = HMAC-SHA256(chain_key, 0x01)
    let mut mac = HmacSha256::new_from_slice(chain_key).expect("HMAC accepts any key size");
    mac.update(&[CHAIN_KDF_CONST_CK]);
    let new_ck_bytes = mac.finalize().into_bytes();

    // mk = HMAC-SHA256(chain_key, 0x02)
    let mut mac = HmacSha256::new_from_slice(chain_key).expect("HMAC accepts any key size");
    mac.update(&[CHAIN_KDF_CONST_MK]);
    let mk_bytes = mac.finalize().into_bytes();

    let mut new_ck = [0u8; 32];
    new_ck.copy_from_slice(&new_ck_bytes);

    // Message key is 48 bytes: 32-byte AES key + 12-byte GCM nonce + 4 padding
    let mut mk = [0u8; 48];
    mk.copy_from_slice(&mk_bytes[..48.min(mk_bytes.len())]);
    // Expand to 48 bytes via HKDF for proper nonce derivation
    let hk = Hkdf::<Sha256>::new(None, &mk_bytes);
    hk.expand(b"WhatsUp_MsgKey_v1", &mut mk).expect("48 bytes is a valid HKDF output length");

    (new_ck, mk)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kdf_ck_produces_different_keys_each_step() {
        let ck0 = [0u8; 32];
        let (ck1, mk1) = kdf_ck(&ck0);
        let (ck2, mk2) = kdf_ck(&ck1);

        assert_ne!(ck1, ck0, "chain key must advance");
        assert_ne!(ck2, ck1, "chain key must keep advancing");
        assert_ne!(mk1, mk2, "message keys must differ per step");
    }

    #[test]
    fn kdf_rk_deterministic() {
        let rk = [1u8; 32];
        let dh = [2u8; 32];
        let (new_rk1, ck1) = kdf_rk(&rk, &dh).unwrap();
        let (new_rk2, ck2) = kdf_rk(&rk, &dh).unwrap();
        assert_eq!(new_rk1, new_rk2);
        assert_eq!(ck1, ck2);
    }
}

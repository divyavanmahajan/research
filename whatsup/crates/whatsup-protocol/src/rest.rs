use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// ── Auth ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct RegisterRequest {
    pub username: String,
    pub password: String,
    pub display_name: String,
    pub phone_number: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(untagged)]
pub enum LoginResponse {
    Success(AuthTokens),
    TwoFactorRequired { status: String, challenge_token: String },
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AuthTokens {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_in: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RefreshRequest {
    pub refresh_token: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TwoFaChallengeRequest {
    pub challenge_token: String,
    pub otp_code: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TwoFaSetupResponse {
    pub otpauth_uri: String,
    pub qr_code_base64: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TwoFaVerifyRequest {
    pub otp_code: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TwoFaDisableRequest {
    pub password: String,
    pub otp_code: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackupCodesResponse {
    /// Plaintext codes — shown once at setup, never stored unencrypted
    pub codes: Vec<String>,
}

// ── Users ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserProfile {
    pub id: String,
    pub username: String,
    pub display_name: String,
    pub avatar_url: Option<String>,
    pub last_seen_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateProfileRequest {
    pub display_name: Option<String>,
    pub avatar_url: Option<String>,
}

// ── Key Bundles ──────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct UploadKeyBundleRequest {
    /// Base64-encoded X25519 public key
    pub ik_public: String,
    /// Base64-encoded Ed25519 public key
    pub ik_public_ed: String,
    pub spk_id: u32,
    /// Base64-encoded X25519 public key
    pub spk_public: String,
    /// Base64-encoded Ed25519 signature
    pub spk_signature: String,
    pub one_time_prekeys: Vec<OtpkUpload>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OtpkUpload {
    pub id: u32,
    /// Base64-encoded X25519 public key
    pub public_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct KeyBundleResponse {
    pub user_id: String,
    pub ik_public: String,
    pub ik_public_ed: String,
    pub spk_id: u32,
    pub spk_public: String,
    pub spk_signature: String,
    pub opk_id: Option<u32>,
    pub opk_public: Option<String>,
}

// ── Messages ─────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct SendMessageRequest {
    pub message_id: String,
    pub kind: String,
    pub to: String,
    pub ciphertext: String,
    pub message_type: String,
    pub file_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageRecord {
    pub id: String,
    pub from_user_id: String,
    pub ciphertext: String,
    pub message_type: String,
    pub file_id: Option<String>,
    pub sent_at: DateTime<Utc>,
    pub delivered_at: Option<DateTime<Utc>>,
    pub read_at: Option<DateTime<Utc>>,
}

// ── Groups ───────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateGroupRequest {
    pub name: String,
    pub member_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupInfo {
    pub id: String,
    pub name: String,
    pub avatar_url: Option<String>,
    pub created_by: String,
    pub created_at: DateTime<Utc>,
    pub members: Vec<GroupMember>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupMember {
    pub user_id: String,
    pub role: String,
    pub joined_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AddMemberRequest {
    pub user_id: String,
}

// ── Files ────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct UploadFileResponse {
    pub file_id: String,
}

// ── WS Ticket ────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct WsTicketResponse {
    pub ticket: String,
}

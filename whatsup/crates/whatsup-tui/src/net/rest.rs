use anyhow::{anyhow, Result};
use reqwest::Client;
use serde_json::Value;

use whatsup_protocol::rest::{AuthTokens, LoginRequest, LoginResponse, RegisterRequest};

pub struct RestClient {
    pub base_url: String,
    pub client: Client,
    pub token: Option<String>,
}

impl RestClient {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            client: Client::new(),
            token: None,
        }
    }

    pub async fn register(&self, username: &str, password: &str, display_name: &str) -> Result<Value> {
        let resp = self
            .client
            .post(format!("{}/api/v1/auth/register", self.base_url))
            .json(&RegisterRequest {
                username: username.into(),
                password: password.into(),
                display_name: display_name.into(),
                phone_number: None,
            })
            .send()
            .await?
            .json::<Value>()
            .await?;
        Ok(resp)
    }

    pub async fn login(&self, username: &str, password: &str) -> Result<LoginResponse> {
        let resp = self
            .client
            .post(format!("{}/api/v1/auth/login", self.base_url))
            .json(&LoginRequest {
                username: username.into(),
                password: password.into(),
            })
            .send()
            .await?;

        let status = resp.status();
        let body: Value = resp.json().await?;

        if body.get("status").and_then(|s| s.as_str()) == Some("2fa_required") {
            Ok(LoginResponse::TwoFactorRequired {
                status: "2fa_required".into(),
                challenge_token: body["challenge_token"].as_str().unwrap_or("").into(),
            })
        } else if status.is_success() {
            Ok(LoginResponse::Success(AuthTokens {
                access_token: body["access_token"].as_str().unwrap_or("").into(),
                refresh_token: body["refresh_token"].as_str().unwrap_or("").into(),
                expires_in: body["expires_in"].as_u64().unwrap_or(900),
            }))
        } else {
            Err(anyhow!("{}", body["error"].as_str().unwrap_or("login failed")))
        }
    }

    pub async fn two_fa_challenge(&self, challenge_token: &str, otp_code: &str) -> Result<AuthTokens> {
        let resp = self
            .client
            .post(format!("{}/api/v1/auth/2fa/challenge", self.base_url))
            .json(&whatsup_protocol::rest::TwoFaChallengeRequest {
                challenge_token: challenge_token.into(),
                otp_code: otp_code.into(),
            })
            .send()
            .await?
            .json::<Value>()
            .await?;

        Ok(AuthTokens {
            access_token: resp["access_token"].as_str().unwrap_or("").into(),
            refresh_token: resp["refresh_token"].as_str().unwrap_or("").into(),
            expires_in: resp["expires_in"].as_u64().unwrap_or(900),
        })
    }

    pub async fn get_ws_ticket(&self) -> Result<String> {
        let token = self.token.as_ref().ok_or_else(|| anyhow!("not logged in"))?;
        let resp = self
            .client
            .post(format!("{}/api/v1/auth/ws-ticket", self.base_url))
            .bearer_auth(token)
            .send()
            .await?
            .json::<Value>()
            .await?;
        Ok(resp["ticket"].as_str().unwrap_or("").into())
    }
}

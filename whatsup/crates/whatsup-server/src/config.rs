use anyhow::{Context, Result};
use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub database_path: String,
    pub jwt_secret: Vec<u8>,
    pub totp_encryption_key: Vec<u8>,
    pub cors_origin: String,
    pub upload_dir: String,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        dotenvy::dotenv().ok();

        let jwt_hex = env::var("JWT_SECRET").context("JWT_SECRET must be set")?;
        let jwt_secret = hex::decode(&jwt_hex)
            .map_err(|e| anyhow::anyhow!("JWT_SECRET must be valid hex: {}", e))?;
        if jwt_secret.len() < 32 {
            anyhow::bail!("JWT_SECRET must be at least 32 bytes (64 hex chars)");
        }

        let totp_hex =
            env::var("TOTP_ENCRYPTION_KEY").context("TOTP_ENCRYPTION_KEY must be set")?;
        let totp_encryption_key = hex::decode(&totp_hex)
            .map_err(|e| anyhow::anyhow!("TOTP_ENCRYPTION_KEY must be valid hex: {}", e))?;
        if totp_encryption_key.len() < 32 {
            anyhow::bail!("TOTP_ENCRYPTION_KEY must be at least 32 bytes");
        }

        Ok(Self {
            host: env::var("HOST").unwrap_or_else(|_| "127.0.0.1".into()),
            port: env::var("PORT")
                .unwrap_or_else(|_| "3000".into())
                .parse()
                .context("PORT must be a number")?,
            database_path: env::var("DATABASE_PATH").unwrap_or_else(|_| "./whatsup.db".into()),
            jwt_secret,
            totp_encryption_key,
            cors_origin: env::var("CORS_ORIGIN")
                .unwrap_or_else(|_| "http://localhost:5173".into()),
            upload_dir: env::var("UPLOAD_DIR").unwrap_or_else(|_| "./uploads".into()),
        })
    }
}

// We add a simple hex module rather than pulling in a full crate
mod hex {
    pub fn decode(s: &str) -> Result<Vec<u8>, String> {
        if s.len() % 2 != 0 {
            return Err("odd hex length".into());
        }
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|e| e.to_string()))
            .collect()
    }
}

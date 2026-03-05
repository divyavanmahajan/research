use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::{fs, path::PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub server_url: String,
    pub username: Option<String>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            server_url: "http://localhost:3000".into(),
            username: None,
        }
    }
}

impl Config {
    pub fn config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("whatsup")
            .join("config.toml")
    }

    pub fn load() -> Result<Self> {
        let path = Self::config_path();
        if path.exists() {
            let s = fs::read_to_string(&path)?;
            Ok(toml::from_str(&s)?)
        } else {
            Ok(Self::default())
        }
    }

    pub fn save(&self) -> Result<()> {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, toml::to_string(self)?)?;
        Ok(())
    }

    pub fn ws_url(&self) -> String {
        self.server_url
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            + "/ws"
    }
}

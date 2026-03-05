use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq)]
pub enum AppScreen {
    Login,
    TwoFaChallenge { challenge_token: String },
    Chat,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conversation {
    pub id: String,
    pub display_name: String,
    pub last_message: Option<String>,
    pub last_at: Option<DateTime<Utc>>,
    pub unread: usize,
    pub is_group: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub id: String,
    pub from_user_id: String,
    pub plaintext: String,
    pub sent_at: DateTime<Utc>,
    pub delivered: bool,
    pub read: bool,
    pub is_own: bool,
}

pub struct AppState {
    pub screen: AppScreen,
    pub current_user_id: Option<String>,
    pub current_username: Option<String>,
    pub access_token: Option<String>,
    pub conversations: Vec<Conversation>,
    pub selected_conversation: Option<usize>,
    pub messages: Vec<ChatMessage>,
    pub input: String,
    pub cursor: usize,
    pub status: String,
    pub is_connected: bool,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            screen: AppScreen::Login,
            current_user_id: None,
            current_username: None,
            access_token: None,
            conversations: Vec::new(),
            selected_conversation: None,
            messages: Vec::new(),
            input: String::new(),
            cursor: 0,
            status: "Not connected".to_string(),
            is_connected: false,
        }
    }
}

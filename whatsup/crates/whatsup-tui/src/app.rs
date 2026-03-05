use anyhow::Result;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::{io, time::Duration};

use crate::{
    config::Config,
    net::rest::RestClient,
    state::{AppScreen, AppState},
    ui,
};
use whatsup_protocol::rest::LoginResponse;

pub struct App {
    config: Config,
    state: AppState,
    rest: RestClient,
    // Login form fields
    username_input: String,
    password_input: String,
    otp_input: String,
    active_field: u8, // 0=username, 1=password, 2=otp
    challenge_token: Option<String>,
}

impl App {
    pub async fn new(config: Config) -> Result<Self> {
        let rest = RestClient::new(&config.server_url);
        Ok(Self {
            config,
            state: AppState::default(),
            rest,
            username_input: String::new(),
            password_input: String::new(),
            otp_input: String::new(),
            active_field: 0,
            challenge_token: None,
        })
    }

    pub async fn run(&mut self) -> Result<()> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        loop {
            // Update displayed input based on active field
            self.state.input = match self.state.screen {
                AppScreen::Login => match self.active_field {
                    0 => format!("Username: {}", self.username_input),
                    1 => format!("Password: {}", "*".repeat(self.password_input.len())),
                    _ => String::new(),
                },
                AppScreen::TwoFaChallenge { .. } => {
                    format!("OTP Code: {}", self.otp_input)
                }
                AppScreen::Chat => self.state.input.clone(),
            };

            terminal.draw(|f| ui::draw(f, &self.state))?;

            if event::poll(Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
                        break;
                    }
                    if let Err(e) = self.handle_key(key.code).await {
                        self.state.status = format!("Error: {e}");
                    }
                }
            }
        }

        disable_raw_mode()?;
        execute!(
            terminal.backend_mut(),
            LeaveAlternateScreen,
            DisableMouseCapture
        )?;
        terminal.show_cursor()?;
        Ok(())
    }

    async fn handle_key(&mut self, key: KeyCode) -> Result<()> {
        match &self.state.screen.clone() {
            AppScreen::Login => self.handle_login_key(key).await?,
            AppScreen::TwoFaChallenge { challenge_token } => {
                self.handle_2fa_key(key, challenge_token.clone()).await?
            }
            AppScreen::Chat => self.handle_chat_key(key).await?,
        }
        Ok(())
    }

    async fn handle_login_key(&mut self, key: KeyCode) -> Result<()> {
        match key {
            KeyCode::Tab => {
                self.active_field = (self.active_field + 1) % 2;
            }
            KeyCode::Char(c) => match self.active_field {
                0 => self.username_input.push(c),
                1 => self.password_input.push(c),
                _ => {}
            },
            KeyCode::Backspace => match self.active_field {
                0 => { self.username_input.pop(); }
                1 => { self.password_input.pop(); }
                _ => {}
            },
            KeyCode::Enter => {
                self.state.status = "Logging in...".into();
                match self.rest.login(&self.username_input, &self.password_input).await {
                    Ok(LoginResponse::Success(tokens)) => {
                        self.rest.token = Some(tokens.access_token.clone());
                        self.state.access_token = Some(tokens.access_token);
                        self.state.current_username = Some(self.username_input.clone());
                        self.state.screen = AppScreen::Chat;
                        self.state.status = "Connected".into();
                        self.state.is_connected = true;
                    }
                    Ok(LoginResponse::TwoFactorRequired { challenge_token, .. }) => {
                        self.challenge_token = Some(challenge_token.clone());
                        self.state.screen = AppScreen::TwoFaChallenge { challenge_token };
                        self.state.status = "Enter your 2FA code".into();
                    }
                    Err(e) => {
                        self.state.status = format!("Login failed: {e}");
                    }
                }
            }
            _ => {}
        }
        Ok(())
    }

    async fn handle_2fa_key(&mut self, key: KeyCode, challenge_token: String) -> Result<()> {
        match key {
            KeyCode::Char(c) => self.otp_input.push(c),
            KeyCode::Backspace => { self.otp_input.pop(); }
            KeyCode::Esc => {
                self.state.screen = AppScreen::Login;
                self.otp_input.clear();
            }
            KeyCode::Enter => {
                match self.rest.two_fa_challenge(&challenge_token, &self.otp_input).await {
                    Ok(tokens) => {
                        self.rest.token = Some(tokens.access_token.clone());
                        self.state.access_token = Some(tokens.access_token);
                        self.state.current_username = Some(self.username_input.clone());
                        self.state.screen = AppScreen::Chat;
                        self.state.status = "Connected".into();
                        self.state.is_connected = true;
                    }
                    Err(e) => {
                        self.state.status = format!("2FA failed: {e}");
                    }
                }
            }
            _ => {}
        }
        Ok(())
    }

    async fn handle_chat_key(&mut self, key: KeyCode) -> Result<()> {
        match key {
            KeyCode::Char(c) => self.state.input.push(c),
            KeyCode::Backspace => { self.state.input.pop(); }
            KeyCode::Up => {
                if let Some(i) = self.state.selected_conversation {
                    if i > 0 {
                        self.state.selected_conversation = Some(i - 1);
                    }
                } else if !self.state.conversations.is_empty() {
                    self.state.selected_conversation = Some(0);
                }
            }
            KeyCode::Down => {
                let len = self.state.conversations.len();
                if len > 0 {
                    let next = self.state.selected_conversation.map(|i| (i + 1).min(len - 1)).unwrap_or(0);
                    self.state.selected_conversation = Some(next);
                }
            }
            KeyCode::Enter => {
                // Send message (placeholder)
                let text = std::mem::take(&mut self.state.input);
                if !text.is_empty() {
                    self.state.status = format!("Sent: {}", &text[..text.len().min(20)]);
                }
            }
            _ => {}
        }
        Ok(())
    }
}

pub mod chat_view;
pub mod input_bar;
pub mod login;
pub mod sidebar;
pub mod status_bar;

use ratatui::{layout::{Constraint, Direction, Layout}, Frame};

use crate::state::{AppScreen, AppState};

pub fn draw(f: &mut Frame, state: &AppState) {
    match &state.screen {
        AppScreen::Login | AppScreen::TwoFaChallenge { .. } => {
            login::draw(f, state);
        }
        AppScreen::Chat => {
            let outer = Layout::default()
                .direction(Direction::Vertical)
                .constraints([Constraint::Min(0), Constraint::Length(1)])
                .split(f.size());

            let main = Layout::default()
                .direction(Direction::Horizontal)
                .constraints([Constraint::Length(24), Constraint::Min(0)])
                .split(outer[0]);

            let chat_area = Layout::default()
                .direction(Direction::Vertical)
                .constraints([Constraint::Min(0), Constraint::Length(3)])
                .split(main[1]);

            sidebar::draw(f, state, main[0]);
            chat_view::draw(f, state, chat_area[0]);
            input_bar::draw(f, state, chat_area[1]);
            status_bar::draw(f, state, outer[1]);
        }
    }
}

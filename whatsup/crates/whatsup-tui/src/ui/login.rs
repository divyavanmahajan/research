use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph},
    Frame,
};

use crate::state::{AppScreen, AppState};

pub fn draw(f: &mut Frame, state: &AppState) {
    let size = f.size();
    f.render_widget(Clear, size);

    let title = match &state.screen {
        AppScreen::TwoFaChallenge { .. } => "WhatsUp — Two-Factor Authentication",
        _ => "WhatsUp — Secure Messaging",
    };

    let outer = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage(30),
            Constraint::Length(12),
            Constraint::Min(0),
        ])
        .split(size);

    let centered = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(25),
            Constraint::Percentage(50),
            Constraint::Percentage(25),
        ])
        .split(outer[1]);

    let block = Block::default()
        .title(title)
        .borders(Borders::ALL)
        .style(Style::default().fg(Color::Cyan));

    let hint = match &state.screen {
        AppScreen::TwoFaChallenge { .. } => {
            "Enter the 6-digit code from your authenticator app"
        }
        _ => "Tab: switch fields  ·  Enter: submit  ·  Ctrl+C: quit",
    };

    let text = vec![
        Line::from(""),
        Line::from(vec![
            Span::raw("  "),
            Span::styled(&state.input, Style::default().add_modifier(Modifier::BOLD)),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            hint,
            Style::default().fg(Color::DarkGray),
        )),
    ];

    f.render_widget(
        Paragraph::new(text)
            .block(block)
            .alignment(Alignment::Left),
        centered[1],
    );

    // Status
    let status = Paragraph::new(state.status.as_str())
        .style(Style::default().fg(Color::Yellow))
        .alignment(Alignment::Center);
    f.render_widget(status, outer[2]);
}

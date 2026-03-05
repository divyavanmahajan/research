use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::{Line, Span},
    widgets::Paragraph,
    Frame,
};

use crate::state::AppState;

pub fn draw(f: &mut Frame, state: &AppState, area: Rect) {
    let conn_indicator = if state.is_connected {
        Span::styled("● Connected", Style::default().fg(Color::Green))
    } else {
        Span::styled("● Disconnected", Style::default().fg(Color::Red))
    };

    let user = state
        .current_username
        .as_deref()
        .map(|u| format!("[{u}]  "))
        .unwrap_or_default();

    let line = Line::from(vec![
        Span::styled(" E2E Encrypted · Signal Protocol  ", Style::default().fg(Color::DarkGray)),
        conn_indicator,
        Span::styled(
            "  ↑↓ scroll · Tab switch · Ctrl+C quit",
            Style::default().fg(Color::DarkGray),
        ),
    ]);

    f.render_widget(Paragraph::new(line), area);
}

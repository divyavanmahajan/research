use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::state::AppState;

pub fn draw(f: &mut Frame, state: &AppState, area: Rect) {
    let input = format!("{}_", state.input); // simple cursor indicator
    let para = Paragraph::new(Line::from(Span::raw(input)))
        .block(
            Block::default()
                .title(" Message (Enter to send) ")
                .borders(Borders::ALL)
                .style(Style::default().fg(Color::Cyan)),
        )
        .style(Style::default().fg(Color::White));
    f.render_widget(para, area);
}

use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

use crate::state::AppState;

pub fn draw(f: &mut Frame, state: &AppState, area: Rect) {
    let my_id = state.current_user_id.as_deref().unwrap_or("");

    let lines: Vec<Line> = state
        .messages
        .iter()
        .flat_map(|m| {
            let time = m.sent_at.format("%H:%M").to_string();
            let receipt = if m.is_own {
                if m.read { " ✓✓" } else if m.delivered { " ✓✓" } else { " ✓" }
            } else {
                ""
            };

            let name_style = if m.is_own {
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)
            };

            vec![Line::from(vec![
                Span::styled(format!("[{time}] "), Style::default().fg(Color::DarkGray)),
                Span::styled(
                    if m.is_own { "you" } else { m.from_user_id.as_str() },
                    name_style,
                ),
                Span::raw(": "),
                Span::raw(m.plaintext.as_str()),
                Span::styled(receipt, Style::default().fg(Color::Blue)),
            ])]
        })
        .collect();

    let title = state
        .selected_conversation
        .and_then(|i| state.conversations.get(i))
        .map(|c| c.display_name.as_str())
        .unwrap_or("Select a conversation");

    let para = Paragraph::new(lines)
        .block(
            Block::default()
                .title(format!(" {title} "))
                .borders(Borders::ALL)
                .style(Style::default().fg(Color::Cyan)),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(para, area);
}

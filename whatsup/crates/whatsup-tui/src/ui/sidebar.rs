use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState},
    Frame,
};

use crate::state::AppState;

pub fn draw(f: &mut Frame, state: &AppState, area: Rect) {
    let items: Vec<ListItem> = state
        .conversations
        .iter()
        .map(|c| {
            let unread = if c.unread > 0 {
                format!(" [{}]", c.unread)
            } else {
                String::new()
            };
            let prefix = if c.is_group { "# " } else { "  " };
            let line1 = Line::from(vec![
                Span::styled(prefix, Style::default().fg(Color::Green)),
                Span::styled(&c.display_name, Style::default().add_modifier(Modifier::BOLD)),
                Span::styled(unread, Style::default().fg(Color::Yellow)),
            ]);
            let preview = c
                .last_message
                .as_deref()
                .unwrap_or("(no messages)")
                .chars()
                .take(20)
                .collect::<String>();
            let line2 = Line::from(Span::styled(
                format!("  {preview}"),
                Style::default().fg(Color::DarkGray),
            ));
            ListItem::new(vec![line1, line2])
        })
        .collect();

    let mut list_state = ListState::default();
    list_state.select(state.selected_conversation);

    let list = List::new(items)
        .block(
            Block::default()
                .title("Conversations")
                .borders(Borders::ALL)
                .style(Style::default().fg(Color::Cyan)),
        )
        .highlight_style(Style::default().bg(Color::DarkGray).add_modifier(Modifier::BOLD))
        .highlight_symbol("▶ ");

    f.render_stateful_widget(list, area, &mut list_state);
}

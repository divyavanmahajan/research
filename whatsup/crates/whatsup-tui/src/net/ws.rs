use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use whatsup_protocol::events::ServerEvent;

pub struct WsClient {
    pub tx: mpsc::UnboundedSender<String>,
    pub rx: mpsc::UnboundedReceiver<ServerEvent>,
}

impl WsClient {
    pub async fn connect(ws_url: &str, ticket: &str) -> Result<Self> {
        let full_url = format!("{ws_url}?ticket={ticket}");
        let (ws_stream, _) = connect_async(&full_url).await?;
        let (mut write, mut read) = ws_stream.split();

        let (out_tx, mut out_rx) = mpsc::unbounded_channel::<String>();
        let (in_tx, in_rx) = mpsc::unbounded_channel::<ServerEvent>();

        // Write task
        tokio::spawn(async move {
            while let Some(msg) = out_rx.recv().await {
                if write.send(Message::Text(msg)).await.is_err() {
                    break;
                }
            }
        });

        // Read task
        tokio::spawn(async move {
            while let Some(Ok(msg)) = read.next().await {
                if let Message::Text(text) = msg {
                    if let Ok(event) = serde_json::from_str::<ServerEvent>(&text) {
                        let _ = in_tx.send(event);
                    }
                }
            }
        });

        Ok(Self { tx: out_tx, rx: in_rx })
    }

    pub fn send_raw(&self, json: String) {
        let _ = self.tx.send(json);
    }
}

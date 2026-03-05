mod app;
mod config;
mod net;
mod state;
mod ui;

use anyhow::Result;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let config = config::Config::load()?;
    let mut app = app::App::new(config).await?;
    app.run().await
}

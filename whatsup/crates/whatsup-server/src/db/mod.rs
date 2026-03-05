pub mod schema;

use std::sync::{Arc, Mutex};

use anyhow::Result;
use rusqlite::Connection;

pub type Db = Arc<Mutex<Connection>>;

pub fn open(path: &str) -> Result<Db> {
    let conn = Connection::open(path)?;
    schema::apply(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

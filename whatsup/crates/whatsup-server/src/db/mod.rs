pub mod schema;

use anyhow::Result;
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;

/// A cloneable connection pool; each handler checks out its own connection.
/// WAL mode allows multiple concurrent readers; writers serialise at the
/// SQLite file level and wait up to busy_timeout ms instead of failing.
pub type Db = Pool<SqliteConnectionManager>;

pub fn open(path: &str) -> Result<Db> {
    let manager = SqliteConnectionManager::file(path)
        .with_init(|conn| conn.execute_batch(schema::INIT_PRAGMAS));
    let pool = Pool::builder()
        .max_size(10)
        .build(manager)?;
    // Apply DDL (CREATE TABLE IF NOT EXISTS …) once at startup.
    schema::apply(&*pool.get()?)?;
    Ok(pool)
}

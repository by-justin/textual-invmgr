# manages connection to db, provides helper methods internal to db package
import asyncio
import os.path
from contextlib import asynccontextmanager
from sqlite3 import Row

import aiosqlite

from utils.logger import get_logger

_logger = get_logger(__name__)

DB_PATH = "data/db.sqlite"
DB_INIT_SCRIPTS = [
    "src/db/prj-tables.sql",
    "src/db/views-triggers.sql",
    "src/db/dummy-data.sql",
]

_initialized = False
_init_lock = asyncio.Lock()


async def _init_db(conn: aiosqlite.Connection) -> None:
    for script in DB_INIT_SCRIPTS:
        if not os.path.exists(script) or os.path.getsize(script) == 0:
            continue
        _logger.info(f"Initializing database with script {script}...")
        with open(script, "r") as f:
            await conn.executescript(f.read())
    await conn.commit()


async def _table_exists(conn: aiosqlite.Connection, table_name: str) -> bool:
    cur = await conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?;
        """,
        (table_name,),
    )
    row = await cur.fetchone()
    await cur.close()
    return row is not None


@asynccontextmanager
async def connect() -> aiosqlite.Connection:
    """Async context manager yielding an aiosqlite connection with FK enabled.

    Ensures the database is initialized (tables and seed data) on first use.
    """
    global _initialized
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = Row
    await conn.execute("PRAGMA foreign_keys = ON;")

    if not _initialized:
        async with _init_lock:
            if not _initialized:
                exists = await _table_exists(conn, "users")
                if not exists:
                    _logger.info("Initializing database...")
                    await _init_db(conn)
                _initialized = True
    try:
        yield conn
    finally:
        await conn.close()

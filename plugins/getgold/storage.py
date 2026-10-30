"""getgold 的 SQLite 存储层（价格历史）。

group.json 仍然保留为广播配置，属于唯一允许的 JSON 小配置。
价格历史不再写 price_history*.json。
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("ARCBOT_DATA_DIR", PROJECT_ROOT / "data"))
GETGOLD_DIR = Path(os.getenv("GETGOLD_DIR", DATA_DIR / "getgold"))
DB_PATH = Path(os.getenv("GETGOLD_DB", GETGOLD_DIR / "getgold.db"))

SCHEMA_VERSION = "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     REAL    NOT NULL,
    price  REAL    NOT NULL,
    push   REAL,
    source TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prices_ts ON prices(ts);
CREATE INDEX IF NOT EXISTS idx_prices_push ON prices(push);
"""


def connect(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db(db_path: Optional[Path | str] = None) -> Path:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        conn.commit()
    return path


def insert_price(
    ts: float,
    price: float,
    *,
    push: Optional[float] = None,
    source: str = "live",
    db_path: Optional[Path | str] = None,
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO prices(ts, price, push, source) VALUES(?, ?, ?, ?)",
            (float(ts), float(price), push, source),
        )
        return int(cur.lastrowid)


def set_push(
    price_id: int,
    push: Optional[float],
    db_path: Optional[Path | str] = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE prices SET push=? WHERE id=?", (push, price_id))


def last_prices(
    limit: int = 16,
    db_path: Optional[Path | str] = None,
) -> list[sqlite3.Row]:
    """按时间从旧到新返回最近 limit 条。"""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM ("
            "  SELECT * FROM prices ORDER BY ts DESC, id DESC LIMIT ?"
            ") ORDER BY ts ASC, id ASC",
            (limit,),
        ).fetchall()
        return rows


def prices_since(
    ts_start: float,
    db_path: Optional[Path | str] = None,
) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM prices WHERE ts >= ? ORDER BY ts ASC, id ASC",
            (float(ts_start),),
        ).fetchall()


def last_push(
    db_path: Optional[Path | str] = None,
) -> Optional[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM prices WHERE push IS NOT NULL "
            "ORDER BY ts DESC, id DESC LIMIT 1"
        ).fetchone()


def count(db_path: Optional[Path | str] = None) -> int:
    with connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0])


def time_range(db_path: Optional[Path | str] = None) -> tuple[Optional[float], Optional[float]]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT MIN(ts) AS a, MAX(ts) AS b FROM prices").fetchone()
        return (row["a"], row["b"]) if row else (None, None)


def backup_db(dest: Path | str, db_path: Optional[Path | str] = None) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = connect(db_path)
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def integrity_check(db_path: Optional[Path | str] = None) -> str:
    with connect(db_path) as conn:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])


def now_ts() -> float:
    return time.time()

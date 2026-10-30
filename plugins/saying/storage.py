"""saying 插件的 SQLite 存储层。

运行时代码不再读写 mappings.json；图片仍然保存在
data/saying/{group_id}/{picture_id}。
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("ARCBOT_DATA_DIR", PROJECT_ROOT / "data"))
SAYING_DIR = Path(os.getenv("SAYING_DIR", DATA_DIR / "saying"))
DB_PATH = Path(os.getenv("SAYING_DB", SAYING_DIR / "saying.db"))

SCHEMA_VERSION = "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  INTEGER NOT NULL,
    who         TEXT    NOT NULL,
    added_by    TEXT    NOT NULL,
    group_id    TEXT    NOT NULL,
    picture_id  TEXT    NOT NULL,
    md5         TEXT,
    have_sent   INTEGER NOT NULL DEFAULT 0,
    deleted_by  TEXT,
    deleted_at  INTEGER,
    source      TEXT    NOT NULL DEFAULT 'mappings.json'
);

CREATE TABLE IF NOT EXISTS quote_extra (
    quote_id INTEGER NOT NULL,
    key      TEXT    NOT NULL,
    value    TEXT,
    PRIMARY KEY (quote_id, key),
    FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quotes_archive (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id       INTEGER,
    created_at     INTEGER NOT NULL,
    who            TEXT    NOT NULL,
    added_by       TEXT    NOT NULL,
    group_id       TEXT    NOT NULL,
    picture_id     TEXT    NOT NULL,
    md5            TEXT,
    have_sent      INTEGER NOT NULL,
    deleted_by     TEXT,
    deleted_at     INTEGER,
    source         TEXT,
    archived_reason TEXT   NOT NULL,
    archived_at    INTEGER NOT NULL,
    kept_id        INTEGER
);

CREATE INDEX IF NOT EXISTS idx_quotes_pick
    ON quotes(group_id, who, have_sent);
CREATE INDEX IF NOT EXISTS idx_quotes_picture
    ON quotes(group_id, picture_id);
CREATE INDEX IF NOT EXISTS idx_quotes_md5
    ON quotes(group_id, md5);
CREATE INDEX IF NOT EXISTS idx_quotes_created
    ON quotes(created_at);
"""

# 只在清理完成后创建：保证“同群 + 同人 + 同图”唯一。
UNIQUE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_quotes_active
    ON quotes(group_id, who, md5)
    WHERE deleted_by IS NULL AND md5 IS NOT NULL;
"""


def connect(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Optional[Path | str] = None, create_unique: bool = False) -> Path:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES(?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        conn.commit()
        if create_unique:
            conn.execute(UNIQUE_INDEX)
            conn.commit()
    return path


def ensure_unique_index(db_path: Optional[Path | str] = None) -> None:
    """清理完成后调用；仍有重复时会抛 sqlite3.IntegrityError。"""
    with connect(db_path) as conn:
        conn.execute(UNIQUE_INDEX)
        conn.commit()


def set_meta(key: str, value: str, db_path: Optional[Path | str] = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_meta(key: str, default: Optional[str] = None, db_path: Optional[Path | str] = None) -> Optional[str]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def add_quote(
    *,
    created_at: int,
    who: str,
    added_by: str,
    group_id: str,
    picture_id: str,
    md5: Optional[str],
    have_sent: bool = False,
    deleted_by: Optional[str] = None,
    source: str = "runtime",
    db_path: Optional[Path | str] = None,
) -> tuple[Optional[int], bool]:
    """返回 (id, 是否插入成功)。唯一索引冲突时返回 (None, False)。"""
    try:
        with connect(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO quotes"
                "(created_at, who, added_by, group_id, picture_id, md5, have_sent, deleted_by, source) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    created_at,
                    who,
                    added_by,
                    group_id,
                    picture_id,
                    md5,
                    1 if have_sent else 0,
                    deleted_by,
                    source,
                ),
            )
            return int(cur.lastrowid), True
    except sqlite3.IntegrityError:
        return None, False


def _placeholders(values: Sequence[str]) -> str:
    return ",".join("?" for _ in values)


def pick_quote(
    group_ids: Iterable[str],
    who: str,
    *,
    db_path: Optional[Path | str] = None,
) -> Optional[sqlite3.Row]:
    """取一张未发送的图；若全部已发送则重置该 Who 后再取。"""
    groups = [str(g) for g in group_ids]
    if not groups:
        return None
    ph = _placeholders(groups)
    base = (
        f"FROM quotes WHERE group_id IN ({ph}) AND who=? "
        "AND deleted_by IS NULL AND have_sent=0"
    )
    params = (*groups, who)
    with connect(db_path) as conn:
        row = conn.execute(
            f"SELECT * {base} ORDER BY RANDOM() LIMIT 1", params
        ).fetchone()
        if row is not None:
            return row

        total = conn.execute(
            f"SELECT COUNT(*) FROM quotes WHERE group_id IN ({ph}) "
            "AND who=? AND deleted_by IS NULL",
            params,
        ).fetchone()[0]
        if not total:
            return None

        conn.execute(
            f"UPDATE quotes SET have_sent=0 WHERE group_id IN ({ph}) "
            "AND who=? AND deleted_by IS NULL",
            params,
        )
        conn.commit()
        return conn.execute(
            f"SELECT * {base} ORDER BY RANDOM() LIMIT 1", params
        ).fetchone()


def mark_sent(quote_id: int, db_path: Optional[Path | str] = None) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE quotes SET have_sent=1 WHERE id=?", (quote_id,))


def mark_unsent(quote_id: int, db_path: Optional[Path | str] = None) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE quotes SET have_sent=0 WHERE id=?", (quote_id,))


def get_quote_by_picture(
    group_id: str,
    picture_id: str,
    db_path: Optional[Path | str] = None,
) -> Optional[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM quotes WHERE group_id=? AND picture_id=? AND deleted_by IS NULL "
            "ORDER BY created_at ASC LIMIT 1",
            (group_id, picture_id),
        ).fetchone()


def delete_quote(
    *,
    group_id: str,
    deleted_by: str,
    picture_id: Optional[str] = None,
    md5: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> int:
    """只删除本群记录；picture_id / md5 至少给一个。"""
    if picture_id is None and md5 is None:
        return 0
    conds = ["group_id=?", "deleted_by IS NULL"]
    params: list[str] = [group_id]
    if picture_id is not None and md5 is not None:
        conds.append("(picture_id=? OR md5=?)")
        params.extend([picture_id, md5])
    elif picture_id is not None:
        conds.append("picture_id=?")
        params.append(picture_id)
    else:
        conds.append("md5=?")
        params.append(md5)

    with connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE quotes SET deleted_by=?, deleted_at=? WHERE " + " AND ".join(conds),
            (deleted_by, int(time.time() * 1000), *params),
        )
        return cur.rowcount


def stats(
    group_ids: Iterable[str],
    db_path: Optional[Path | str] = None,
) -> tuple[list[sqlite3.Row], int]:
    """返回 ([(who, cnt), ...], 去重图片总数)。"""
    groups = [str(g) for g in group_ids]
    if not groups:
        return [], 0
    ph = _placeholders(groups)
    where = f"group_id IN ({ph}) AND deleted_by IS NULL"
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT who, COUNT(DISTINCT COALESCE(md5, picture_id)) AS cnt "
            f"FROM quotes WHERE {where} "
            "GROUP BY who ORDER BY cnt DESC, who ASC",
            groups,
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(DISTINCT COALESCE(md5, picture_id)) "
            f"FROM quotes WHERE {where}",
            groups,
        ).fetchone()[0]
        return rows, int(total or 0)


def all_quotes(include_deleted: bool = False, db_path: Optional[Path | str] = None) -> list[sqlite3.Row]:
    where = "" if include_deleted else "WHERE deleted_by IS NULL"
    with connect(db_path) as conn:
        return conn.execute(
            f"SELECT * FROM quotes {where} ORDER BY created_at ASC, id ASC"
        ).fetchall()


def archive_quote(
    quote_id: int,
    reason: str,
    *,
    kept_id: Optional[int] = None,
    db_path: Optional[Path | str] = None,
) -> bool:
    """把一条记录移入 quotes_archive，并从 quotes 删除。"""
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM quotes WHERE id=?", (quote_id,)).fetchone()
        if row is None:
            return False
        conn.execute(
            "INSERT INTO quotes_archive"
            "(quote_id, created_at, who, added_by, group_id, picture_id, md5, have_sent,"
            " deleted_by, deleted_at, source, archived_reason, archived_at, kept_id) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["id"],
                row["created_at"],
                row["who"],
                row["added_by"],
                row["group_id"],
                row["picture_id"],
                row["md5"],
                row["have_sent"],
                row["deleted_by"],
                row["deleted_at"],
                row["source"],
                reason,
                int(time.time() * 1000),
                kept_id,
            ),
        )
        conn.execute("DELETE FROM quotes WHERE id=?", (quote_id,))
        return True


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

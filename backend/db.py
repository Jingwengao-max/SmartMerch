"""SQLite 数据访问：连接与建表。

用户、会话与作品数据统一放在 data/app.db（默认 backend/data/app.db，可经 SMARTMERCH_RUNTIME_DIR 指定），
使用标准库 sqlite3，不引入第三方依赖。
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 与 api.py 保持一致：云部署可通过 SMARTMERCH_RUNTIME_DIR 指定持久化目录，
# 默认回退到 backend 目录，本地路径不变。
RUNTIME_DIR = Path(os.getenv("SMARTMERCH_RUNTIME_DIR", str(ROOT))).expanduser().resolve()
DATA_DIR = RUNTIME_DIR / "data"
GENERATED_DIR = RUNTIME_DIR / "generated"
WORKS_DIR = RUNTIME_DIR / "works"
DB_PATH = DATA_DIR / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);

CREATE TABLE IF NOT EXISTS works (
    id            TEXT NOT NULL PRIMARY KEY,
    user_id       TEXT NOT NULL,
    title         TEXT NOT NULL,
    meta_json     TEXT NOT NULL DEFAULT '{}',
    document_json TEXT NOT NULL,
    preview_url   TEXT NOT NULL,
    asset_version TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_works_user_id ON works (user_id);
"""

_REQUIRED_WORKS_COLUMNS = {
    "id", "user_id", "title", "meta_json", "document_json",
    "preview_url", "asset_version", "created_at", "updated_at",
}


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    # 每次连接都幂等建表：即使 app.db 被删除或为空，也能自愈，
    # 不依赖「进程启动时只执行一次 init_db」。
    connection.executescript(SCHEMA)
    connection.commit()
    return connection


def _ensure_works_columns(connection: sqlite3.Connection) -> None:
    """works 是全新表；若发现已存在但缺列的历史结构，明确报错而非伪造迁移。"""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(works)")}
    if not columns:
        return  # works 表刚由 SCHEMA 创建，结构完整
    missing = _REQUIRED_WORKS_COLUMNS - columns
    if missing:
        raise RuntimeError(
            f"works 表缺少必需字段 {sorted(missing)}，无法安全迁移，请人工处理。"
        )


def init_db() -> None:
    # 显式初始化入口：打开一次连接即完成建表（get_connection 自带建表），并校验 works 结构。
    connection = get_connection()
    try:
        _ensure_works_columns(connection)
    finally:
        connection.close()

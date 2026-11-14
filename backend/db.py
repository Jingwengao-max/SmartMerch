"""SQLite 数据访问：连接与建表。

用户与会话数据统一放在 backend/data/app.db，使用标准库 sqlite3，不引入第三方依赖。
阶段四的作品存储也复用本模块。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
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
"""


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


def init_db() -> None:
    # 显式初始化入口：打开一次连接即完成建表（get_connection 自带建表）。
    connection = get_connection()
    connection.close()

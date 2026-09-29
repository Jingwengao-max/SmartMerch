"""读取随 poster-design 源码附带的 SQLite 模板库。"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
VENDOR_ROOT = ROOT / "vendor" / "poster-design"
DB_PATH = VENDOR_ROOT / "service" / "seed" / "poster.db"
STATIC_DIR = VENDOR_ROOT / "service" / "seed" / "static"
REMOTE_STATIC_PREFIX = "http://127.0.0.1:7001/static/"
PUBLIC_STATIC_PREFIX = "/poster-design-static/"


def available() -> bool:
    return DB_PATH.is_file() and STATIC_DIR.is_dir()


def _connect() -> sqlite3.Connection:
    if not available():
        raise FileNotFoundError("未找到 poster-design 的种子数据库或静态素材。")
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _rewrite_assets(value: Any) -> Any:
    """把源码中指向 7001 端口的静态地址改成本项目地址。"""
    if isinstance(value, str):
        return value.replace(REMOTE_STATIC_PREFIX, PUBLIC_STATIC_PREFIX)
    if isinstance(value, list):
        return [_rewrite_assets(item) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_assets(item) for key, item in value.items()}
    return value


def list_templates(template_type: int = 0) -> list[dict[str, Any]]:
    with closing(_connect()) as connection:
        rows = connection.execute(
            """SELECT id, title, cover, width, height, type, cate
               FROM templates WHERE state = 1 AND type = ? ORDER BY id DESC""",
            (template_type,),
        ).fetchall()
    return [
        {
            **dict(row),
            "cover": _rewrite_assets(row["cover"]),
            "kind": "template" if row["type"] == 0 else "component",
        }
        for row in rows
    ]


def load_template(template_id: int) -> dict[str, Any]:
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT * FROM templates WHERE id = ? AND state = 1", (template_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"模板 {template_id} 不存在。")

    payload = json.loads(row["data"])
    # 旧组件记录的真实组件数组被包在 data 字符串中。
    if isinstance(payload, dict) and isinstance(payload.get("data"), str):
        payload = {
            "id": row["id"],
            "title": row["title"],
            "page": {
                "width": row["width"],
                "height": row["height"],
                "backgroundColor": "#ffffffff",
            },
            "widgets": json.loads(payload["data"]),
        }
    elif isinstance(payload, list):
        payload = {
            "id": row["id"],
            "title": row["title"],
            "page": {"width": row["width"], "height": row["height"]},
            "widgets": payload,
        }
    payload.setdefault("id", row["id"])
    payload.setdefault("title", row["title"])
    return _rewrite_assets(payload)

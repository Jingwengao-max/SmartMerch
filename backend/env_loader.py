"""从 backend/.env 读取本地配置。

只补全缺失的环境变量，不覆盖外部已经设好的值；找不到文件就安静跳过。
优先使用 python-dotenv，没安装时退回内置的极简解析，避免多一个硬依赖。
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"
_loaded = False


def _parse(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def load_env(path: Path | None = None) -> bool:
    """返回是否成功读取到配置文件。已存在的环境变量不会被覆盖。"""
    global _loaded
    target = Path(path) if path is not None else ENV_FILE
    if path is None:
        if _loaded:
            return False
        _loaded = True
    if not target.is_file():
        return False

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv(dotenv_path=target, override=False)
        return True

    for key, value in _parse(target.read_text(encoding="utf-8")).items():
        os.environ.setdefault(key, value)
    return True

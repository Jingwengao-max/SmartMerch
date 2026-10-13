"""AI 文案模块的配置读取，集中在一处，方便整体替换模型或网关。"""

from __future__ import annotations

import os
from urllib.parse import urlparse

DEFAULT_MODEL = "qwen3-vl-plus"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
# 样例文件里的占位值不算配置，否则复制一份 .env.example 就会假装已配置。
PLACEHOLDER_KEYS = {"replace-with-your-key", "your-key-here", "your-key", "changeme", "sk-xxx"}
PLACEHOLDER_HOSTS = {"example.com", "your-host"}


def api_url() -> str:
    return os.getenv("AI_API_URL", "").strip()


def api_key() -> str:
    return os.getenv("AI_API_KEY", "").strip()


def model_name() -> str:
    return os.getenv("AI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def timeout() -> float:
    try:
        return float(os.getenv("AI_TIMEOUT", "120"))
    except ValueError:
        return 120.0


def image_max_edge() -> int:
    try:
        return int(os.getenv("AI_IMAGE_MAX_EDGE", "1024"))
    except ValueError:
        return 1024


def is_local_endpoint(url: str | None = None) -> bool:
    """本地部署（Ollama / vLLM / LM Studio）通常不需要真实密钥。"""
    target = (url if url is not None else api_url()).strip()
    if not target:
        return False
    host = (urlparse(target).hostname or "").lower()
    if host in LOCAL_HOSTS:
        return True
    return host.startswith(("10.", "192.168.", "172.16.", "172.17.")) or host.endswith(".local")


def _placeholder_key(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_KEYS


def _placeholder_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in PLACEHOLDER_HOSTS or host.endswith(".example.com")


def configured() -> bool:
    """没有 URL 就是未配置；本地端点允许省略密钥。"""
    url = api_url()
    if not url or _placeholder_url(url):
        return False
    key = api_key()
    if key and not _placeholder_key(key):
        return True
    return is_local_endpoint(url)


def chat_endpoint() -> str:
    """允许填 /v1 根地址或完整的 /chat/completions 地址。"""
    url = api_url().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return url

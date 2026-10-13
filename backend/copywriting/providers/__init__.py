"""Provider 注册表：换模型只改这里，业务层不感知。"""

from __future__ import annotations

from ..config import configured
from . import local_fallback
from .openai_compat import OpenAICompatProvider

__all__ = ["get_provider", "local_fallback", "OpenAICompatProvider"]


def get_provider():
    """配置齐全时返回视觉模型 provider，否则返回 None（调用方走本地兜底）。"""
    if not configured():
        return None
    return OpenAICompatProvider()

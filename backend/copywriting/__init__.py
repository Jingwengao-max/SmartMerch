"""视觉文案模块的公开入口。

对外只有三样东西：configured()、generate_copy()、CopyRequest。
调用方不需要知道背后是哪个模型、哪家网关。
"""

from __future__ import annotations

from dataclasses import replace

from .config import configured
from .compose import compose
from .providers import get_provider, local_fallback
from .schema import CopyRequest, build_copy_set, normalize_variant

__all__ = ["configured", "generate_copy", "refine_copy", "CopyRequest", "build_copy_set", "compose"]


def generate_copy(request: CopyRequest, *, require_ai: bool = False) -> dict:
    """生成文案。未配置模型时自动降级为本地安全占位文案。"""
    provider = get_provider()
    if provider is None:
        if require_ai:
            raise RuntimeError("尚未配置视觉模型接口（AI_API_URL / AI_API_KEY）。")
        return local_fallback.generate(request)
    payload = provider.generate(request)
    return compose(payload, request, source="ai", provider=provider.name)


def refine_copy(request: CopyRequest, current: dict, feedback: dict) -> dict:
    """按用户对某几条的意见修改文案，未提意见的条目保持原样。"""
    provider = get_provider()
    if provider is None:
        raise RuntimeError("尚未配置视觉模型接口（AI_API_URL / AI_API_KEY），无法按意见修改。")

    payload = provider.generate_refine(request, current, feedback)
    # 只有用户自己填的价格才算事实；当前版本里的价格是模型推测的，应该允许改。
    # 活动信息只可能来自用户（模型编造的会被 compose 清掉），所以保留下来。
    facts = replace(request, promo=request.promo.strip() or str(current.get("promo_text") or "").strip())
    result = compose(payload, facts, source="ai", provider=provider.name)
    result["variants"] = result["variants"][:1]
    if result["variants"]:
        variant = result["variants"][0]
        # 模型这次没给价格时，沿用上一版，避免改一条意见反而把价格弄丢。
        if not variant["price_text"] and not request.price.strip() and current.get("price_text"):
            variant["price_text"] = str(current["price_text"])
            variant["price_estimated"] = bool(current.get("price_estimated"))
    result["refinedFrom"] = normalize_variant(current)
    return result

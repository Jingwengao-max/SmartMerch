"""用户逐条修改意见的规范化：保持与文案块一一对应。"""

from __future__ import annotations

from typing import Any

from .schema import MAX_SELLING_POINTS, SPLIT_PATTERN, _clean

FEEDBACK_LIMIT = 60


def normalize_feedback(payload: Any, point_count: int) -> dict[str, Any]:
    """把前端传来的修改意见整理成与文案块同构的结构。"""
    data = payload if isinstance(payload, dict) else {}
    raw_points = data.get("selling_points")
    if isinstance(raw_points, str):
        raw_points = SPLIT_PATTERN.split(raw_points)
    if not isinstance(raw_points, (list, tuple)):
        raw_points = []
    points = [_clean(item, FEEDBACK_LIMIT) for item in list(raw_points)[:MAX_SELLING_POINTS]]
    points = (points + [""] * point_count)[:max(point_count, len(points))]
    return {
        "title": _clean(data.get("title"), FEEDBACK_LIMIT),
        "subtitle": _clean(data.get("subtitle"), FEEDBACK_LIMIT),
        "selling_points": points,
        "price_text": _clean(data.get("price_text"), FEEDBACK_LIMIT),
        "promo_text": _clean(data.get("promo_text"), FEEDBACK_LIMIT),
    }


def has_feedback(feedback: dict[str, Any]) -> bool:
    if any(str(feedback.get(key, "")).strip() for key in ("title", "subtitle", "price_text", "promo_text")):
        return True
    return any(str(item).strip() for item in feedback.get("selling_points", []))

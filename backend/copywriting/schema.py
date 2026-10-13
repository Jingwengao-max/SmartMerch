"""文案契约：只描述"海报上需要哪些文字"，不掺任何模型细节。

换视觉模型时，只要保证输出能映射到这里，其余代码都不用动。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

LIMITS: dict[str, int] = {
    "title": 24,
    "subtitle": 48,
    "selling_point": 24,
    "price_text": 20,
    "promo_text": 20,
    "category": 30,
    "color": 20,
    "feature": 30,
    "scene": 20,
    "warning": 160,
}

MAX_VARIANTS = 3
MAX_SELLING_POINTS = 4
SPLIT_PATTERN = re.compile(r"[，,、;；|\n]+")


@dataclass
class CopyRequest:
    """一次文案生成请求：抠图后的商品图 + 用户已经填写的已知信息。"""

    images: list[Path] = field(default_factory=list)
    name: str = ""
    feature: str = ""
    selling_points: list[str] = field(default_factory=list)
    vibe: str = ""
    style: str = ""
    price: str = ""
    promo: str = ""

    @property
    def known_facts(self) -> dict[str, str]:
        """只有用户真正填了的字段才算事实，用于防幻觉。"""
        raw = {
            "商品名称": self.name,
            "商品特点": self.feature,
            "用户提供的卖点": "、".join(point.strip() for point in self.selling_points if point.strip()),
            "营销方向": self.vibe,
            "设计风格": self.style,
            "价格": self.price,
            "活动": self.promo,
        }
        return {key: value.strip() for key, value in raw.items() if value and value.strip()}


def _clean(value: Any, limit: int) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def empty_variant() -> dict[str, Any]:
    return {
        "title": "",
        "subtitle": "",
        "selling_points": [],
        "price_text": "",
        "promo_text": "",
        "price_estimated": False,
    }


def normalize_selling_points(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates: Iterable[Any] = SPLIT_PATTERN.split(value)
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        return []
    points: list[str] = []
    for item in candidates:
        text = _clean(item, LIMITS["selling_point"])
        if text and text not in points:
            points.append(text)
    return points[:MAX_SELLING_POINTS]


def normalize_variant(payload: Any) -> dict[str, Any] | None:
    """接受 dict 或纯字符串；至少要有标题或副标题才认为有效。"""
    variant = empty_variant()
    if isinstance(payload, str):
        variant["title"] = _clean(payload, LIMITS["title"])
    elif isinstance(payload, dict):
        variant["title"] = _clean(payload.get("title"), LIMITS["title"])
        variant["subtitle"] = _clean(payload.get("subtitle"), LIMITS["subtitle"])
        variant["selling_points"] = normalize_selling_points(payload.get("selling_points"))
        variant["price_text"] = _clean(payload.get("price_text"), LIMITS["price_text"])
        variant["promo_text"] = _clean(payload.get("promo_text"), LIMITS["promo_text"])
        variant["price_estimated"] = bool(payload.get("price_estimated"))
    if variant["title"] or variant["subtitle"]:
        return variant
    return None


def normalize_variants(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, (list, tuple)):
        return []
    variants: list[dict[str, Any]] = []
    for item in payload:
        variant = normalize_variant(item)
        if variant and variant not in variants:
            variants.append(variant)
    return variants[:MAX_VARIANTS]


def _text_list(value: Any, limit: int, maximum: int) -> list[str]:
    if isinstance(value, str):
        value = SPLIT_PATTERN.split(value)
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value:
        text = _clean(item, limit)
        if text and text not in result:
            result.append(text)
    return result[:maximum]


def normalize_identification(payload: Any) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    try:
        confidence = round(float(data.get("confidence", 0) or 0), 3)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "category": _clean(data.get("category"), LIMITS["category"]) or "待确认商品",
        "color": _clean(data.get("color"), LIMITS["color"]) or "待确认",
        "visible_features": _text_list(data.get("visible_features"), LIMITS["feature"], 5),
        "scene": _text_list(data.get("scene"), LIMITS["scene"], 4),
        "confidence": min(1.0, max(0.0, confidence)),
        "warning": _clean(data.get("warning"), LIMITS["warning"]),
    }


def build_copy_set(
    identification: dict[str, Any],
    variants: list[dict[str, Any]],
    source: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    first = variants[0] if variants else empty_variant()
    return {
        "source": source,
        "identification": identification,
        "variants": variants,
        "suggested": {
            "name": "" if identification["category"] == "待确认商品" else identification["category"],
            "feature": "，".join(identification["visible_features"]),
            "price": first["price_text"],
            "promo": first["promo_text"],
            "selling_points": list(first["selling_points"]),
        },
        "meta": dict(meta or {}),
    }

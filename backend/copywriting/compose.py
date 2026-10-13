"""把模型输出收敛成契约，并做一层服务端防幻觉校验。"""

from __future__ import annotations

from typing import Any

from .config import model_name
from .schema import (
    LIMITS,
    CopyRequest,
    build_copy_set,
    normalize_identification,
    normalize_variants,
)

FABRICATION_NOTE = "已忽略模型自行编造的折扣/活动信息，请以真实资料为准。"
PRICE_ESTIMATE_NOTE = "价格为模型根据商品推测的参考价，请核对后再使用。"


def compose(payload: dict[str, Any], request: CopyRequest, source: str = "ai",
            provider: str = "") -> dict[str, Any]:
    """模型输出 → 稳定契约。用户没给的价格和活动，无论模型怎么答都会被清空。"""
    identification = normalize_identification(payload)
    variants = normalize_variants(payload.get("variants"))
    if not variants:
        # 兼容旧字段名，也允许模型只给一组。
        variants = normalize_variants(payload.get("copywriting"))
    if not variants:
        raise ValueError("视觉模型没有返回可用文案。")

    price_fact = request.price.strip()[: LIMITS["price_text"]]
    promo_fact = request.promo.strip()[: LIMITS["promo_text"]]
    fabricated = False
    for variant in variants:
        # 价格和活动属于事实：用户填了就一律以用户为准，没填就清空模型编的内容。
        if price_fact:
            variant["price_text"] = price_fact
            variant["price_estimated"] = False
        else:
            # 价格允许模型推测，但必须标注成参考价。
            variant["price_estimated"] = bool(variant["price_text"])
        if promo_fact:
            variant["promo_text"] = promo_fact
        else:
            if variant["promo_text"]:
                fabricated = True
            variant["promo_text"] = ""

    warning = identification["warning"]
    if any(variant["price_estimated"] for variant in variants):
        warning = f"{warning} {PRICE_ESTIMATE_NOTE}".strip()
    if fabricated:
        warning = f"{warning} {FABRICATION_NOTE}".strip()
    identification["warning"] = warning

    return build_copy_set(
        identification,
        variants,
        source=source,
        meta={"provider": provider or source, "model": model_name()},
    )

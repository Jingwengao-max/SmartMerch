"""可解释的海报质量评分。后续可替换为训练得到的排序模型。"""

from __future__ import annotations

from typing import Any


def _rect(element: dict[str, Any]) -> tuple[float, float, float, float]:
    x, y = float(element["x"]), float(element["y"])
    return x, y, x + float(element["width"]), y + float(element["height"])


def _intersection(a, b) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0.0, min(a[3], b[3]) - max(a[1], b[1])
    )


def evaluate_document(document: dict[str, Any]) -> dict[str, Any]:
    """基于图层几何关系给出0～100分及可读建议。"""
    canvas = document["canvas"]
    width, height = float(canvas["width"]), float(canvas["height"])
    elements = document.get("elements", [])
    product = next((item for item in elements if item.get("role") == "product"), None)
    texts = [item for item in elements if item.get("type") == "text"]
    suggestions: list[str] = []

    safe = 100.0
    for element in elements:
        left, top, right, bottom = _rect(element)
        if left < 20 or top < 20 or right > width - 20 or bottom > height - 20:
            safe -= 12
    if safe < 100:
        suggestions.append("部分元素过于靠近画布边缘，建议保留至少20像素安全距离。")

    overlap_score = 100.0
    if product:
        product_rect = _rect(product)
        product_area = max(1.0, float(product["width"]) * float(product["height"]))
        for text in texts:
            intersection = _intersection(product_rect, _rect(text))
            if intersection:
                overlap_score -= min(45.0, intersection / product_area * 180)
        if overlap_score < 95:
            suggestions.append("商品与文字存在遮挡，可移动文字或缩小商品。")

    readability = 100.0
    for text in texts:
        size = float(text.get("fontSize", 32))
        if size < 28:
            readability -= 10
        content = str(text.get("content", ""))
        estimated_width = len(content) * size
        if estimated_width > float(text.get("width", width)) * 1.15:
            readability -= 15
    if readability < 95:
        suggestions.append("部分文字可能过小或超出文本框。")

    balance = 100.0
    if product:
        center = (float(product["x"]) + float(product["width"]) / 2) / width
        text_weight = sum(float(item.get("width", 0)) * float(item.get("height", 0)) for item in texts)
        if text_weight and abs(center - 0.5) > 0.34:
            balance -= 15

    product_prominence = 0.0
    if product:
        ratio = float(product["width"]) * float(product["height"]) / (width * height)
        product_prominence = max(0.0, 100 - abs(ratio - 0.24) * 240)
        if ratio < 0.10:
            suggestions.append("商品主体偏小，建议适当放大。")

    scores = {
        "safe_margin": round(max(0, safe), 1),
        "no_overlap": round(max(0, overlap_score), 1),
        "readability": round(max(0, readability), 1),
        "visual_balance": round(max(0, balance), 1),
        "product_prominence": round(max(0, product_prominence), 1),
    }
    overall = sum(scores.values()) / len(scores)
    return {
        "overall": round(overall, 1),
        "scores": scores,
        "suggestions": suggestions or ["当前版式结构良好，可继续微调文案与配色。"],
    }

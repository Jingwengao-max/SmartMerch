"""把文案字段追加成海报文本图层。

刻意不改 layout_engine 的模板评分逻辑：这里只负责"在画面空白处补文字"，
模板若声明了可选的 promo_area / selling_points_area 则优先使用，否则按商品区域
自动推导底部信息栏。
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from layout_engine import CANVAS, load_font, load_templates, normalized_to_pixels, overlap

MAX_SELLING_POINTS = 4
BAND_BOTTOM = 0.978
BAND_LEFT = 0.083
BAND_RIGHT = 0.917


def _measure(text: str, font) -> tuple[int, int]:
    box = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    return max(1, box[2] - box[0]), max(1, box[3] - box[1])


def _template_for(document: dict[str, Any]) -> dict[str, Any]:
    template_id = document.get("templateId")
    if not template_id:
        return {}
    for template in load_templates():
        if template.get("id") == template_id:
            return template
    return {}


def _text_element(element_id: str, role: str, content: str, x: int, y: int,
                  font_size: int, color: str, weight: int) -> dict[str, Any]:
    font = load_font(font_size)
    width, height = _measure(content, font)
    return {
        "id": element_id,
        "type": "text",
        "role": role,
        "content": content,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "fontSize": font_size,
        "fontWeight": weight,
        "color": color,
        "rotation": 0,
        "zIndex": 5,
    }


def _upsert(elements: list[dict[str, Any]], spec: dict[str, Any]) -> None:
    for element in elements:
        if element.get("id") == spec["id"]:
            element.update(spec)
            return
    elements.append(spec)


def _band_bounds(document: dict[str, Any], template: dict[str, Any]) -> tuple[int, int, int, int]:
    """返回底部信息栏的像素边界，自动避开商品区域和价格图层。"""
    canvas_width, canvas_height = int(document["canvas"]["width"]), int(document["canvas"]["height"])
    product_area = template.get("product_area")
    top_ratio = max(0.830, float(product_area[3]) + 0.008) if product_area else 0.830
    left = round(BAND_LEFT * canvas_width)
    right = round(BAND_RIGHT * canvas_width)
    for element in document.get("elements", []):
        if element.get("role") == "price":
            right = min(right, round(float(element.get("x", right))) - 20)
    top = round(top_ratio * canvas_height)
    bottom = round(BAND_BOTTOM * canvas_height)
    return left, max(top, 0), max(right, left + 80), bottom


def attach_copy_layers(document: dict[str, Any], copy: dict[str, Any] | None) -> dict[str, Any]:
    """把 promo_text / selling_points 追加为图层；没有内容就原样返回。"""
    if not copy:
        return document
    promo = str(copy.get("promo_text") or "").strip()
    points = [str(point).strip() for point in (copy.get("selling_points") or []) if str(point).strip()]
    points = points[:MAX_SELLING_POINTS]
    if not promo and not points:
        return document

    elements = document.setdefault("elements", [])
    template = _template_for(document)
    left, top, right, bottom = _band_bounds(document, template)
    canvas_width = int(document["canvas"]["width"])

    promo_area = template.get("promo_area")
    if promo_area:
        area = normalized_to_pixels(promo_area, (canvas_width, int(document["canvas"]["height"])))
        promo_top, promo_bottom = area[1], area[3]
        points_top, points_bottom = area[3], bottom
    elif promo and points:
        split = top + round((bottom - top) * 0.32)
        promo_top, promo_bottom = top, split
        points_top, points_bottom = split, bottom
    elif promo:
        promo_top, promo_bottom = top, bottom
        points_top, points_bottom = bottom, bottom
    else:
        promo_top, promo_bottom = top, top
        points_top, points_bottom = top, bottom

    if promo:
        font_size = 30
        font = load_font(font_size)
        width, height = _measure(promo, font)
        x = max(left, left + (right - left - width) // 2)
        y = promo_top + max(0, (promo_bottom - promo_top - height) // 2)
        _upsert(elements, _text_element("promo", "promo", promo, x, y, font_size, "#b94767", 600))

    if points:
        available = max(1, points_bottom - points_top)
        step = max(24, min(38, available // len(points)))
        font_size = max(20, min(28, step - 8))
        for index, point in enumerate(points, start=1):
            y = points_top + (index - 1) * step
            _upsert(
                elements,
                _text_element(
                    f"selling_point_{index}", "selling_point", point,
                    left, y, font_size, "#5c4d55", 400,
                ),
            )

    product_rect = next(
        (
            (element["x"], element["y"], element["x"] + element["width"], element["y"] + element["height"])
            for element in elements
            if element.get("role") == "product"
        ),
        None,
    )
    if product_rect:
        placed = [
            (element["x"], element["y"], element["x"] + element["width"], element["y"] + element["height"])
            for element in elements
            if element.get("role") in {"promo", "selling_point"}
        ]
        if any(overlap(product_rect, rect) for rect in placed):
            document["layoutNote"] = "底部信息栏与商品区域接近，建议在编辑器中微调文字位置。"
    return document

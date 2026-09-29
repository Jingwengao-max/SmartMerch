"""把poster-design常见的画布/组件JSON转换为本项目分层文档。"""

from __future__ import annotations

from typing import Any


def _number(*values, default=0):
    for value in values:
        if value is not None:
            try:
                return float(str(value).replace("px", ""))
            except (TypeError, ValueError):
                pass
    return default


def normalize_template(payload: dict[str, Any]) -> dict[str, Any]:
    """接受本项目JSON，以及poster-design真实的page/widgets与global/layers格式。"""
    if isinstance(payload, list):
        if not payload:
            raise ValueError("模板数组为空。")
        first = payload[0]
        payload = {"page": first.get("global", {}), "widgets": first.get("layers", [])}
    if payload.get("canvas") and isinstance(payload.get("elements"), list):
        return payload

    raw_canvas = payload.get("canvas") or payload.get("page") or payload.get("artboard") or payload
    width = int(_number(raw_canvas.get("width"), payload.get("width"), default=1080))
    height = int(_number(raw_canvas.get("height"), payload.get("height"), default=1350))
    background = (
        raw_canvas.get("backgroundImage") or raw_canvas.get("background")
        or raw_canvas.get("backgroundColor") or payload.get("backgroundImage")
        or payload.get("background") or payload.get("backgroundColor")
    )
    raw_elements = (
        payload.get("elements") or payload.get("components") or payload.get("layers")
        or payload.get("list") or payload.get("widgets") or []
    )
    elements = []
    for index, raw in enumerate(raw_elements):
        style = raw.get("style") or raw.get("css") or {}
        if not isinstance(style, dict):
            style = {}
        raw_type = str(raw.get("type") or raw.get("component") or raw.get("widget") or "").lower()
        content = raw.get("content", raw.get("text", ""))
        source = raw.get("src") or raw.get("imgUrl") or raw.get("svgUrl") or raw.get("url") or raw.get("image")
        element_type = "text" if "text" in raw_type or (content and not source) else "image"
        element = {
            "id": str(raw.get("uuid") or raw.get("id") or f"imported_{index}"),
            "type": element_type,
            "role": raw.get("role") or ("title" if element_type == "text" and index == 0 else element_type),
            "x": _number(raw.get("x"), raw.get("left"), style.get("left")),
            "y": _number(raw.get("y"), raw.get("top"), style.get("top")),
            "width": _number(raw.get("width"), style.get("width"), default=300),
            "height": _number(raw.get("height"), style.get("height"), default=100),
            "rotation": _number(raw.get("rotation"), raw.get("rotate"), style.get("rotate")),
            "zIndex": int(_number(raw.get("zIndex"), style.get("zIndex"), default=index + 1)),
        }
        if element_type == "text":
            element.update({
                "content": str(content),
                "fontSize": int(_number(raw.get("fontSize"), style.get("fontSize"), default=48)),
                "fontWeight": int(_number(raw.get("fontWeight"), style.get("fontWeight"), default=400)),
                "color": raw.get("color") or style.get("color") or "#222222",
            })
        elif source:
            element["src"] = source
        else:
            continue
        elements.append(element)
    if not elements:
        raise ValueError("模板中没有识别到文字或图片组件。")
    canvas = {"width": width, "height": height}
    if isinstance(background, str) and background.startswith(("/", "http", "data:")):
        canvas["backgroundImage"] = background
    else:
        canvas["backgroundColor"] = background if isinstance(background, str) else "#ffffff"
    return {
        "id": str(payload.get("id") or "imported_template"),
        "name": str(payload.get("name") or payload.get("title") or "导入模板"),
        "templateId": str(payload.get("templateId") or payload.get("id") or "imported"),
        "canvas": canvas,
        "elements": elements,
    }

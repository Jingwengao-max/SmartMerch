"""Instantiate a reusable template with new content."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _pixel_bbox(bbox: list[float], canvas: dict[str, Any]) -> tuple[int, int, int, int]:
    width = float(canvas["width"])
    height = float(canvas["height"])
    return (
        round(float(bbox[0]) * width),
        round(float(bbox[1]) * height),
        max(1, round(float(bbox[2]) * width)),
        max(1, round(float(bbox[3]) * height)),
    )


def _fit_image(bbox: tuple[int, int, int, int],
               source_size: tuple[int, int] | None) -> tuple[int, int, int, int]:
    if not source_size:
        return bbox
    x, y, width, height = bbox
    source_ratio = source_size[0] / max(1, source_size[1])
    target_ratio = width / max(1, height)
    if source_ratio > target_ratio:
        render_width, render_height = width, round(width / source_ratio)
    else:
        render_height, render_width = height, round(height * source_ratio)
    return (
        x + (width - render_width) // 2,
        y + (height - render_height) // 2,
        render_width,
        render_height,
    )


def _content_value(content: dict[str, Any], key: str | None,
                   fallback: Any = "") -> str:
    if not key:
        return str(fallback or "")
    value = content.get(key, fallback)
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if str(item).strip())
    return str(value or "")


def instantiate_template(template: dict[str, Any], content: dict[str, Any], *,
                         product_url: str, background_url: str = "",
                         product_size: tuple[int, int] | None = None,
                         document_id: str = "poster_001") -> dict[str, Any]:
    """Build a PosterDocument consumable by the existing editor and renderer."""
    canvas = deepcopy(template["canvas"])
    if background_url:
        canvas["backgroundImage"] = background_url
    else:
        palette = (template.get("style") or {}).get("palette") or []
        canvas["backgroundColor"] = palette[0] if palette else "#f5f5f5"

    elements: list[dict[str, Any]] = []
    product_name = str(
        content.get("title")
        or content.get("subtitle")
        or content.get("productName")
        or ""
    )
    for layer in template.get("layers", []):
        x, y, width, height = _pixel_bbox(layer["bbox"], canvas)
        element = {
            "id": layer["id"],
            "type": layer["type"],
            "role": layer.get("role"),
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "rotation": float(layer.get("rotation", 0)),
            "zIndex": int(layer.get("zIndex", 1)),
            "opacity": float(layer.get("opacity", 1)),
        }
        if layer["type"] == "text":
            style = deepcopy(layer.get("style") or {})
            element.update({
                "content": _content_value(
                    content, layer.get("bindTo"), layer.get("defaultText", "")
                ),
                "fontSize": int(style.get("fontSize", 40)),
                "fontWeight": int(style.get("fontWeight", 400)),
                "fontFamily": style.get("fontId", "sans"),
                "color": style.get("color", "#222222"),
                "textAlign": style.get("textAlign", "left"),
                "verticalAlign": style.get("verticalAlign", "top"),
                "lineHeight": int(style.get(
                    "lineHeight",
                    round(float(style.get("fontSize", 40)) * 1.18),
                )),
                "letterSpacing": float(style.get("letterSpacing", 0)),
            })
        elif layer["type"] == "image":
            if layer.get("bindTo") == "product":
                src = product_url
                element.update(_coordinates(_fit_image((x, y, width, height), product_size)))
            else:
                src = str(layer.get("assetId") or layer.get("src") or "")
                if not src.startswith(("/generated/", "/poster-design-static/")):
                    # P0 keeps unsupported decoration regions in the flattened
                    # background. Rendering an empty placeholder would fail the
                    # local-asset guard.
                    continue
            element["src"] = src
            element["blur"] = int(layer.get("blur", 0))
            element["flipX"] = bool(layer.get("flipX", False))
            element["flipY"] = bool(layer.get("flipY", False))
        elif layer["type"] == "shape":
            element.update(deepcopy(layer.get("style") or {}))
            element.setdefault("shape", "rect")
            element.setdefault("fill", "#ffffff")
        else:
            continue
        elements.append(element)

    return {
        "id": document_id,
        "name": str(template.get("name", "模板海报")),
        "productName": product_name,
        "templateId": str(template.get("templateId", "template_001")),
        "backgroundProvider": "template-instantiator",
        "palette": deepcopy(template.get("style", {}).get("palette", [])),
        "canvas": canvas,
        "elements": elements,
    }


def _coordinates(rect: tuple[int, int, int, int]) -> dict[str, int]:
    return {
        "x": rect[0],
        "y": rect[1],
        "width": rect[2],
        "height": rect[3],
    }

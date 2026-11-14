"""Compile reviewed poster analysis into a reusable template document."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


FIELD_LABELS = {
    "title": "主标题",
    "subtitle": "商品名",
    "productName": "商品名",
    "slogan": "口号",
    "intro": "商品介绍",
    "sellingPoint": "卖点",
    "price": "价格",
    "badge": "徽章",
    "footer": "底部说明",
}


def _require_bbox(value: Any, owner: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{owner} 的 bbox 必须是 [x, y, width, height]。")
    bbox = [float(item) for item in value]
    if any(item < 0 or item > 1 for item in bbox):
        raise ValueError(f"{owner} 的 bbox 必须使用 0 到 1 的归一化坐标。")
    if bbox[2] <= 0 or bbox[3] <= 0:
        raise ValueError(f"{owner} 的 bbox 宽高必须大于 0。")
    if bbox[0] + bbox[2] > 1.000001 or bbox[1] + bbox[3] > 1.000001:
        raise ValueError(f"{owner} 的 bbox 不能超出画布。")
    return [round(item, 6) for item in bbox]


def _field_key(observation: dict[str, Any], index: int) -> str:
    explicit = observation.get("field", {}).get("key")
    if explicit:
        return str(explicit)
    role = str(observation.get("role") or observation.get("roleCandidate") or "")
    if role in FIELD_LABELS:
        return role
    return f"text_{index + 1}"


def _default_style(observation: dict[str, Any], bbox: list[float],
                   canvas: dict[str, Any]) -> dict[str, Any]:
    style = deepcopy(observation.get("style") or {})
    estimated_height = bbox[3] * float(canvas.get("height", 1440))
    style.setdefault("fontId", "sans")
    style.setdefault("fontSize", max(18, round(estimated_height * 0.58)))
    style.setdefault("fontWeight", 700)
    style.setdefault("color", "#222222")
    style.setdefault("textAlign", "left")
    return style


def compile_analysis(analysis: dict[str, Any],
                     template_id: str = "template_001",
                     name: str = "未命名模板") -> dict[str, Any]:
    """Convert reviewed observations into a template without rendering a poster."""
    canvas = deepcopy(analysis.get("canvas") or {})
    if not canvas.get("width") or not canvas.get("height"):
        raise ValueError("PosterAnalysis 缺少画布宽高。")
    observations = analysis.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("PosterAnalysis 至少需要一个观察元素。")

    fields: list[dict[str, Any]] = []
    layers: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    used_keys: set[str] = set()

    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            continue
        element_type = str(observation.get("type", "text"))
        role = str(observation.get("role") or observation.get("roleCandidate") or element_type)
        bbox = _require_bbox(observation.get("bbox"), str(observation.get("id", role)))
        layer_id = str(observation.get("id") or f"layer_{index + 1}")
        layer: dict[str, Any] = {
            "id": layer_id,
            "type": element_type,
            "role": role,
            "bbox": bbox,
            "rotation": float(observation.get("rotation", 0)),
            "zIndex": int(observation.get("zIndex", index + 1)),
            "opacity": float(observation.get("opacity", 1)),
            "sourceObservationId": observation.get("id"),
            "confidence": float(observation.get("confidence", 1.0)),
            "reviewRequired": bool(observation.get("reviewRequired", False)),
        }

        if element_type == "text":
            key = _field_key(observation, index)
            while key in used_keys:
                key = f"{key}_{index + 1}"
            used_keys.add(key)
            replaceable = observation.get("replaceable", True)
            layer["bindTo"] = key if replaceable else None
            layer["style"] = _default_style(observation, bbox, canvas)
            layer["defaultText"] = str(observation.get("text", ""))
            fields.append({
                "key": key,
                "label": observation.get("field", {}).get("label") or FIELD_LABELS.get(
                    role, observation.get("field", {}).get("label", "文本")
                ),
                "type": observation.get("field", {}).get("type", "text"),
                "required": bool(observation.get("field", {}).get("required", replaceable)),
                "maxChars": int(observation.get("field", {}).get("maxChars", 60)),
                "maxLines": int(observation.get("field", {}).get("maxLines", 3)),
                "replaceable": bool(replaceable),
            })
        elif element_type == "image":
            layer["assetId"] = observation.get("assetId") or observation.get("sourceAssetId")
            layer["bindTo"] = "product" if role == "product" else None
            layer["opacity"] = float(observation.get("opacity", 1))
            layer["blur"] = int(observation.get("blur", 0))
            layer["flipX"] = bool(observation.get("flipX", False))
            layer["flipY"] = bool(observation.get("flipY", False))
        elif element_type == "shape":
            layer["style"] = deepcopy(observation.get("style") or {})
        else:
            continue

        layers.append(layer)
        observation_constraints = observation.get("constraints") or {}
        constraints.append({
            "target": layer_id,
            "safeBBox": [round(float(v), 6) for v in observation_constraints.get(
                "safeBBox", bbox
            )],
            "minFontSize": int(observation_constraints.get("minFontSize", 18)),
            "maxFontSize": int(observation_constraints.get("maxFontSize", 220)),
            "allowWrap": bool(observation_constraints.get("allowWrap", True)),
            "allowMove": bool(observation_constraints.get("allowMove", False)),
            "priority": int(observation_constraints.get("priority", 10)),
        })

    if not layers:
        raise ValueError("没有可编译的有效元素。")

    if not any(field.get("key") == "product" for field in fields):
        fields.insert(0, {
            "key": "product",
            "label": "商品图片",
            "type": "image",
            "required": True,
            "maxChars": 0,
            "maxLines": 0,
            "replaceable": True,
        })

    background = deepcopy(analysis.get("background") or {})
    background.setdefault("mode", "image")
    cleanup_masks = list(background.get("cleanupMasks") or [])
    for layer in layers:
        if (
            layer.get("type") == "text"
            and layer.get("bindTo")
            and layer["bbox"] not in cleanup_masks
        ):
            cleanup_masks.append(layer["bbox"])
    background["cleanupMasks"] = cleanup_masks
    if analysis.get("sourceUrl"):
        background.setdefault("sourceUrl", analysis["sourceUrl"])
    return {
        "schemaVersion": 1,
        "templateId": template_id,
        "name": name,
        "canvas": canvas,
        "style": deepcopy(analysis.get("style") or {}),
        "generationPrompt": str(analysis.get("generationPrompt", "")).strip(),
        "background": background,
        "fields": fields,
        "layers": layers,
        "constraints": constraints,
        "source": {
            "analysisId": analysis.get("analysisId"),
            "imageId": analysis.get("imageId"),
        },
    }

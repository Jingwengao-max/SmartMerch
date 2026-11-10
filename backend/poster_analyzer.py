"""First-pass semantic analysis for a reference poster."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat

from ai_copywriter import _data_url, _extract_json, configured as ai_configured


ANALYSIS_PROMPT = """你是海报版式分析器。只返回一个 JSON 对象，不要返回 Markdown。

识别海报中的主要文字块和商品图片区域。坐标必须使用相对整张图片的归一化值，
并使用明确的 left/top/right/bottom 字段，所有值在 0 到 1 之间。

返回结构：
{
  "style": {
    "category": "极简/复古/科技/国潮/清新等",
    "palette": ["#rrggbb", "#rrggbb", "#rrggbb"],
    "tone": "视觉氛围"
  },
  "generationPrompt": "一段可直接交给图像生成模型的中文提示词，描述画面风格、配色、构图、背景材质、光影和装饰元素，并强调不要生成额外文字、Logo或水印",
  "observations": [
    {
      "id": "唯一ID",
      "type": "text 或 image",
      "roleCandidate": "title/subtitle/sellingPoint/price/slogan/footer/badge/product/logo/decoration",
      "text": "文字内容，图片元素留空",
      "bbox": {
        "left": 0.0,
        "top": 0.0,
        "right": 1.0,
        "bottom": 1.0
      },
      "rotation": 0,
      "zIndex": 1,
      "opacity": 1.0,
      "style": {
        "fontCategory": "serif/sans/handwriting/display/calligraphy",
        "fontSize": 48,
        "fontWeight": 700,
        "color": "#rrggbb",
        "textAlign": "left/center/right"
      },
      "confidence": 0.0
    }
  ]
}

要求：
1. 文字内容必须忠实识别，不要扩写。
2. 每个文字块只对应一个语义角色。
3. 商品主体标记为 product。
4. 无法判断的文字角色使用 unknown。
5. bbox 必须包住对应元素的可见区域，不能随意猜测。
"""


def _normalize_bbox(value: Any) -> list[float] | None:
    if isinstance(value, dict):
        left = value.get("left", value.get("x"))
        top = value.get("top", value.get("y"))
        right = value.get("right")
        bottom = value.get("bottom")
        width = value.get("width", value.get("w"))
        height = value.get("height", value.get("h"))
        try:
            if right is not None and bottom is not None:
                x1, y1, x2, y2 = float(left), float(top), float(right), float(bottom)
            else:
                x1, y1 = float(left), float(top)
                x2, y2 = x1 + float(width), y1 + float(height)
        except (TypeError, ValueError):
            return None
    elif isinstance(value, list) and len(value) == 4:
        try:
            x1, y1, third, fourth = (float(item) for item in value)
        except (TypeError, ValueError):
            return None
        # Vision models frequently return [x1,y1,x2,y2] even when asked for
        # [x,y,width,height]. A sum beyond the canvas is a safe corner signal.
        if x1 + third > 1.000001 or y1 + fourth > 1.000001:
            x2, y2 = third, fourth
        else:
            x2, y2 = x1 + third, y1 + fourth
    else:
        return None
    x1 = min(1.0, max(0.0, x1))
    y1 = min(1.0, max(0.0, y1))
    x2 = min(1.0, max(0.0, x2))
    y2 = min(1.0, max(0.0, y2))
    left, right = min(x1, x2), max(x1, x2)
    top, bottom = min(y1, y2), max(y1, y2)
    if right - left <= 0 or bottom - top <= 0:
        return None
    return [
        round(left, 6),
        round(top, 6),
        round(right - left, 6),
        round(bottom - top, 6),
    ]


def _font_id(value: Any) -> str:
    category = str(value or "").strip().lower()
    if any(token in category for token in ("serif", "song", "宋")):
        return "serif"
    if any(token in category for token in ("sans", "hei", "黑")):
        return "sans"
    if any(token in category for token in ("hand", "手写", "文楷")):
        return "hand"
    if any(token in category for token in ("brush", "calligraphy", "书法", "毛笔")):
        return "brush"
    if any(token in category for token in ("display", "装饰", "标题")):
        return "xiaowei"
    return "sans"


def _normalize_text_style(item: dict[str, Any], bbox: list[float],
                          height: int) -> dict[str, Any]:
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    try:
        estimated_size = max(18, round(bbox[3] * height * 0.58))
    except (TypeError, ValueError):
        estimated_size = 40
    try:
        font_size = max(12, min(320, int(style.get("fontSize", estimated_size))))
    except (TypeError, ValueError):
        font_size = estimated_size
    try:
        font_weight = max(100, min(900, int(style.get("fontWeight", 700))))
    except (TypeError, ValueError):
        font_weight = 700
    color = str(style.get("color", "#222222"))
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = "#222222"
    align = str(style.get("textAlign", style.get("align", "left"))).lower()
    if align not in {"left", "center", "right"}:
        align = "left"
    return {
        "fontId": _font_id(style.get("fontCategory", style.get("fontId"))),
        "fontSize": font_size,
        "fontWeight": font_weight,
        "color": color,
        "textAlign": align,
        "lineHeight": max(font_size, int(style.get("lineHeight", round(font_size * 1.18)))),
        "letterSpacing": float(style.get("letterSpacing", 0) or 0),
    }


def _palette(path: Path) -> list[str]:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        image.thumbnail((160, 160))
        quantized = image.quantize(colors=5)
        palette = quantized.getpalette() or []
        counts = quantized.getcolors() or []
    colors: list[str] = []
    for _, index in sorted(counts, reverse=True):
        offset = index * 3
        rgb = tuple(palette[offset:offset + 3])
        if len(rgb) == 3:
            colors.append("#" + "".join(f"{value:02x}" for value in rgb))
    return colors[:3]


def _prepare_vision_image(path: Path, max_edge: int = 1280) -> tuple[Path, tuple[int, int]]:
    """Create a smaller JPEG copy for vision inference while preserving aspect ratio."""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        flattened = Image.new("RGB", image.size, "#ffffff")
        flattened.paste(image, mask=image.getchannel("A"))
    target = path.with_name(f".vision-{uuid.uuid4().hex[:10]}.jpg")
    flattened.save(target, format="JPEG", quality=85, optimize=True)
    return target, flattened.size


def _call_vision(path: Path) -> dict[str, Any]:
    import requests

    endpoint = os.environ["AI_API_URL"].strip().rstrip("/")
    if endpoint.endswith("/v1"):
        endpoint += "/chat/completions"
    elif not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    payload = {
        "model": os.getenv("AI_MODEL", "qwen3-vl-plus").strip(),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "分析这张参考海报并返回结构化 JSON。"},
                {"type": "image_url", "image_url": {"url": _data_url(path)}},
            ]},
        ],
    }
    headers = {
        "Authorization": f"Bearer {os.environ['AI_API_KEY'].strip()}",
        "Content-Type": "application/json",
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if response.status_code == 400:
        payload.pop("response_format", None)
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if not response.ok:
        raise RuntimeError(
            f"视觉模型接口返回 HTTP {response.status_code}：{response.text[:800]}"
        )
    content = response.json()["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(
            str(item.get("text", "")) for item in content if isinstance(item, dict)
        )
    return _extract_json(content)


def analyze_reference(path: Path) -> dict[str, Any]:
    if not ai_configured():
        raise RuntimeError("尚未配置视觉模型，暂时无法自动解析参考海报。")
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        average = tuple(round(value) for value in ImageStat.Stat(image).mean)
    max_edge = max(640, int(os.getenv("VISION_MAX_EDGE", "1280")))
    vision_path, vision_size = _prepare_vision_image(path, max_edge)
    try:
        raw = _call_vision(vision_path)
    finally:
        vision_path.unlink(missing_ok=True)
    style = raw.get("style") if isinstance(raw.get("style"), dict) else {}
    palette = [str(color) for color in style.get("palette", []) if re.fullmatch(
        r"#[0-9a-fA-F]{6}", str(color)
    )][:5]
    if not palette:
        palette = _palette(path)
    observations = []
    for index, item in enumerate(raw.get("observations", [])):
        if not isinstance(item, dict):
            continue
        bbox = _normalize_bbox(item.get("bbox"))
        if bbox is None:
            continue
        element_type = str(item.get("type", "text"))
        if element_type not in {"text", "image", "shape"}:
            element_type = "text"
        style = _normalize_text_style(item, bbox, height) if element_type == "text" else {}
        try:
            rotation = float(item.get("rotation", 0) or 0)
        except (TypeError, ValueError):
            rotation = 0.0
        try:
            z_index = int(item.get("zIndex", index + 1) or index + 1)
        except (TypeError, ValueError):
            z_index = index + 1
        try:
            opacity = max(0.0, min(1.0, float(item.get("opacity", 1))))
        except (TypeError, ValueError):
            opacity = 1.0
        observations.append({
            "id": str(item.get("id") or f"{element_type}_{index + 1}"),
            "type": element_type,
            "roleCandidate": str(item.get("roleCandidate", "unknown")),
            "text": str(item.get("text", "")).strip(),
            "bbox": bbox,
            "rotation": rotation,
            "zIndex": z_index,
            "opacity": opacity,
            "style": style,
            "confidence": max(
                0.0, min(1.0, float(item.get("confidence", 0.5) or 0.5))
            ),
            "reviewRequired": float(item.get("confidence", 0.5) or 0.5) < 0.75,
        })
    return {
        "schemaVersion": 1,
        "analysisId": uuid.uuid4().hex[:12],
        "imageId": path.parent.name,
        "canvas": {"width": width, "height": height},
        "style": {
            "category": str(style.get("category", "待确认")),
            "palette": palette,
            "tone": str(style.get("tone", "待确认")),
            "average": average,
        },
        "analysisMeta": {
            "sourceSize": [width, height],
            "visionSize": list(vision_size),
            "visionMaxEdge": max_edge,
        },
        "generationPrompt": str(raw.get("generationPrompt", "")).strip()[:2000],
        "background": {
            "mode": "image",
            "sourceImageId": path.parent.name,
            "cleanupMasks": [],
        },
        "observations": observations,
    }

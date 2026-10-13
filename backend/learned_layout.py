"""Instantiate editable posters from the learned bakery editorial layout."""

from __future__ import annotations

import colorsys
import json
import math
import re
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from layout_engine import CANVAS, load_font


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "bakery_editorial_layout.json"


def load_model(path: Path = MODEL_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"版式模型不存在，请先运行 python train_layout_model.py：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _region(model: dict[str, Any], name: str) -> tuple[int, int, int, int]:
    x, y, width, height = model["regions"][name]
    return round(x * CANVAS[0]), round(y * CANVAS[1]), round(width * CANVAS[0]), round(height * CANVAS[1])


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, value)):02x}" for value in rgb)


def adaptive_palette(mean_rgb: tuple[int, int, int]) -> dict[str, str]:
    r, g, b = (value / 255 for value in mean_rgb)
    h, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    saturation = max(0.42, min(0.68, saturation * 1.25))
    accent = colorsys.hls_to_rgb(h, max(0.32, min(0.55, lightness * 0.82)), saturation)
    soft = colorsys.hls_to_rgb(h, 0.82, min(0.42, saturation * 0.55))
    dark = colorsys.hls_to_rgb(h, 0.24, min(0.48, saturation * 0.65))
    return {
        "accent": _hex(tuple(round(value * 255) for value in accent)),
        "soft": _hex(tuple(round(value * 255) for value in soft)),
        "dark": _hex(tuple(round(value * 255) for value in dark)),
        "paper": "#faf5ed",
    }


def _product_doodle(product: Image.Image, color: str, size: tuple[int, int]) -> Image.Image:
    """Convert the uploaded product silhouette into a compact line drawing."""
    alpha = product.convert("RGBA").getchannel("A")
    bounds = alpha.getbbox()
    if bounds:
        alpha = alpha.crop(bounds)
    alpha.thumbnail(size, Image.Resampling.LANCZOS)
    edge = alpha.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5))
    edge = edge.point(lambda value: 220 if value > 24 else 0)
    doodle = Image.new("RGBA", edge.size, color)
    doodle.putalpha(edge)
    return doodle


def build_style_background(target: Path, palette: dict[str, str], product: Image.Image | None = None) -> None:
    width, height = CANVAS
    image = Image.new("RGB", CANVAS, palette["paper"])
    draw = ImageDraw.Draw(image)
    soft = palette["soft"]
    accent = palette["accent"]

    # The organic product backdrop and scalloped footer are the two strongest
    # non-textual patterns shared by all four references.
    points = []
    cx, cy, rx, ry = width * 0.52, height * 0.63, width * 0.42, height * 0.25
    for index in range(96):
        angle = index / 96 * math.tau
        wobble = 1 + 0.055 * math.sin(angle * 5) + 0.035 * math.cos(angle * 3)
        points.append((cx + math.cos(angle) * rx * wobble, cy + math.sin(angle) * ry * wobble))
    draw.polygon(points, fill=soft)

    badge_cx, badge_cy = round(width * 0.84), round(height * 0.42)
    badge_points = []
    for index in range(32):
        angle = index / 32 * math.tau
        radius_value = 132 if index % 2 == 0 else 112
        badge_points.append((
            badge_cx + math.cos(angle) * radius_value,
            badge_cy + math.sin(angle) * radius_value,
        ))
    draw.polygon(badge_points, fill=accent)

    footer_top = round(height * 0.87)
    draw.rectangle((0, footer_top + 12, width, height), fill=soft)
    radius = 12
    for x in range(-radius, width + radius, radius * 2):
        draw.ellipse((x, footer_top, x + radius * 2, footer_top + radius * 2), fill=soft)
    for x, y in ((86, 430), (930, 270), (902, 1050), (110, 850)):
        draw.line((x - 12, y, x + 12, y), fill=accent, width=3)
        draw.line((x, y - 12, x, y + 12), fill=accent, width=3)
    # Reference posters frame the launch label with two restrained rules.
    launch_x, launch_y, launch_width, launch_height = _region(load_model(), "launch")
    rule_inset = 24
    draw.line(
        (launch_x + rule_inset, launch_y + 5, launch_x + launch_width - rule_inset, launch_y + 5),
        fill=palette["dark"], width=2,
    )
    draw.line(
        (
            launch_x + rule_inset, launch_y + launch_height - 7,
            launch_x + launch_width - rule_inset, launch_y + launch_height - 7,
        ),
        fill=palette["dark"], width=2,
    )
    if product is not None:
        doodle = _product_doodle(product, accent, (118, 118)).rotate(
            -8, expand=True, resample=Image.Resampling.BICUBIC
        )
        image.paste(doodle, (858, 330), doodle)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, quality=94)


def _text_element(element_id: str, role: str, content: str, rect: tuple[int, int, int, int],
                  font_size: int, color: str, z_index: int = 3, weight: int = 700,
                  align: str = "left", vertical_align: str = "top") -> dict[str, Any]:
    x, y, width, height = rect
    return {
        "id": element_id, "type": "text", "role": role, "content": content,
        "x": x, "y": y, "width": width, "height": height,
        "fontSize": font_size, "fontWeight": weight, "color": color,
        "textAlign": align, "verticalAlign": vertical_align, "rotation": 0, "zIndex": z_index,
    }


def _single_line_font_size(text: str, max_width: int, start: int, minimum: int) -> int:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start, minimum - 1, -2):
        box = probe.textbbox((0, 0), text, font=load_font(size, 700), stroke_width=1)
        if box[2] - box[0] <= max_width:
            return size
    return minimum


def _wrap_copy(text: str, width: int) -> str:
    lines: list[str] = []
    for source_line in text.splitlines() or [text]:
        lines.extend(textwrap.wrap(source_line.strip(), width=width) or [""])
    return "\n".join(lines[:4])


def create_document(job_id: str, product_url: str, background_url: str,
                    product_size: tuple[int, int], mean_rgb: tuple[int, int, int],
                    title: str, feature: str, price: str = "",
                    selling_points: list[str] | None = None, footer: str = "",
                    launch_text: str = "新品上市", badge_text: str = "NEW!") -> dict[str, Any]:
    model = load_model()
    palette = adaptive_palette(mean_rgb)
    product_box = _region(model, "product")
    px, py, pw, ph = product_box
    source_ratio = product_size[0] / max(1, product_size[1])
    target_ratio = pw / ph
    if source_ratio > target_ratio:
        render_w, render_h = pw, round(pw / source_ratio)
    else:
        render_h, render_w = ph, round(ph * source_ratio)
    product_rect = (px + (pw - render_w) // 2, py + (ph - render_h) // 2, render_w, render_h)

    hero = re.sub(r"\s+", " ", title.strip()) or "NEW PRODUCT"
    cn_title = feature.strip() or "匠心新品 好味登场"
    footer_copy = footer.strip() or "品牌口号待补充"
    points = [point.strip() for point in (selling_points or []) if point.strip()][:3]
    hero_font_size = _single_line_font_size(hero, 920, 132, 74)
    cn_font_size = _single_line_font_size(cn_title, 850, 82, 62)
    elements: list[dict[str, Any]] = [
        {
            "id": "product", "type": "image", "role": "product", "src": product_url,
            "x": product_rect[0], "y": product_rect[1], "width": product_rect[2],
            "height": product_rect[3], "rotation": 0, "zIndex": 2,
        },
        _text_element("hero-title", "heroTitle", hero, (54, 78, 930, 168), hero_font_size, palette["accent"]),
        _text_element("cn-title", "title", cn_title, (54, 244, 850, 128), cn_font_size, palette["accent"]),
        _text_element(
            "launch", "label", launch_text.strip() or "新品上市", _region(model, "launch"),
            38, palette["dark"], align="center", vertical_align="middle",
        ),
        _text_element("badge", "badge", badge_text.strip() or "NEW!", _region(model, "badge"), 60, "#ffffff", z_index=5, align="center", vertical_align="middle"),
        _text_element(
            "footer-brand", "footer", footer_copy, (70, 1258, 940, 182),
            64, palette["dark"], align="center", vertical_align="middle",
        ),
    ]
    point_layouts = {
        1: [((80, 1040, 360, 150), 32, 12)],
        2: [(_region(model, "leftDetail"), 30, 9), (_region(model, "rightDetail"), 30, 5)],
        3: [(_region(model, "leftCallout"), 30, 9), (_region(model, "leftDetail"), 30, 9), (_region(model, "rightDetail"), 30, 5)],
    }
    for index, (rect, font_size, wrap_width) in enumerate(point_layouts.get(len(points), [])):
        elements.append(_text_element(
            f"selling-point-{index + 1}", "sellingPoint", _wrap_copy(points[index], wrap_width),
            rect, font_size, palette["dark"], z_index=4,
        ))
    if price.strip():
        elements.append(_text_element("price", "price", price.strip(), (820, 1080, 200, 80), 54, palette["accent"], z_index=5, align="right"))

    return {
        "id": f"{job_id}_learned",
        "name": "AI 学习版式 · 烘焙编辑风",
        "productName": title.strip() or cn_title,
        "templateId": "learned-bakery-editorial-v1",
        "backgroundProvider": "learned-style-renderer",
        "layoutModel": {"type": model["modelType"], "version": model["modelVersion"], "trainedSamples": model["trainedSamples"]},
        "palette": palette,
        "canvas": {"width": CANVAS[0], "height": CANVAS[1], "backgroundImage": background_url},
        "elements": elements,
    }

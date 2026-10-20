"""Instantiate editable posters from the learned bakery editorial layout."""

from __future__ import annotations

import colorsys
import json
import math
import re
import statistics
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from layout_engine import CANVAS, load_font
from style_specs import get_style_spec


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "bakery_editorial_layout.json"

# 风格 → 版式模型文件列表。一个风格可以有多套版式（例如 4 张参考图各自不同）。
STYLE_MODELS = {
    "editorial": ["bakery_editorial_layout.json"],
    "minimal": ["minimal_layout.json"],
    "style2": [f"style2_layout_{index}.json" for index in range(1, 5)],
}
# 兼容旧调用：只取该风格的第一套版式。
MODEL_FILES = {key: files[0] for key, files in STYLE_MODELS.items()}


def load_model(path: Path = MODEL_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"版式模型不存在，请先运行 python train_layout_model.py：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_models_for(style: str = "editorial") -> list[dict[str, Any]]:
    """按风格加载全部版式模型；未知风格直接报错，避免静默回退。"""
    filenames = STYLE_MODELS.get(style)
    if not filenames:
        raise ValueError(f"未知风格：{style}")
    return [load_model(ROOT / "models" / filename) for filename in filenames]


def load_model_for(style: str = "editorial") -> dict[str, Any]:
    """取该风格的第一套版式（兼容旧调用）。"""
    return load_models_for(style)[0]


def _region(model: dict[str, Any], name: str) -> tuple[int, int, int, int]:
    x, y, width, height = model["regions"][name]
    return round(x * CANVAS[0]), round(y * CANVAS[1]), round(width * CANVAS[0]), round(height * CANVAS[1])


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, value)):02x}" for value in rgb)


def adaptive_palette(mean_rgb: tuple[int, int, int], paper: str = "#faf5ed") -> dict[str, str]:
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
        "paper": paper,
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


def build_style_background(target: Path, palette: dict[str, str], product: Image.Image | None = None,
                           model: dict[str, Any] | None = None,
                           style_key: str = "editorial",
                           variant_index: int | None = None) -> None:
    """按风格模型的开关绘制背景；位置全部来自模型里归一化的 regions。"""
    model = model or load_model_for(style_key)
    style = model.get("style", {})
    spec = get_style_spec(style_key, variant_index)
    layout = spec.get("layout") or {}
    width, height = CANVAS
    image = Image.new("RGB", CANVAS, palette["paper"])
    draw = ImageDraw.Draw(image)
    soft = palette["soft"]
    accent = palette["accent"]
    haze = (spec.get("background") or {}).get("haze")
    if haze:
        haze_color = _resolve_color(str(haze.get("color", "accent")), palette)
        haze_rgb = _rgb_tuple(haze_color)
        haze_alpha = round(float(haze.get("opacity", 0.14)) * 255)
        haze_top = round(CANVAS[1] * float(haze.get("from", 0.5)))
        haze_bottom = round(CANVAS[1] * float(haze.get("to", 0.8)))
        band = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(band).rounded_rectangle(
            (-80, haze_top, width + 80, haze_bottom),
            radius=max(20, (haze_bottom - haze_top) // 2),
            fill=(*haze_rgb, haze_alpha),
        )
        band = band.filter(ImageFilter.GaussianBlur(int(haze.get("blur", 80))))
        image = Image.alpha_composite(image.convert("RGBA"), band).convert("RGB")
        draw = ImageDraw.Draw(image)
    organic = bool(style.get("organicBackdrop", True))

    # The organic product backdrop and scalloped footer are the two strongest
    # non-textual patterns shared by all four references.
    if organic:
        points = []
        cx, cy, rx, ry = width * 0.52, height * 0.63, width * 0.42, height * 0.25
        for index in range(96):
            angle = index / 96 * math.tau
            wobble = 1 + 0.055 * math.sin(angle * 5) + 0.035 * math.cos(angle * 3)
            points.append((cx + math.cos(angle) * rx * wobble, cy + math.sin(angle) * ry * wobble))
        draw.polygon(points, fill=soft)

    if product is not None and style.get("productShadow"):
        px, py, pw, ph = _product_rect(
            model, product.size,
            float(layout.get("productMinLeft", 0.0)),
            float(layout.get("productScale", 1.0)),
            float(layout.get("productShrink", 1.0)),
        )
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_w = pw * 0.82
        shadow_h = max(18, int(ph * 0.07))
        center_x = px + pw / 2
        bottom = py + ph - shadow_h * 0.25
        shadow_draw.ellipse(
            (center_x - shadow_w / 2, bottom - shadow_h / 2,
             center_x + shadow_w / 2, bottom + shadow_h / 2),
            fill=(30, 25, 20, 65),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(26))
        image = Image.alpha_composite(image.convert("RGBA"), shadow).convert("RGB")
        draw = ImageDraw.Draw(image)

    regions = model.get("regions", {})
    badge_cx = badge_cy = 0
    if "badge" in regions:
        badge_x, badge_y, badge_width, badge_height = _region(model, "badge")
        badge_cx = badge_x + badge_width // 2
        badge_cy = badge_y + badge_height // 2
        badge_base = min(badge_width, badge_height) / 2
        if style.get("badgeShape", "star") == "circle":
            radius_value = round(badge_base)
            draw.ellipse(
                (badge_cx - radius_value, badge_cy - radius_value,
                 badge_cx + radius_value, badge_cy + radius_value),
                fill=accent,
            )
        else:
            badge_points = []
            for index in range(32):
                angle = index / 32 * math.tau
                radius_value = badge_base * (1.18 if index % 2 == 0 else 0.95)
                badge_points.append((
                    badge_cx + math.cos(angle) * radius_value,
                    badge_cy + math.sin(angle) * radius_value,
                ))
            draw.polygon(badge_points, fill=accent)

    if "footer" in regions:
        _, footer_top, _, _ = _region(model, "footer")
        if style.get("footerScallop", True):
            draw.rectangle((0, footer_top + 12, width, height), fill=soft)
            radius = 12
            for x in range(-radius, width + radius, radius * 2):
                draw.ellipse((x, footer_top, x + radius * 2, footer_top + radius * 2), fill=soft)
        else:
            draw.rectangle((0, footer_top, width, height), fill=soft)
            draw.line((70, footer_top, width - 70, footer_top), fill=accent, width=2)

    if organic:
        for x, y in ((86, 430), (930, 270), (902, 1050), (110, 850)):
            draw.line((x - 12, y, x + 12, y), fill=accent, width=3)
            draw.line((x, y - 12, x, y + 12), fill=accent, width=3)
    # Reference posters frame the launch label with two restrained rules.
    if "launch" in regions:
        launch_x, launch_y, launch_width, launch_height = _region(model, "launch")
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
    if product is not None and style.get("productDoodle", True) and "badge" in regions:
        doodle = _product_doodle(product, accent, (118, 118)).rotate(
            -8, expand=True, resample=Image.Resampling.BICUBIC
        )
        doodle_x = min(width - doodle.width - 40, badge_cx + 60)
        doodle_y = max(40, badge_cy - doodle.height - 80)
        image.paste(doodle, (doodle_x, doodle_y), doodle)
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


def _single_line_font_size(text: str, max_width: int, start: int, minimum: int,
                           weight: int = 700) -> int:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start, minimum - 1, -2):
        box = probe.textbbox((0, 0), text, font=load_font(size, weight), stroke_width=1)
        if box[2] - box[0] <= max_width:
            return size
    return minimum


def _wrap_copy(text: str, width: int, max_lines: int = 4) -> str:
    lines: list[str] = []
    for source_line in text.splitlines() or [text]:
        lines.extend(textwrap.wrap(source_line.strip(), width=width) or [""])
    return "\n".join(lines[:max_lines])


def _wrap_pixels(text: str, font, max_width: int, max_lines: int = 8) -> str:
    """按像素宽度折行，保证文字不会超出浮窗。"""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        current = ""
        for character in paragraph:
            trial = current + character
            if probe.textlength(trial, font=font) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = character
        if current:
            lines.append(current)
    return "\n".join(lines[:max_lines])


def _symmetric_rects(rects: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """把一组卖点框改成关于画布中心轴对称、间距相等。"""
    count = len(rects)
    if count < 2:
        return rects
    xs = [rect[0] for rect in rects]
    ys = [rect[1] for rect in rects]
    if len(set(ys)) == 1:
        width = max(rect[2] for rect in rects)
        height = max(rect[3] for rect in rects)
        gaps = [rects[i + 1][0] - (rects[i][0] + rects[i][2]) for i in range(count - 1)]
        gap = round(statistics.median(gaps)) if gaps else 0
        total = count * width + (count - 1) * gap
        start = round((CANVAS[0] - total) / 2)
        return [(start + i * (width + gap), ys[0], width, height) for i in range(count)]
    if len(set(xs)) == 1:
        width = max(rect[2] for rect in rects)
        height = max(rect[3] for rect in rects)
        gaps = [rects[i + 1][1] - (rects[i][1] + rects[i][3]) for i in range(count - 1)]
        gap = round(statistics.median(gaps)) if gaps else 0
        total = count * height + (count - 1) * gap
        start = round((CANVAS[1] - total) / 2)
        return [(xs[0], start + i * (height + gap), width, height) for i in range(count)]
    return rects


def _apply_pad(rect: tuple[int, int, int, int], pad) -> tuple[int, int, int, int]:
    if not pad:
        return rect
    left, top, right, bottom = (int(value) for value in pad)
    x, y, width, height = rect
    return (
        x + left, y + top,
        max(1, width - left - right), max(1, height - top - bottom),
    )


def _resolve_color(value: str, palette: dict[str, str]) -> str:
    if value == "accent-dark":
        return _darken(palette.get("accent", "#2b2723"), 0.12)
    return palette.get(value, value)


def _rgb_tuple(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))


def _hex_color(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(value))) for value in rgb)


def _blend(color: str, target: tuple[int, int, int], amount: float) -> str:
    source = _rgb_tuple(color)
    return _hex_color(tuple(
        source[index] + (target[index] - source[index]) * amount for index in range(3)
    ))


def _desaturate(color: str, amount: float = 0.55) -> str:
    red, green, blue = _rgb_tuple(color)
    gray = round(0.299 * red + 0.587 * green + 0.114 * blue)
    return _blend(color, (gray, gray, gray), amount)


def _darken(color: str, amount: float = 0.22) -> str:
    return _blend(color, (0, 0, 0), amount)


def _product_rect(model: dict[str, Any], product_size: tuple[int, int],
                  min_left_ratio: float = 0.0,
                  scale: float = 1.0,
                  shrink: float = 1.0) -> tuple[int, int, int, int]:
    px, py, pw, ph = _region(model, "product")
    min_left = round(CANVAS[0] * min_left_ratio)
    if min_left > px:
        # 商品整体限制在中轴线右侧，必要时等比缩小。
        px = min_left
        pw = max(1, CANVAS[0] - min_left)
    source_ratio = product_size[0] / max(1, product_size[1])
    target_ratio = pw / ph
    if source_ratio > target_ratio:
        render_w, render_h = pw, round(pw / source_ratio)
    else:
        render_h, render_w = ph, round(ph * source_ratio)
    if scale != 1.0:
        render_w = round(render_w * scale)
        render_h = round(render_h * scale)
    left = px + (pw - render_w) // 2
    top = py + (ph - render_h) // 2
    if shrink != 1.0:
        shrunk_w = round(render_w * shrink)
        shrunk_h = round(render_h * shrink)
        # 右下角固定，只收左上角。
        left += render_w - shrunk_w
        top += render_h - shrunk_h
        render_w, render_h = shrunk_w, shrunk_h
    left = max(0, min(CANVAS[0] - render_w, left))
    top = max(0, min(CANVAS[1] - render_h, top))
    return (left, top, render_w, render_h)


def _partition(tokens: list[str], parts: int) -> list[list[str]]:
    """把 tokens 连续切成 parts 段，使最长一段的字符数最小。"""
    count = len(tokens)
    parts = max(1, min(parts, count))
    prefix = [0]
    for token in tokens:
        prefix.append(prefix[-1] + len(token))
    inf = float("inf")
    dp = [[inf] * (parts + 1) for _ in range(count + 1)]
    cut = [[0] * (parts + 1) for _ in range(count + 1)]
    dp[0][0] = 0
    for part in range(1, parts + 1):
        for end in range(1, count + 1):
            for start in range(part - 1, end):
                value = max(dp[start][part - 1], prefix[end] - prefix[start])
                if value < dp[end][part]:
                    dp[end][part] = value
                    cut[end][part] = start
    groups: list[list[str]] = []
    end, part = count, parts
    while part > 0:
        start = cut[end][part]
        groups.append(tokens[start:end])
        end, part = start, part - 1
    return groups[::-1]


def _split_title(text: str, line_count: int = 3) -> list[str]:
    """按语义尽量均衡地拆行：英文按词、中文按字，短标题自动少拆。"""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    if " " in cleaned:
        tokens = cleaned.split(" ")
        separator = " "
    else:
        tokens = [character for character in cleaned if not character.isspace()]
        separator = ""
    if len(tokens) <= 1:
        return [cleaned]
    # 尽量按要求行数拆；标题本身短于行数时按实际字数拆。
    parts = min(line_count, len(tokens))
    groups = _partition(tokens, parts)
    return [separator.join(group) for group in groups if group]


def _fit_lines(lines: list[str], rect: tuple[int, int, int, int],
               weight: int, family: str | None) -> tuple[int, int, float]:
    """找出能放进标题框的最大字号；保持正常字距，不用拉伸来填满。"""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    usable_width = rect[2] * 0.96
    usable_height = rect[3] * 0.96
    for size in range(240, 11, -1):
        font = load_font(size, weight, family)
        widths = [probe.textlength(line, font=font) for line in lines]
        # 行距压到最小（1.0 倍字号），字距保持 0。
        line_height = size
        if max(widths or [0]) <= usable_width and line_height * len(lines) <= usable_height:
            return size, line_height, 0.0
    return 14, round(14 * 1.12), 0.0


def create_document(job_id: str, product_url: str, background_url: str,
                    product_size: tuple[int, int], mean_rgb: tuple[int, int, int],
                    copy: dict[str, Any], style: str = "editorial",
                    model: dict[str, Any] | None = None,
                    variant_index: int = 0, variant_count: int = 1) -> dict[str, Any]:
    """按风格的字段配置生成图层：字段、区域、字号、层级全部来自 style_specs。"""
    model = model or load_model_for(style)
    spec = get_style_spec(style, variant_index)
    layout = spec.get("layout") or {}
    style_flags = model.get("style", {})
    palette = adaptive_palette(mean_rgb)
    product_rect = _product_rect(
        model, product_size,
        float(layout.get("productMinLeft", 0.0)),
        float(layout.get("productScale", 1.0)),
        float(layout.get("productShrink", 1.0)),
    )

    oversized = bool(style_flags.get("oversizedHeadline", True))
    elements: list[dict[str, Any]] = [
        {
            "id": "product", "type": "image", "role": "product", "src": product_url,
            "x": product_rect[0], "y": product_rect[1], "width": product_rect[2],
            "height": product_rect[3], "rotation": 0, "zIndex": 2,
        },
    ]
    point_rects: dict[str, list[tuple[int, int, int, int]]] = {}

    for field in spec["fields"]:
        key = field["key"]
        raw = copy.get(key)
        if field.get("attachTo"):
            base_rects = point_rects.get(field["attachTo"], [])
            values = [str(item).strip() for item in (raw or []) if str(item).strip()]
            start = int(field.get("font", 30))
            minimum = int(field.get("minFont", 16))
            weight = int(field.get("weight", 400))
            for index, (rect, value) in enumerate(zip(base_rects, values)):
                font_size = _single_line_font_size(value, rect[2], start, minimum, weight)
                spread = int(field.get("spread", 0))
                en_rect = (
                    rect[0] - spread,
                    rect[1] + rect[3] + int(field.get("gap", 3)),
                    rect[2] + spread * 2,
                    round(font_size * 1.5),
                )
                elements.append(_text_element(
                    f"{field.get('id', key)}-{index + 1}",
                    field.get("role", key), value, en_rect, font_size,
                    _resolve_color(field.get("color", "dark"), palette),
                    z_index=int(field.get("zIndex", 4)),
                    weight=weight,
                    align=field.get("align", "center"),
                    vertical_align="top",
                ))
            continue
        if field["kind"] == "text":
            content = str(raw or "").strip() or spec["defaults"].get(key, "")
            if not content:
                continue
            if not field.get("wrap") and not field.get("lines"):
                content = re.sub(r"\s+", " ", content)
            rect = _apply_pad(_region(model, field["regions"][0]), field.get("pad"))
            expand = field.get("expand")
            if expand:
                rect = (
                    rect[0] - int(expand[0]), rect[1] - int(expand[1]),
                    rect[2] + int(expand[0]) + int(expand[2]),
                    rect[3] + int(expand[1]) + int(expand[3]),
                )
            offset = field.get("offset")
            if offset:
                rect = (
                    rect[0] + int(offset[0]), rect[1] + int(offset[1]),
                    rect[2], rect[3],
                )
            weight = int(field.get("weight", 700))
            family = field.get("fontFamily")
            font_spec = field["font"]
            extras: dict[str, Any] = {}
            if field.get("lines"):
                lines = _split_title(content, int(field["lines"]))
                content = "\n".join(lines)
                if field.get("fillBox"):
                    font_size, line_height, spacing = _fit_lines(lines, rect, weight, family)
                    font_scale = float(field.get("fontScale", 1.0))
                    if font_scale != 1.0:
                        font_size = max(12, round(font_size * font_scale))
                        line_height = round(line_height * font_scale)
                    extras["lineHeight"] = line_height
                    extras["letterSpacing"] = spacing
                else:
                    longest = max(lines, key=len) if lines else content
                    start, minimum = font_spec if isinstance(font_spec, (list, tuple)) else (font_spec, font_spec)
                    font_size = _single_line_font_size(longest, rect[2], int(start), int(minimum), weight)
            elif isinstance(font_spec, (list, tuple)):
                start, minimum = font_spec
                if "compactFont" in field and not oversized:
                    start, minimum = field["compactFont"]
                if field.get("wrap"):
                    # 换行字段按设定字号折行，不能按整段文字宽度缩字号。
                    font_size = int(start)
                else:
                    font_size = _single_line_font_size(content, rect[2], int(start), int(minimum), weight)
            else:
                font_size = int(font_spec)
            if field.get("wrap"):
                wrap_font = load_font(font_size, weight, family)
                content = _wrap_pixels(content, wrap_font, rect[2], int(field.get("maxLines", 8)))
            if field.get("stripPunctuation"):
                content = re.sub(r"[，,、；;。.!！?？]", "", content).strip()

            # 浮窗按实际文字块自适应，保证包住所有字。
            panel = field.get("panel")
            if panel:
                measure_font = load_font(font_size, weight, family)
                probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
                block_lines = content.splitlines() or [""]
                line_height = int(extras.get("lineHeight") or round(font_size * 1.18))
                block_width = max(
                    (probe.textlength(item, font=measure_font) for item in block_lines),
                    default=0,
                )
                block_height = line_height * len(block_lines)
                align_mode = field.get("align", "left")
                vertical_mode = field.get("verticalAlign", "top")
                text_x = rect[0]
                if align_mode == "center":
                    text_x = rect[0] + max(0, (rect[2] - block_width) / 2)
                elif align_mode == "right":
                    text_x = rect[0] + max(0, rect[2] - block_width)
                text_y = rect[1]
                if vertical_mode == "middle":
                    text_y = rect[1] + max(0, (rect[3] - block_height) / 2)
                elif vertical_mode == "bottom":
                    text_y = rect[1] + max(0, rect[3] - block_height)
                panel_pad = list(panel.get("pad") or [0, 0, 0, 0])
                if panel.get("icon"):
                    # 左侧留出图标位，避免角标压住文字。
                    panel_pad[0] += 38
                panel_x = round(text_x) - int(panel_pad[0])
                panel_y = round(text_y) - int(panel_pad[1])
                panel_z = int(field.get("zIndex", 3)) - 1
                elements.append({
                    "id": f"{field.get('id', key)}-panel",
                    "type": "shape", "role": "panel", "shape": "rect",
                    "fill": panel.get("fill", "#ffffff"),
                    "opacity": float(panel.get("opacity", 0.55)),
                    "radius": int(panel.get("radius", 16)),
                    "x": panel_x,
                    "y": panel_y,
                    "width": round(block_width) + int(panel_pad[0]) + int(panel_pad[2]),
                    "height": round(block_height) + int(panel_pad[1]) + int(panel_pad[3]),
                    "rotation": 0, "zIndex": panel_z,
                })
                if panel.get("icon"):
                    elements.append({
                        "id": f"{field.get('id', key)}-icon",
                        "type": "shape", "role": "icon", "shape": "tech-corner",
                        "fill": palette["accent"], "opacity": 0.95,
                        "x": panel_x + 12, "y": panel_y + 12,
                        "width": 26, "height": 26,
                        "rotation": 0, "zIndex": panel_z,
                    })
            element = _text_element(
                field.get("id", key), field.get("role", key), content, rect, font_size,
                _resolve_color(field.get("color", "dark"), palette),
                z_index=int(field.get("zIndex", 3)), weight=weight,
                align=field.get("align", "left"),
                vertical_align=field.get("verticalAlign", "top"),
            )
            if family:
                element["fontFamily"] = family
            element.update(extras)
            emboss = field.get("emboss")
            if emboss:
                offset = int(emboss.get("offset", 6))
                shadow = {**element}
                shadow["id"] = f"{element['id']}-emboss"
                shadow["role"] = f"{element.get('role', key)}-emboss"
                shadow["x"] = element["x"] + offset
                shadow["y"] = element["y"] + offset
                shadow["color"] = _desaturate(element["color"], float(emboss.get("gray", 0.55)))
                shadow["opacity"] = float(emboss.get("opacity", 0.45))
                shadow["zIndex"] = max(0, int(element["zIndex"]) - 1)
                elements.append(shadow)
            elements.append(element)
            continue

        points = [str(item).strip() for item in (raw or []) if str(item).strip()]
        points = points[: int(field.get("maxItems", 3))]
        layouts = field["layouts"].get(len(points), [])
        rects = [_region(model, layout[0]) for layout in layouts]
        if field.get("symmetric"):
            rects = _symmetric_rects(rects)
        point_rects[key] = rects
        for index, (layout, rect) in enumerate(zip(layouts, rects)):
            _, font_size, wrap_chars, max_lines = layout
            glow = field.get("glow")
            if glow:
                glow_pad = int(glow.get("pad", 10))
                glow_base = _resolve_color(field.get("color", "dark"), palette)
                if glow.get("lighten") is not None:
                    glow_color = _blend(glow_base, (255, 255, 255), float(glow["lighten"]))
                else:
                    glow_color = _darken(glow_base, float(glow.get("darken", 0.15)))
                elements.append({
                    "id": f"{key}-{index + 1}-glow",
                    "type": "shape", "role": "glow", "shape": "soft-shadow",
                    "fill": glow_color,
                    "opacity": float(glow.get("opacity", 0.18)),
                    "blur": int(glow.get("blur", 20)),
                    "x": rect[0] - glow_pad, "y": rect[1] - glow_pad,
                    "width": rect[2] + glow_pad * 2, "height": rect[3] + glow_pad * 2,
                    "rotation": 0, "zIndex": max(0, int(field.get("zIndex", 4)) - 1),
                })
            point_element = _text_element(
                f"{key}-{index + 1}", field.get("role", key),
                _wrap_copy(points[index], int(wrap_chars), int(max_lines)),
                rect, int(font_size),
                _resolve_color(field.get("color", "dark"), palette),
                z_index=int(field.get("zIndex", 4)),
                weight=int(field.get("weight", 700)),
                align=field.get("align", "left"),
                vertical_align=field.get("verticalAlign", "top"),
            )
            point_shadow = field.get("shadow")
            if point_shadow:
                offset = int(point_shadow.get("offset", 3))
                tinted = {**point_element}
                tinted["id"] = f"{point_element['id']}-shadow"
                tinted["role"] = f"{point_element.get('role', key)}-shadow"
                tinted["x"] = point_element["x"] + offset
                tinted["y"] = point_element["y"] + offset
                tinted["color"] = _darken(point_element["color"], float(point_shadow.get("darken", 0.22)))
                tinted["opacity"] = float(point_shadow.get("opacity", 0.3))
                tinted["zIndex"] = max(0, int(point_element["zIndex"]) - 1)
                elements.append(tinted)
            elements.append(point_element)

    product_name = ""
    name_field = spec.get("productNameField")
    if name_field:
        product_name = str(copy.get(name_field) or "").strip()
    if not product_name:
        product_name = next(
            (str(value).strip() for value in copy.values()
             if isinstance(value, str) and str(value).strip()),
            "",
        )

    return {
        "id": f"{job_id}_learned_{variant_index}",
        "name": (
            f"AI 学习版式 · {spec['label']} · 版式 {variant_index + 1}"
            if variant_count > 1 else f"AI 学习版式 · {spec['label']}"
        ),
        "productName": product_name,
        "templateId": spec.get("templateId", f"learned-{style}-v1"),
        "backgroundProvider": "learned-style-renderer",
        "layoutModel": {"type": model["modelType"], "version": model["modelVersion"], "trainedSamples": model["trainedSamples"]},
        "palette": palette,
        "canvas": {"width": CANVAS[0], "height": CANVAS[1], "backgroundImage": background_url},
        "elements": elements,
    }

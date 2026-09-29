"""配置驱动的海报布局候选生成与评分。"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat


CANVAS = (1080, 1350)
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def load_font(size):
    for path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError("找不到中文字体，请在 layout_engine.py 的 load_font() 中指定字体。")


def load_templates(template_dir=TEMPLATE_DIR):
    templates = []
    for path in sorted(Path(template_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"id", "product_area", "title_area", "subtitle_area", "title_font_size"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"模板 {path.name} 缺少字段：{sorted(missing)}")
        templates.append(data)
    if not templates:
        raise FileNotFoundError(f"模板目录为空：{template_dir}")
    return templates


def normalized_to_pixels(area, canvas=CANVAS):
    width, height = canvas
    return (
        round(area[0] * width), round(area[1] * height),
        round(area[2] * width), round(area[3] * height),
    )


def fit_text(text, max_width, max_height, start_size):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start_size, 21, -2):
        current = load_font(size)
        box = draw.textbbox((0, 0), text, font=current)
        dimensions = (box[2] - box[0], box[3] - box[1])
        if dimensions[0] <= max_width and dimensions[1] <= max_height:
            return current, dimensions
    raise ValueError(f"文字太长，无法排进海报：{text}")


def center_rect(area, size):
    x = area[0] + (area[2] - area[0] - size[0]) // 2
    y = area[1] + (area[3] - area[1] - size[1]) // 2
    return (x, y, x + size[0], y + size[1])


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def extract_product_features(product):
    ratio = product.width / product.height
    shape = "vertical" if ratio < 0.85 else "horizontal" if ratio > 1.18 else "square"
    rgba = product.convert("RGBA")
    thumbnail = rgba.copy()
    thumbnail.thumbnail((128, 128))
    background = Image.new("RGBA", thumbnail.size, (255, 255, 255, 255))
    background.alpha_composite(thumbnail)
    mean = tuple(round(value) for value in ImageStat.Stat(background.convert("RGB")).mean)
    brightness = round(sum(mean) / (3 * 255), 4)
    return {
        "width": product.width,
        "height": product.height,
        "aspect_ratio": round(ratio, 4),
        "shape": shape,
        "mean_rgb": mean,
        "brightness": brightness,
    }


def make_candidate(template, product, title, subtitle, style="minimal"):
    product_area = normalized_to_pixels(template["product_area"])
    title_area = normalized_to_pixels(template["title_area"])
    subtitle_area = normalized_to_pixels(template["subtitle_area"])
    available_width = product_area[2] - product_area[0]
    available_height = product_area[3] - product_area[1]
    scale = min(available_width / product.width, available_height / product.height)
    product_size = (round(product.width * scale), round(product.height * scale))
    product_rect = center_rect(product_area, product_size)

    title_font, title_dimensions = fit_text(
        title, title_area[2] - title_area[0], title_area[3] - title_area[1], template["title_font_size"]
    )
    subtitle_start = template.get("subtitle_font_size", 42)
    subtitle_font, subtitle_dimensions = fit_text(
        subtitle, subtitle_area[2] - subtitle_area[0], subtitle_area[3] - subtitle_area[1], subtitle_start
    )
    title_rect = center_rect(title_area, title_dimensions)
    subtitle_rect = center_rect(subtitle_area, subtitle_dimensions)
    collision = overlap(product_rect, title_rect) + overlap(product_rect, subtitle_rect)

    features = extract_product_features(product)
    target_area = template.get("target_product_area_ratio", 0.22) * CANVAS[0] * CANVAS[1]
    actual_area = product_size[0] * product_size[1]
    area_score = max(0, 1 - abs(actual_area - target_area) / target_area)
    actual_center = (product_rect[0] + product_rect[2]) / (2 * CANVAS[0])
    expected_center = template.get("expected_product_center_x", 0.5)
    balance_score = max(0, 1 - abs(actual_center - expected_center) * 2)
    shape_score = 1 if features["shape"] in template.get("preferred_shapes", []) else 0.35
    style_score = 1 if style in template.get("style", []) else 0.5
    font_score = title_font.size / template["title_font_size"]
    score_parts = {
        "product_area": round(35 * area_score, 2),
        "visual_balance": round(20 * balance_score, 2),
        "title_fit": round(15 * font_score, 2),
        "shape_match": round(10 * shape_score, 2),
        "style_match": round(10 * style_score, 2),
        "no_collision": 10 if collision == 0 else -100,
    }
    score = round(sum(score_parts.values()), 2)
    return {
        "name": template["id"], "template_name": template.get("name", template["id"]),
        "score": score, "score_parts": score_parts, "product_rect": product_rect,
        "title_rect": title_rect, "subtitle_rect": subtitle_rect,
        "title_font": title_font, "subtitle_font": subtitle_font,
    }

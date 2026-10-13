"""未配置视觉模型时的本地兜底：只按图片颜色给安全占位文案，不假装识别商品。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat

from ..schema import MAX_SELLING_POINTS, CopyRequest, build_copy_set, normalize_identification

PLACEHOLDER_TITLES = [
    ("质感新选", "简约设计，为日常增添一份美好"),
    ("恰好心动", "清新配色，遇见属于你的生活灵感"),
    ("今日上新", "用精致设计，点亮每一个平常时刻"),
]


def mean_rgb(path: Path) -> tuple[int, int, int]:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
        canvas.alpha_composite(image)
        flat = canvas.convert("RGB")
        flat.thumbnail((128, 128))
        mean = ImageStat.Stat(flat).mean
    return (round(mean[0]), round(mean[1]), round(mean[2]))


def describe_color(path: Path) -> str:
    mean = mean_rgb(path)
    maximum, minimum = max(mean), min(mean)
    if maximum - minimum < 22:
        return "柔和中性色"
    if mean[0] > mean[1] * 1.08 and mean[0] > mean[2] * 1.05:
        return "暖色"
    if mean[2] > mean[0] * 1.08:
        return "清爽蓝色"
    return "自然色"


def generate(request: CopyRequest) -> dict[str, Any]:
    color = describe_color(request.images[0]) if request.images else "待确认"
    points = [str(point).strip() for point in request.selling_points if str(point).strip()]
    points = points[:MAX_SELLING_POINTS]
    name, feature = request.name.strip(), request.feature.strip()
    price, promo = request.price.strip(), request.promo.strip()

    # 没有模型时优先用用户自己填的内容：至少保证"先输入再拆块"的流程可用。
    if name or feature:
        variants = [{
            "title": name,
            "subtitle": feature,
            "selling_points": points,
            "price_text": price,
            "promo_text": promo,
        }]
        warning = "尚未配置视觉模型，当前直接使用你填写的内容，未做润色。"
    else:
        variants = [
            {
                "title": title,
                "subtitle": subtitle,
                "selling_points": points,
                "price_text": price,
                "promo_text": promo,
            }
            for title, subtitle in PLACEHOLDER_TITLES
        ]
        warning = "尚未配置视觉模型，当前仅按图片颜色生成通用文案，请人工填写准确商品信息。"

    identification = normalize_identification({
        "category": name or "待人工确认的商品",
        "color": color,
        "visible_features": points,
        "scene": ["日常", "分享"],
        "confidence": 0,
        "warning": warning,
    })
    return build_copy_set(identification, variants, source="local_fallback", meta={"provider": "local"})

"""背景生成器：本地方案始终可用，PosterCraft服务为可选增强。"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
TEMPLATE_BACKGROUND_DIR = ROOT / "backgrounds"


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float):
    return tuple(round(a[i] * (1 - amount) + b[i] * amount) for i in range(3))


def make_local_background(
    target: Path,
    size: tuple[int, int],
    color: tuple[int, int, int],
    variant: int,
) -> Path:
    """无需GPU的稳定回退背景，使用商品主色生成不同构图。"""
    width, height = size
    top = _mix(color, (255, 255, 255), 0.78)
    bottom = _mix(color, (255, 255, 255), 0.48)
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        row = _mix(top, bottom, t)
        for x in range(width):
            pixels[x, y] = row

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    accent = (*_mix(color, (255, 255, 255), 0.30), 72)
    if variant == 0:
        draw.ellipse((width * .56, height * .18, width * 1.10, height * .72), fill=accent)
        draw.ellipse((-width * .18, height * .70, width * .42, height * 1.12), fill=(*color, 30))
    elif variant == 1:
        draw.rounded_rectangle((width * .55, height * .10, width * 1.05, height * .91), 120, fill=accent)
        draw.ellipse((-200, -160, 410, 450), fill=(*color, 24))
    else:
        draw.rounded_rectangle((-width * .08, height * .12, width * .47, height * .92), 120, fill=accent)
        draw.ellipse((width * .68, -120, width * 1.12, height * .34), fill=(*color, 25))
    overlay = overlay.filter(ImageFilter.GaussianBlur(18))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, quality=95)
    return target


def make_postercraft_background(target: Path, prompt: str, timeout: int = 300) -> Path | None:
    """调用可选PosterCraft HTTP服务；失败时由调用方回退本地背景。"""
    endpoint = os.getenv("POSTERCRAFT_URL", "").strip()
    if not endpoint:
        return None
    import requests

    response = requests.post(endpoint, json={"prompt": prompt}, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("image/"):
        data = response.content
    else:
        payload = response.json()
        encoded = payload.get("image_base64")
        if not encoded:
            return None
        data = base64.b64decode(encoded.split(",")[-1])
    with Image.open(io.BytesIO(data)) as opened:
        opened.convert("RGB").save(target, quality=95)
    return target


def make_template_background(target: Path, size: tuple[int, int], variant: int) -> Path | None:
    """从授权的背景图库选择图片；可放入从设计系统导出的纯背景图片。"""
    files = []
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        files.extend(TEMPLATE_BACKGROUND_DIR.glob(pattern))
    files.sort()
    if not files:
        return None
    source = files[variant % len(files)]
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        source_ratio = image.width / image.height
        target_ratio = size[0] / size[1]
        if source_ratio > target_ratio:
            new_width = round(image.height * target_ratio)
            left = (image.width - new_width) // 2
            image = image.crop((left, 0, left + new_width, image.height))
        else:
            new_height = round(image.width / target_ratio)
            top = (image.height - new_height) // 2
            image = image.crop((0, top, image.width, top + new_height))
        image.resize(size, Image.Resampling.LANCZOS).save(target, quality=95)
    return target


def build_background(target: Path, size, color, variant, prompt, provider="auto"):
    if provider == "template":
        generated = make_template_background(target, size, variant)
        if generated:
            return generated, "template"
        return make_local_background(target, size, color, variant), "local_fallback"
    if provider in {"auto", "postercraft"}:
        try:
            generated = make_postercraft_background(target, prompt)
            if generated:
                return generated, "postercraft"
        except Exception as error:
            if provider == "postercraft":
                raise RuntimeError(f"PosterCraft服务调用失败：{error}") from error
    return make_local_background(target, size, color, variant), "local"

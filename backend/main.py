"""商品照片 → 自动抠图 → 模板库评分选优 → PNG 海报。"""

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from layout_engine import CANVAS, extract_product_features, fit_text, load_templates, make_candidate

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def cutout(source, target):
    """透明图直接使用；普通照片使用 rembg 去背景。"""
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    if image.getchannel("A").getextrema()[0] >= 250:
        try:
            from rembg import new_session, remove
        except ImportError as error:
            raise RuntimeError("普通照片需要安装自动抠图依赖：py -m pip install \"rembg[cpu]\"") from error
        print("正在自动抠图；首次运行需要下载模型……")
        image = remove(image, session=new_session("u2net")).convert("RGBA")
    bounds = image.getchannel("A").getbbox()
    if not bounds:
        raise RuntimeError("未识别到商品主体，请换一张主体清晰的图片。")
    image = image.crop(bounds)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return image


def render(product, layout, title, subtitle, footer):
    poster = Image.new("RGBA", CANVAS, "#faf6f3")
    left, top, right, bottom = layout["product_rect"]
    product = product.resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    shadow = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    silhouette = Image.new("RGBA", product.size, (74, 46, 57, 0))
    silhouette.putalpha(product.getchannel("A").point(lambda value: round(value * 0.20)))
    shadow.alpha_composite(silhouette, (left + 24, top + 30))
    poster = Image.alpha_composite(poster, shadow.filter(ImageFilter.GaussianBlur(25)))
    poster.alpha_composite(product, (left, top))
    draw = ImageDraw.Draw(poster)
    draw.text(layout["title_rect"][:2], title, font=layout["title_font"], fill="#3d3037")
    draw.text(layout["subtitle_rect"][:2], subtitle, font=layout["subtitle_font"], fill="#7b6671")
    draw.line((140, 1190, 940, 1190), fill="#d8c7cf", width=2)
    footer_font, footer_size = fit_text(footer, 800, 50, 32)
    draw.text(((CANVAS[0] - footer_size[0]) // 2, 1225), footer, font=footer_font, fill="#7b6671")
    return poster.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description="从商品图自动抠图并生成海报")
    parser.add_argument("--input", type=Path, default=ROOT / "assets" / "product.png")
    parser.add_argument("--title", default="一抹柔粉")
    parser.add_argument("--subtitle", default="把喜欢的颜色，带进每一天")
    parser.add_argument("--footer", default="粉色随行杯 · 产品展示")
    parser.add_argument("--style", default="minimal", help="风格标签：minimal、fresh、business 等")
    parser.add_argument("--desktop", action="store_true", help="同时保存到桌面海报生成图文件夹")
    args = parser.parse_args()
    source = args.input.resolve()
    if not source.is_file():
        parser.error(f"找不到商品图：{source}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    product = cutout(source, OUTPUT_DIR / f"{source.stem}_cutout.png")
    product_features = extract_product_features(product)
    templates = load_templates()
    candidates = [make_candidate(template, product, args.title, args.subtitle, args.style) for template in templates]
    best = max(candidates, key=lambda item: item["score"])
    poster = render(product, best, args.title, args.subtitle, args.footer)
    poster_path = OUTPUT_DIR / f"poster_{source.stem}.png"
    report_path = OUTPUT_DIR / f"poster_{source.stem}_layout.json"
    poster.save(poster_path)
    report = {
        "source": str(source), "style": args.style, "product_features": product_features,
        "selected_template": best["name"], "selected_template_name": best["template_name"],
        "candidates": [
            {"name": item["name"], "score": item["score"], "score_parts": item["score_parts"]}
            for item in candidates
        ],
        "final_layout": {
            "product_rect": best["product_rect"], "title_rect": best["title_rect"],
            "subtitle_rect": best["subtitle_rect"],
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"读取模板：{len(templates)} 个")
    print(f"商品特征：{product_features}")
    print(f"选择模板：{best['template_name']}（{best['name']}），得分：{best['score']}")
    print(f"海报：{poster_path}")
    print(f"布局报告：{report_path}")
    if args.desktop:
        destination_dir = Path.home() / "Desktop" / "海报生成图"
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / poster_path.name
        shutil.copy2(poster_path, destination)
        print(f"桌面副本：{destination}")


if __name__ == "__main__":
    main()

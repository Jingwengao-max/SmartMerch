"""Train a compact layout prior from annotated reference posters.

This is intentionally a statistical few-shot model rather than a diffusion
fine-tune: four posters are enough to learn stable regions and color roles,
but not enough to train a generative network without severe overfitting.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "training" / "layout_annotations_style1.json"
DEFAULT_OUTPUT = ROOT / "models" / "bakery_editorial_layout.json"


def _canvas_size(ratio_value) -> tuple[int, int]:
    """支持 0.75 或 "3:4" 两种写法。"""
    if isinstance(ratio_value, str) and ":" in ratio_value:
        width_part, height_part = ratio_value.split(":", 1)
        ratio = float(width_part) / float(height_part)
    else:
        ratio = float(ratio_value or 0.75)
    if ratio <= 0:
        ratio = 0.75
    width = 1080
    return width, round(width / ratio)


def train_payload(payload: dict, style_name: str = "bakery-editorial",
                  paper: str = "#faf5ed") -> dict:
    examples = payload.get("examples", [])
    if len(examples) < 1:
        raise ValueError("至少需要 1 张带标注的参考海报。")

    region_names = set(examples[0]["regions"])
    if any(set(item["regions"]) != region_names for item in examples):
        raise ValueError("所有样本必须标注相同的版式区域。")

    regions = {
        name: [round(median(item["regions"][name][i] for item in examples), 4) for i in range(4)]
        for name in sorted(region_names)
    }
    palettes = [item["palette"] for item in examples]
    style = payload.get("style") or {}
    paper = str(style.get("paper") or paper)
    canvas_width, canvas_height = _canvas_size(payload.get("canvasRatio", 0.75))
    return {
        "modelType": "few-shot-layout-prior",
        "modelVersion": 1,
        "trainedSamples": len(examples),
        "canvas": [canvas_width, canvas_height],
        "regions": regions,
        "paletteExamples": palettes,
        "style": {
            "name": style_name,
            "paper": paper,
            "outerPadding": int(style.get("outerPadding", 54)),
            "organicBackdrop": bool(style.get("organicBackdrop", True)),
            "footerScallop": bool(style.get("footerScallop", True)),
            "oversizedHeadline": bool(style.get("oversizedHeadline", True)),
            "badgeShape": style.get("badgeShape", "star"),
            "productDoodle": bool(style.get("productDoodle", True)),
            "productShadow": bool(style.get("productShadow", False)),
        }
    }


def train(source: Path, style_name: str = "bakery-editorial", paper: str = "#faf5ed") -> dict:
    return train_payload(json.loads(source.read_text(encoding="utf-8")), style_name, paper)


def main() -> None:
    parser = argparse.ArgumentParser(description="从标注参考图训练版式先验")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--style-name", default="bakery-editorial")
    parser.add_argument("--paper", default="#faf5ed")
    parser.add_argument("--split", action="store_true",
                        help="每张参考图各训练一个版式模型（适合多套排版的风格）")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if args.split:
        for index, example in enumerate(payload.get("examples", []), start=1):
            model = train_payload({**payload, "examples": [example]}, args.style_name, args.paper)
            output = args.output.with_name(f"{args.output.stem}_{index}{args.output.suffix}")
            output.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"variant={index} image={example['image']} model={output}")
        return
    model = train_payload(payload, args.style_name, args.paper)
    args.output.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"trained_samples={model['trainedSamples']}")
    print(f"model={args.output}")


if __name__ == "__main__":
    main()

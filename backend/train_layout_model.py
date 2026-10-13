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
DEFAULT_INPUT = ROOT / "training" / "layout_annotations.json"
DEFAULT_OUTPUT = ROOT / "models" / "bakery_editorial_layout.json"


def train(source: Path) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    examples = payload.get("examples", [])
    if len(examples) < 2:
        raise ValueError("至少需要 2 张带标注的参考海报。")

    region_names = set(examples[0]["regions"])
    if any(set(item["regions"]) != region_names for item in examples):
        raise ValueError("所有样本必须标注相同的版式区域。")

    regions = {
        name: [round(median(item["regions"][name][i] for item in examples), 4) for i in range(4)]
        for name in sorted(region_names)
    }
    palettes = [item["palette"] for item in examples]
    return {
        "modelType": "few-shot-layout-prior",
        "modelVersion": 1,
        "trainedSamples": len(examples),
        "canvas": [1080, 1440],
        "regions": regions,
        "paletteExamples": palettes,
        "style": {
            "name": "bakery-editorial",
            "paper": "#faf5ed",
            "outerPadding": 54,
            "organicBackdrop": True,
            "footerScallop": True,
            "oversizedHeadline": True
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从标注参考图训练版式先验")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    model = train(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"trained_samples={model['trainedSamples']}")
    print(f"model={args.output}")


if __name__ == "__main__":
    main()

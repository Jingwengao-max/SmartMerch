"""把人工选择记录为后续模板选择模型的训练样本。"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "data" / "template_feedback.csv"


def main():
    parser = argparse.ArgumentParser(description="记录人工选择的最佳海报模板")
    parser.add_argument("--report", type=Path, required=True, help="main.py 生成的 layout.json")
    parser.add_argument("--chosen", required=True, help="人工认为最佳的模板 id")
    parser.add_argument("--rating", type=int, choices=range(1, 6), default=5, help="1～5 分")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    valid = {candidate["name"] for candidate in report["candidates"]}
    if args.chosen not in valid:
        parser.error(f"模板不存在：{args.chosen}；可选值：{sorted(valid)}")

    features = report["product_features"]
    row = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": report["source"],
        "aspect_ratio": features["aspect_ratio"],
        "shape": features["shape"],
        "brightness": features["brightness"],
        "mean_r": features["mean_rgb"][0],
        "mean_g": features["mean_rgb"][1],
        "mean_b": features["mean_rgb"][2],
        "style": report["style"],
        "chosen_template": args.chosen,
        "rating": args.rating,
    }
    DATASET.parent.mkdir(parents=True, exist_ok=True)
    exists = DATASET.exists()
    with DATASET.open("a", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=row.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    print(f"训练样本已记录：{DATASET}")


if __name__ == "__main__":
    main()

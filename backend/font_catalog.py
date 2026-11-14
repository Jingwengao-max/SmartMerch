"""Portable, open-source font catalog shared by generation and rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FONTSOURCE_ROOT = ROOT.parent / "node_modules" / "@fontsource"
DEFAULT_FONT = "wenkai"


def _fontsource(package: str, filename: str) -> Path:
    return FONTSOURCE_ROOT / package / "files" / filename


FONT_CATALOG: dict[str, dict[str, Any]] = {
    "wenkai": {
        "label": "霞鹜文楷",
        "description": "亲和、人文，适合食品与生活方式品牌",
        "category": "handwriting",
        "css_family": "LXGW WenKai",
        "package": "@fontsource/lxgw-wenkai",
        "weights": {
            300: _fontsource("lxgw-wenkai", "lxgw-wenkai-latin-300-normal.woff"),
            500: _fontsource("lxgw-wenkai", "lxgw-wenkai-latin-500-normal.woff"),
            700: _fontsource("lxgw-wenkai", "lxgw-wenkai-latin-700-normal.woff"),
        },
    },
    "sans": {
        "label": "思源黑体",
        "description": "清晰、现代，适合信息型海报与正文",
        "category": "sans",
        "css_family": "Noto Sans SC",
        "package": "@fontsource/noto-sans-sc",
        "weights": {
            weight: _fontsource(
                "noto-sans-sc",
                f"noto-sans-sc-chinese-simplified-{weight}-normal.woff",
            )
            for weight in (400, 500, 700, 900)
        },
    },
    "serif": {
        "label": "思源宋体",
        "description": "克制、正式，适合杂志感和精品商品",
        "category": "serif",
        "css_family": "Noto Serif SC",
        "package": "@fontsource/noto-serif-sc",
        "weights": {
            weight: _fontsource(
                "noto-serif-sc",
                f"noto-serif-sc-chinese-simplified-{weight}-normal.woff",
            )
            for weight in (400, 500, 700, 900)
        },
    },
    "xiaowei": {
        "label": "站酷小薇",
        "description": "纤细、有编辑感的标题字体",
        "category": "editorial",
        "css_family": "ZCOOL XiaoWei",
        "package": "@fontsource/zcool-xiaowei",
        "weights": {
            400: _fontsource(
                "zcool-xiaowei",
                "zcool-xiaowei-chinese-simplified-400-normal.woff",
            ),
        },
    },
    "kuaile": {
        "label": "站酷快乐体",
        "description": "轻松、活泼，适合零食、活动与节日海报",
        "category": "display",
        "css_family": "ZCOOL KuaiLe",
        "package": "@fontsource/zcool-kuaile",
        "weights": {
            400: _fontsource(
                "zcool-kuaile",
                "zcool-kuaile-chinese-simplified-400-normal.woff",
            ),
        },
    },
    "qingke": {
        "label": "站酷庆科黄油体",
        "description": "厚重、复古，适合大标题和促销信息",
        "category": "display",
        "css_family": "ZCOOL QingKe HuangYou",
        "package": "@fontsource/zcool-qingke-huangyou",
        "weights": {
            400: _fontsource(
                "zcool-qingke-huangyou",
                "zcool-qingke-huangyou-chinese-simplified-400-normal.woff",
            ),
        },
    },
    "brush": {
        "label": "马善政毛笔楷书",
        "description": "毛笔书写感，适合东方、传统与节庆主题",
        "category": "calligraphy",
        "css_family": "Ma Shan Zheng",
        "package": "@fontsource/ma-shan-zheng",
        "weights": {
            400: _fontsource(
                "ma-shan-zheng",
                "ma-shan-zheng-chinese-simplified-400-normal.woff",
            ),
        },
    },
    "hand": {
        "label": "龙藏体",
        "description": "随性手写感，适合个性化短标题",
        "category": "handwriting",
        "css_family": "Long Cang",
        "package": "@fontsource/long-cang",
        "weights": {
            400: _fontsource(
                "long-cang",
                "long-cang-chinese-simplified-400-normal.woff",
            ),
        },
    },
}


FONT_ALIASES = {
    "hei": "sans",
    "bold": "sans",
    "simhei": "sans",
    "microsoft yahei": "sans",
    "noto sans sc": "sans",
    "noto serif sc": "serif",
    "lxgw wenkai": "wenkai",
    "zcool xiaowei": "xiaowei",
    "zcool kuaile": "kuaile",
    "zcool qingke huangyou": "qingke",
    "ma shan zheng": "brush",
    "long cang": "hand",
}


def resolve_font_id(family: str | None) -> str:
    """Accept catalog IDs, CSS family names, and legacy renderer aliases."""
    candidate = (family or DEFAULT_FONT).strip()
    if candidate in FONT_CATALOG:
        return candidate
    return FONT_ALIASES.get(candidate.lower(), DEFAULT_FONT)


def resolve_font_path(family: str | None, weight: int = 400) -> Path:
    font_id = resolve_font_id(family)
    weights = FONT_CATALOG[font_id]["weights"]
    nearest = min(weights, key=lambda item: abs(int(item) - int(weight)))
    path = Path(weights[nearest])
    if not path.is_file():
        raise FileNotFoundError(
            f"缺少字体文件 {path}。请先在项目根目录运行 npm install。"
        )
    return path


def public_font_catalog() -> list[dict[str, Any]]:
    """Return JSON-safe metadata without exposing local filesystem paths."""
    return [
        {
            "id": font_id,
            "label": item["label"],
            "description": item["description"],
            "category": item["category"],
            "cssFamily": item["css_family"],
            "package": item["package"],
            "weights": sorted(int(weight) for weight in item["weights"]),
            "license": "OFL-1.1",
        }
        for font_id, item in FONT_CATALOG.items()
    ]

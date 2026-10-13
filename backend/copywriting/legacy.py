"""兼容旧接口：把新契约降级映射成 /api/analyze-copy 原有的返回结构。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import generate_copy
from .providers import local_fallback
from .schema import CopyRequest


def to_legacy(copy_set: dict[str, Any]) -> dict[str, Any]:
    identification = copy_set["identification"]
    return {
        "category": identification["category"],
        "color": identification["color"],
        "visible_features": identification["visible_features"],
        "scene": identification["scene"],
        "confidence": identification["confidence"],
        "warning": identification["warning"],
        "copywriting": [
            {"title": variant["title"], "subtitle": variant["subtitle"]}
            for variant in copy_set["variants"]
            if variant["title"] or variant["subtitle"]
        ],
        "source": copy_set["source"],
    }


def analyze_with_ai(path: Path) -> dict[str, Any]:
    request = CopyRequest(images=[Path(path)])
    return to_legacy(generate_copy(request, require_ai=True))


def local_suggestions(path: Path) -> dict[str, Any]:
    request = CopyRequest(images=[Path(path)])
    return to_legacy(local_fallback.generate(request))

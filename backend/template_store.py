"""Persist compiled templates and list reusable template summaries."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe_id(template_id: str) -> str:
    value = template_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError("templateId 只能包含字母、数字、下划线和短横线。")
    return value


def save_template(template: dict[str, Any], base_dir: Path,
                  template_id: str | None = None) -> dict[str, Any]:
    canvas = template.get("canvas") or {}
    if not canvas.get("width") or not canvas.get("height"):
        raise ValueError("模板缺少画布宽高。")
    resolved_id = _safe_id(str(template_id or template.get("templateId") or ""))
    target_dir = base_dir / resolved_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "template.json"
    now = datetime.now(timezone.utc).isoformat()
    stored = json.loads(json.dumps(template))
    stored["templateId"] = resolved_id
    stored["updatedAt"] = now
    stored.setdefault("createdAt", now)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(target)
    return stored


def load_template(template_id: str, base_dir: Path) -> dict[str, Any]:
    safe_id = _safe_id(template_id)
    target = base_dir / safe_id / "template.json"
    if not target.is_file():
        raise FileNotFoundError(f"模板不存在：{safe_id}")
    return json.loads(target.read_text(encoding="utf-8"))


def list_templates(base_dir: Path) -> list[dict[str, Any]]:
    if not base_dir.is_dir():
        return []
    summaries = []
    for target in base_dir.glob("*/template.json"):
        try:
            template = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        background = template.get("background") or {}
        summaries.append({
            "templateId": template.get("templateId", target.parent.name),
            "name": template.get("name", "未命名模板"),
            "canvas": template.get("canvas", {}),
            "fieldCount": len(template.get("fields", [])),
            "layerCount": len(template.get("layers", [])),
            "previewUrl": background.get("sourceUrl"),
            "createdAt": template.get("createdAt"),
            "updatedAt": template.get("updatedAt"),
            "generationPrompt": template.get("generationPrompt", ""),
        })
    summaries.sort(key=lambda item: item.get("updatedAt") or "", reverse=True)
    return summaries

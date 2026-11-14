"""可配置的视觉AI商品识别与文案生成，兼容常见OpenAI格式接口。"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat

from style_specs import get_style_spec

def _field_lines(style: str) -> str:
    spec = get_style_spec(style)
    lines = []
    for field in spec["fields"]:
        if not field.get("generated", True):
            continue
        hint = field.get("hint") or f'{field.get("maxChars", 30)} 字以内'
        if field["kind"] == "list":
            lines.append(
                f'- {field["key"]}（{field["label"]}）：1 到 {field.get("maxItems", 3)} 条，每条{hint}'
            )
        else:
            lines.append(f'- {field["key"]}（{field["label"]}）：{hint}')
    return "\n".join(lines)


def _json_shape(style: str) -> str:
    spec = get_style_spec(style)
    parts = []
    for field in spec["fields"]:
        if not field.get("generated", True):
            continue
        if field["kind"] == "list":
            parts.append(f'"{field["key"]}":["条目一","条目二"]')
        else:
            parts.append(f'"{field["key"]}":"..."')
    return "{" + ",".join(parts) + "}"


def _system_prompt(style: str) -> str:
    shape = _json_shape(style)
    return f"""你是一名谨慎的电商视觉文案助手。先识别图片中的主要商品，再根据商品类别、可见颜色、
造型和合理使用场景，生成3组与该商品直接相关的海报文案。卖点和口号必须让人能联想到识别出的商品，
避免“质感新选”“今日上新”等与任何商品都适用的空泛文案。只描述图片中能够确认的信息；不得虚构
品牌、价格、容量、材质、保温时长、医疗效果或其他无法从图片确认的参数。
如果用户已经提供了某些字段，必须优先沿用或轻微规范，不要改写成无关内容。

本风格需要的字段：
{_field_lines(style)}

必须仅返回JSON，不要Markdown。格式：
{{"category":"具体商品类别","color":"主要颜色","visible_features":["可见特征1"],"scene":["场景1"],
"confidence":0.0,"warning":"需要人工确认的内容","copywriting":[{shape},{shape},{shape}]}}"""


def _refine_prompt(style: str) -> str:
    shape = _json_shape(style)
    return f"""你是一名谨慎的商品海报文案编辑。根据商品图片、当前文案和用户修改意见，只修改意见涉及的字段，
其余字段必须原样保留。不得虚构品牌、价格、材质、容量、功效或参数。

本风格字段：
{_field_lines(style)}

仅返回JSON，不要Markdown。格式：
{{"copywriting":[{shape}],"warning":"需要人工确认的内容"}}"""

TRANSLATE_PROMPT = """你是商品名称翻译助手。将用户输入的中文商品名翻译为自然、简洁、适合商品海报标题的英文。
不要增加原文没有的品牌、口味、材质、功效或规格。只返回JSON，不要Markdown。格式：
{"translation":"英文商品名"}"""


def configured() -> bool:
    return bool(os.getenv("AI_API_URL", "").strip() and os.getenv("AI_API_KEY", "").strip())


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI没有返回有效JSON。")
    return json.loads(text[start:end + 1])


ALIASES = {
    "subtitle": ["subtitle", "chinese_name"],
    "sellingPoints": ["sellingPoints", "selling_points"],
    "launchText": ["launchText", "launch_text"],
    "badgeText": ["badgeText", "badge_text"],
}


def _validate(payload: dict[str, Any], style: str = "editorial") -> dict[str, Any]:
    spec = get_style_spec(style)
    options = payload.get("copywriting", payload.get("variants"))
    if not isinstance(options, list) or not options:
        raise ValueError("AI结果缺少copywriting数组。")
    cleaned = []
    for item in options[:3]:
        if not isinstance(item, dict):
            continue
        option: dict[str, Any] = {}
        for field in spec["fields"]:
            if not field.get("generated", True):
                continue
            key = field["key"]
            value = next(
                (item.get(alias) for alias in ALIASES.get(key, [key]) if item.get(alias) is not None),
                None,
            )
            if field["kind"] == "list":
                if isinstance(value, str):
                    value = re.split(r"[，,、;；\n]+", value)
                if not isinstance(value, list):
                    value = []
                option[key] = [
                    str(entry).strip()[: field.get("maxChars", 30)]
                    for entry in value[: field.get("maxItems", 3)]
                    if str(entry).strip()
                ]
            else:
                text_value = str(value or "").strip()[: field.get("maxChars", 30)]
                if field.get("stripPunctuation"):
                    text_value = re.sub(r"[，,、；;。.!！?？]", "", text_value).strip()
                option[key] = text_value
        if any(option.values()):
            cleaned.append(option)
    if not cleaned:
        raise ValueError("AI没有生成可用文案。")
    payload["copywriting"] = cleaned
    payload["category"] = str(payload.get("category", "待确认商品"))[:30]
    payload["color"] = str(payload.get("color", "待确认"))[:20]
    payload["scene"] = [str(item)[:20] for item in payload.get("scene", [])[:4]]
    payload["visible_features"] = [str(item)[:30] for item in payload.get("visible_features", [])[:5]]
    payload["warning"] = str(payload.get("warning", "请人工核对商品信息。"))[:120]
    payload["source"] = "ai"
    return payload


def _call_ai(path: Path, system_prompt: str, user_text: str, style: str = "editorial") -> dict[str, Any]:
    import requests

    endpoint = os.environ["AI_API_URL"].strip().rstrip("/")
    # 允许用户填写 OpenAI 兼容服务的根地址，例如 https://host/v1。
    if endpoint.endswith("/v1"):
        endpoint += "/chat/completions"
    api_key = os.environ["AI_API_KEY"].strip()
    model = os.getenv("AI_MODEL", "qwen3-vl-plus").strip()
    payload = {
        "model": model,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": _data_url(path)}},
            ]},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if response.status_code == 400:
        # 少数OpenAI兼容视觉接口不实现response_format，提示词仍要求只返回JSON。
        payload.pop("response_format", None)
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if not response.ok:
        detail = response.text.strip()[:800]
        raise RuntimeError(
            f"视觉模型接口返回 HTTP {response.status_code}：{detail or response.reason}"
        )
    data = response.json()
    text = data["choices"][0]["message"]["content"]
    if isinstance(text, list):
        text = "".join(str(item.get("text", "")) for item in text if isinstance(item, dict))
    return _validate(_extract_json(text), style)


def translate_with_ai(chinese_name: str) -> str:
    """使用统一 AI 模型翻译商品名，不发送商品图片。"""
    import requests

    source = chinese_name.strip()
    if not source:
        raise ValueError("请输入中文商品名。")
    endpoint = os.environ["AI_API_URL"].strip().rstrip("/")
    if endpoint.endswith("/v1"):
        endpoint += "/chat/completions"
    model = os.getenv("AI_MODEL", "qwen3-vl-plus").strip()
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": TRANSLATE_PROMPT},
            {"role": "user", "content": source},
        ],
    }
    headers = {
        "Authorization": f"Bearer {os.environ['AI_API_KEY'].strip()}",
        "Content-Type": "application/json",
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=45)
    if response.status_code == 400:
        payload.pop("response_format", None)
        response = requests.post(endpoint, headers=headers, json=payload, timeout=45)
    if not response.ok:
        raise RuntimeError(f"AI模型接口返回 HTTP {response.status_code}：{response.text.strip()[:500]}")
    content = response.json()["choices"][0]["message"]["content"]
    result = _extract_json(content)
    translation = str(result.get("translation", "")).strip()[:60]
    if not translation:
        raise ValueError("AI模型没有返回英文译名。")
    return translation


def analyze_with_ai(path: Path, known: dict[str, Any] | None = None,
                    style: str = "editorial") -> dict[str, Any]:
    """识别商品并生成适配当前风格的三组可编辑文案。"""
    facts = known or {}
    lines = [f"- {key}：{value}" for key, value in facts.items() if value]
    known_text = "\n".join(lines) if lines else "- 用户尚未填写商品资料"
    return _call_ai(
        path,
        _system_prompt(style),
        "识别商品并生成三组真实、克制的宣传文案。\n【用户已知信息】\n" + known_text,
        style,
    )


def refine_with_ai(path: Path, current: dict[str, Any], instruction: str,
                   style: str = "editorial") -> dict[str, Any]:
    """根据一句自然语言意见修改一组文案，未提及字段保持原样。"""
    user_text = (
        "【当前文案】\n" + json.dumps(current, ensure_ascii=False)
        + "\n【修改意见】\n" + instruction.strip()
    )
    return _call_ai(path, _refine_prompt(style), user_text, style)


def local_suggestions(path: Path) -> dict[str, Any]:
    """未配置AI时只根据颜色给出安全占位文案，不声称识别商品种类。"""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((128, 128))
        mean = tuple(round(value) for value in ImageStat.Stat(image).mean)
    maximum, minimum = max(mean), min(mean)
    if maximum - minimum < 22:
        color = "柔和中性色"
    elif mean[0] > mean[1] * 1.08 and mean[0] > mean[2] * 1.05:
        color = "暖色"
    elif mean[2] > mean[0] * 1.08:
        color = "清爽蓝色"
    else:
        color = "自然色"
    return {
        "category": "待人工确认的商品",
        "color": color,
        "scene": ["日常", "分享"],
        "confidence": 0,
        "warning": "尚未配置视觉AI，当前仅按图片颜色生成通用文案，请人工填写准确商品信息。",
        "copywriting": [],
        "source": "local_fallback",
    }

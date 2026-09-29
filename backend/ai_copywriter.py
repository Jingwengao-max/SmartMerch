"""可配置的视觉AI商品识别与文案生成，兼容常见OpenAI格式接口。"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat


SYSTEM_PROMPT = """你是一名谨慎的电商视觉文案助手。先识别图片中的主要商品，再根据商品类别、可见颜色、
造型和合理使用场景，生成3组与该商品直接相关的中文宣传文案。标题必须让人能联想到识别出的商品，
避免“质感新选”“今日上新”等与任何商品都适用的空泛标题。只描述图片中能够确认的信息；不得虚构
品牌、价格、容量、材质、保温时长、医疗效果或其他无法从图片确认的参数。必须仅返回JSON，不要Markdown。格式：
{"category":"具体商品类别","color":"主要颜色","visible_features":["可见特征1","可见特征2"],
"scene":["场景1","场景2"],"confidence":0.0,"warning":"需要人工确认的内容","copywriting":[
{"title":"2至10字商品宣传标题","subtitle":"8至24字、与商品相关的副标题"},
{"title":"...","subtitle":"..."},{"title":"...","subtitle":"..."}]}"""


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


def _validate(payload: dict[str, Any]) -> dict[str, Any]:
    options = payload.get("copywriting")
    if not isinstance(options, list) or not options:
        raise ValueError("AI结果缺少copywriting数组。")
    cleaned = []
    for item in options[:3]:
        if isinstance(item, dict) and item.get("title") and item.get("subtitle"):
            cleaned.append({
                "title": str(item["title"])[:20],
                "subtitle": str(item["subtitle"])[:40],
            })
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


def analyze_with_ai(path: Path) -> dict[str, Any]:
    """调用用户配置的视觉模型，不在代码中保存密钥。"""
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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "识别这张商品图并生成三组真实、克制的宣传文案。"},
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
    return _validate(_extract_json(text))


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
        "copywriting": [
            {"title": "质感新选", "subtitle": "简约设计，为日常增添一份美好"},
            {"title": "恰好心动", "subtitle": "清新配色，遇见属于你的生活灵感"},
            {"title": "今日上新", "subtitle": "用精致设计，点亮每一个平常时刻"},
        ],
        "source": "local_fallback",
    }

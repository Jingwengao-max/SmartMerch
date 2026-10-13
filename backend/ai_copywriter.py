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
造型和合理使用场景，生成3组与该商品直接相关的海报文案。标题必须让人能联想到识别出的商品，
避免“质感新选”“今日上新”等与任何商品都适用的空泛标题。只描述图片中能够确认的信息；不得虚构
品牌、价格、容量、材质、保温时长、医疗效果或其他无法从图片确认的参数。如果用户提供了中文商品名，
title 必须是它自然、简洁的英文翻译，subtitle 必须保留或轻微规范该中文名称。必须仅返回JSON，不要Markdown。格式：
{"category":"具体商品类别","color":"主要颜色","visible_features":["可见特征1","可见特征2"],
"scene":["场景1","场景2"],"confidence":0.0,"warning":"需要人工确认的内容","copywriting":[
{"title":"2至5个英文单词的商品英文名，只使用英文","subtitle":"4至12字中文商品名，只使用中文",
"sellingPoints":["10至28字卖点1","10至28字卖点2","可选卖点3"],
"footer":"8至24字底部品牌口号","launchText":"2至6字右上标签","badgeText":"2至8字符徽章文字"},
{"title":"...","subtitle":"...","sellingPoints":["..."],"footer":"...","launchText":"...","badgeText":"..."},
{"title":"...","subtitle":"...","sellingPoints":["..."],"footer":"...","launchText":"...","badgeText":"..."}]}"""

REFINE_PROMPT = """你是一名谨慎的商品海报文案编辑。根据商品图片、当前文案和用户修改意见，只修改意见涉及的字段，
其余字段必须原样保留。不得虚构品牌、价格、材质、容量、功效或参数。英文商品名只使用英文，中文商品名只使用中文，
卖点最多3条。仅返回JSON，不要Markdown。格式：
{"copywriting":[{"title":"英文商品名","subtitle":"中文商品名","sellingPoints":["卖点"],
"footer":"品牌口号","launchText":"新品上市","badgeText":"NEW!"}],"warning":"需要人工确认的内容"}"""

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


def _validate(payload: dict[str, Any]) -> dict[str, Any]:
    options = payload.get("copywriting", payload.get("variants"))
    if not isinstance(options, list) or not options:
        raise ValueError("AI结果缺少copywriting数组。")
    cleaned = []
    for item in options[:3]:
        if isinstance(item, dict):
            title = item.get("title", item.get("english_name", ""))
            subtitle = item.get("subtitle", item.get("chinese_name", ""))
            selling_points = item.get("sellingPoints", item.get("selling_points", []))
            if not isinstance(selling_points, list):
                selling_points = []
            option = {
                "title": str(title).strip()[:40],
                "subtitle": str(subtitle).strip()[:20],
                "sellingPoints": [str(point)[:60] for point in selling_points[:3] if str(point).strip()],
                "footer": str(item.get("footer", ""))[:40],
                "launchText": str(item.get("launchText", item.get("launch_text", "")))[:12],
                "badgeText": str(item.get("badgeText", item.get("badge_text", "")))[:12],
            }
            if option["title"] or option["subtitle"]:
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


def _call_ai(path: Path, system_prompt: str, user_text: str) -> dict[str, Any]:
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
    return _validate(_extract_json(text))


def translate_with_ai(chinese_name: str) -> str:
    """仅调用普通文本模型翻译商品名，不发送商品图片。"""
    import requests

    source = chinese_name.strip()
    if not source:
        raise ValueError("请输入中文商品名。")
    endpoint = os.environ["AI_API_URL"].strip().rstrip("/")
    if endpoint.endswith("/v1"):
        endpoint += "/chat/completions"
    model = os.getenv("AI_TEXT_MODEL", "qwen-plus").strip()
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
        raise RuntimeError(f"文本模型接口返回 HTTP {response.status_code}：{response.text.strip()[:500]}")
    content = response.json()["choices"][0]["message"]["content"]
    result = _extract_json(content)
    translation = str(result.get("translation", "")).strip()[:60]
    if not translation:
        raise ValueError("文本模型没有返回英文译名。")
    return translation


def analyze_with_ai(path: Path, known: dict[str, Any] | None = None) -> dict[str, Any]:
    """识别商品并生成适配当前学习版式的三组可编辑文案。"""
    facts = known or {}
    lines = [f"- {key}：{value}" for key, value in facts.items() if value]
    known_text = "\n".join(lines) if lines else "- 用户尚未填写商品资料"
    return _call_ai(
        path,
        SYSTEM_PROMPT,
        "识别商品并生成三组真实、克制的宣传文案。\n【用户已知信息】\n" + known_text,
    )


def refine_with_ai(path: Path, current: dict[str, Any], instruction: str) -> dict[str, Any]:
    """根据一句自然语言意见修改一组文案，未提及字段保持原样。"""
    user_text = (
        "【当前文案】\n" + json.dumps(current, ensure_ascii=False)
        + "\n【修改意见】\n" + instruction.strip()
    )
    return _call_ai(path, REFINE_PROMPT, user_text)


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

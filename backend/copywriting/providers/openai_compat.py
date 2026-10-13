"""OpenAI 兼容的视觉模型调用（chat/completions + base64 图片）。"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from .. import config
from ..prompts import REFINE_SYSTEM_PROMPT, SYSTEM_PROMPT, build_refine_text, build_user_text
from ..schema import CopyRequest


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("视觉模型没有返回有效JSON。")
    return json.loads(text[start:end + 1])


def image_data_url(path: Path) -> str:
    """透明抠图先合成到白底，避免部分模型把 alpha 通道渲染成黑底。"""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
        canvas.alpha_composite(image)
        flat = canvas.convert("RGB")
    edge = config.image_max_edge()
    flat.thumbnail((edge, edge))
    buffer = io.BytesIO()
    flat.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class OpenAICompatProvider:
    """任何兼容 OpenAI chat/completions 的视觉模型都能走这个 provider。"""

    name = "openai_compat"

    def build_payload(self, request: CopyRequest) -> dict[str, Any]:
        return self._payload(SYSTEM_PROMPT, build_user_text(request), request)

    def _image_parts(self, request: CopyRequest) -> list[dict[str, Any]]:
        return [
            {"type": "image_url", "image_url": {"url": image_data_url(path)}}
            for path in request.images
        ]

    def _payload(self, system_prompt: str, user_text: str, request: CopyRequest) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        content.extend(self._image_parts(request))
        return {
            "model": config.model_name(),
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        }

    def _complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        import requests

        endpoint = config.chat_endpoint()
        headers = {
            "Authorization": f"Bearer {config.api_key() or 'local'}",
            "Content-Type": "application/json",
        }
        response = requests.post(endpoint, headers=headers, json=payload, timeout=config.timeout())
        if response.status_code == 400:
            # 少数兼容接口不实现 response_format，提示词仍然要求只返回 JSON。
            payload.pop("response_format", None)
            response = requests.post(endpoint, headers=headers, json=payload, timeout=config.timeout())
        if not response.ok:
            detail = response.text.strip()[:800]
            raise RuntimeError(
                f"视觉模型接口返回 HTTP {response.status_code}：{detail or response.reason}"
            )
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        if isinstance(text, list):
            text = "".join(str(item.get("text", "")) for item in text if isinstance(item, dict))
        return extract_json(text)

    def generate(self, request: CopyRequest) -> dict[str, Any]:
        return self._complete(self.build_payload(request))

    def generate_refine(self, request: CopyRequest, current: dict[str, Any],
                        feedback: dict[str, Any]) -> dict[str, Any]:
        return self._complete(
            self._payload(REFINE_SYSTEM_PROMPT, build_refine_text(current, feedback), request)
        )

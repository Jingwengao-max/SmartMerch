"""商品图到可编辑海报的完整Web API。"""

from __future__ import annotations

import csv
import io
import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFilter

from ai_copywriter import (
    analyze_with_ai,
    configured as ai_configured,
    local_suggestions,
    refine_with_ai,
    translate_with_ai,
)
from font_catalog import public_font_catalog
from layout_engine import CANVAS, extract_product_features, load_font
from learned_layout import (
    adaptive_palette,
    build_style_background,
    create_document,
    load_model,
    load_model_for,
    load_models_for,
    retro_palette,
)
from main import cutout
from poster_design_adapter import normalize_template
from poster_design_source import (
    STATIC_DIR as POSTER_DESIGN_STATIC_DIR,
    available as poster_design_available,
    list_templates as list_poster_design_templates,
    load_template as load_poster_design_template,
)
from quality_evaluator import evaluate_document
from style_specs import STYLE_SPECS


def _load_local_env() -> None:
    """手动运行 api.py 时也读取本地 .env；不覆盖已有的环境变量。"""
    project_root = Path(__file__).resolve().parent.parent
    for candidate in (project_root / ".env", Path(__file__).resolve().parent / ".env"):
        if not candidate.is_file():
            continue
        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key:
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))


_load_local_env()

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
FRONTEND_DIR = ROOT.parent / "dist"
GENERATED_DIR = ROOT / "generated"
DATA_DIR = ROOT / "data"
GENERATED_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI商品海报工作室", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")
if WEB_DIR.is_dir():
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")
if POSTER_DESIGN_STATIC_DIR.is_dir():
    app.mount(
        "/poster-design-static",
        StaticFiles(directory=POSTER_DESIGN_STATIC_DIR),
        name="poster-design-static",
    )


def _public(path: Path) -> str:
    return f"/generated/{path.relative_to(GENERATED_DIR).as_posix()}"


def _asset_path(url: str) -> Path:
    roots = {
        "/generated/": GENERATED_DIR,
        "/poster-design-static/": POSTER_DESIGN_STATIC_DIR,
    }
    for prefix, root in roots.items():
        if not url.startswith(prefix):
            continue
        resolved = (root / Path(url[len(prefix):])).resolve()
        if root.resolve() not in resolved.parents:
            raise ValueError("非法资源路径。")
        return resolved
    raise ValueError("只允许渲染本系统或 poster-design 的本地资源。")


def _text_box(text: str, font_size: int, max_width: int) -> tuple[int, int]:
    font = load_font(font_size)
    box = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    return min(max_width, max(80, box[2] - box[0] + 12)), max(48, box[3] - box[1] + 16)


def _document(job_id: str, index: int, template: dict[str, Any], candidate: dict[str, Any],
              product_url: str, background_url: str, title: str, subtitle: str,
              price: str, provider: str) -> dict[str, Any]:
    product_rect = candidate["product_rect"]
    title_rect = candidate["title_rect"]
    subtitle_rect = candidate["subtitle_rect"]
    title_width, title_height = _text_box(title, candidate["title_font"].size, 900)
    subtitle_width, subtitle_height = _text_box(subtitle, candidate["subtitle_font"].size, 900)
    elements = [
        {
            "id": "product", "type": "image", "role": "product", "src": product_url,
            "x": product_rect[0], "y": product_rect[1],
            "width": product_rect[2] - product_rect[0], "height": product_rect[3] - product_rect[1],
            "rotation": 0, "zIndex": 2,
        },
        {
            "id": "title", "type": "text", "role": "title", "content": title,
            "x": title_rect[0], "y": title_rect[1], "width": title_width, "height": title_height,
            "fontSize": candidate["title_font"].size, "fontWeight": 700,
            "color": "#3d3037", "rotation": 0, "zIndex": 3,
        },
        {
            "id": "subtitle", "type": "text", "role": "subtitle", "content": subtitle,
            "x": subtitle_rect[0], "y": subtitle_rect[1], "width": subtitle_width, "height": subtitle_height,
            "fontSize": candidate["subtitle_font"].size, "fontWeight": 400,
            "color": "#765f6b", "rotation": 0, "zIndex": 3,
        },
    ]
    if price.strip():
        elements.append({
            "id": "price", "type": "text", "role": "price", "content": price.strip(),
            "x": 790, "y": 1190, "width": 220, "height": 82,
            "fontSize": 60, "fontWeight": 700, "color": "#b94767", "rotation": 0, "zIndex": 4,
        })
    document = {
        "id": f"{job_id}_{index}",
        "name": template.get("name", template["id"]),
        "templateId": template["id"],
        "backgroundProvider": provider,
        "canvas": {"width": CANVAS[0], "height": CANVAS[1], "backgroundImage": background_url},
        "elements": elements,
        "layoutScore": candidate["score"],
        "layoutScoreParts": candidate["score_parts"],
    }
    document["quality"] = evaluate_document(document)
    return document


def _render(document: dict[str, Any]) -> Image.Image:
    canvas = document["canvas"]
    size = (int(canvas["width"]), int(canvas["height"]))
    background_url = canvas.get("backgroundImage")
    if background_url:
        with Image.open(_asset_path(background_url)) as opened:
            poster = opened.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    else:
        poster = Image.new("RGBA", size, canvas.get("backgroundColor", "#f8f4f5"))

    for element in sorted(document.get("elements", []), key=lambda item: item.get("zIndex", 0)):
        x, y = round(float(element["x"])), round(float(element["y"]))
        width, height = max(1, round(float(element["width"]))), max(1, round(float(element["height"])))
        if element["type"] == "image":
            with Image.open(_asset_path(element["src"])) as opened:
                layer = opened.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
            if element.get("role") == "product":
                shadow = Image.new("RGBA", size, (0, 0, 0, 0))
                silhouette = Image.new("RGBA", layer.size, (40, 28, 34, 0))
                silhouette.putalpha(layer.getchannel("A").point(lambda value: round(value * 0.16)))
                shadow.alpha_composite(silhouette, (x + 18, y + 24))
                poster = Image.alpha_composite(poster, shadow.filter(ImageFilter.GaussianBlur(22)))
            rotation = float(element.get("rotation", 0))
            if rotation:
                layer = layer.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
            poster.alpha_composite(layer, (x, y))
        elif element["type"] == "shape" and element.get("shape") == "rect":
            fill = str(element.get("fill", "#ffffff"))
            rgb = tuple(int(fill[index:index + 2], 16) for index in (1, 3, 5))
            alpha = round(float(element.get("opacity", 0.5)) * 255)
            layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle(
                (0, 0, width - 1, height - 1),
                radius=int(element.get("radius", 16)),
                fill=(*rgb, alpha),
            )
            poster.alpha_composite(layer, (x, y))
        elif element["type"] == "shape" and element.get("shape") == "soft-shadow":
            fill = str(element.get("fill", "#ffffff"))
            rgb = tuple(int(fill[index:index + 2], 16) for index in (1, 3, 5))
            alpha = round(float(element.get("opacity", 0.18)) * 255)
            blur = int(element.get("blur", 20))
            # 图层要比晕影本身大，否则模糊会被边界裁成方块。
            pad = blur * 2
            layer = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))
            ImageDraw.Draw(layer).ellipse(
                (pad, pad, pad + width - 1, pad + height - 1), fill=(*rgb, alpha)
            )
            layer = layer.filter(ImageFilter.GaussianBlur(blur))
            poster.alpha_composite(layer, (x - pad, y - pad))
        elif element["type"] == "shape" and element.get("shape") == "tech-corner":
            fill = str(element.get("fill", "#7e409d"))
            rgb = tuple(int(fill[index:index + 2], 16) for index in (1, 3, 5))
            alpha = round(float(element.get("opacity", 1.0)) * 255)
            layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shape_draw = ImageDraw.Draw(layer)
            arm = max(4, round(min(width, height) * 0.34))
            line_width = max(1, round(min(width, height) * 0.1))
            color = (*rgb, alpha)
            shape_draw.line((0, 0, arm, 0), fill=color, width=line_width)
            shape_draw.line((0, 0, 0, arm), fill=color, width=line_width)
            shape_draw.line((width - 1, 0, width - 1 - arm, 0), fill=color, width=line_width)
            shape_draw.line((width - 1, 0, width - 1, arm), fill=color, width=line_width)
            shape_draw.line((0, height - 1, arm, height - 1), fill=color, width=line_width)
            shape_draw.line((0, height - 1, 0, height - 1 - arm), fill=color, width=line_width)
            shape_draw.line((width - 1, height - 1, width - 1 - arm, height - 1), fill=color, width=line_width)
            shape_draw.line((width - 1, height - 1, width - 1, height - 1 - arm), fill=color, width=line_width)
            dot = max(2, round(min(width, height) * 0.1))
            shape_draw.ellipse(
                (width / 2 - dot, height / 2 - dot, width / 2 + dot, height / 2 + dot),
                fill=color,
            )
            poster.alpha_composite(layer, (x, y))
        elif element["type"] == "text":
            layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            font = load_font(
                int(element.get("fontSize", 40)),
                int(element.get("fontWeight", 400)),
                element.get("fontFamily"),
            )
            content = str(element.get("content", ""))
            align = element.get("textAlign", "left")
            line_height = int(element.get("lineHeight") or round(font.size * 1.18))
            spacing = float(element.get("letterSpacing") or 0)
            line_spacings = element.get("lineSpacings") or []
            color = element.get("color", "#222222")
            weight = int(element.get("fontWeight", 400))
            if weight >= 600:
                # 黑体大标题按字号加粗，避免只描 1px 看不出来。
                stroke = max(1, round(font.size / 90)) if element.get("fontFamily") == "hei" else 1
            else:
                stroke = 0
            lines = content.splitlines() or [""]
            total_height = len(lines) * line_height
            vertical_align = element.get("verticalAlign", "top")
            if vertical_align == "middle":
                text_y = y + max(0, (height - total_height) // 2)
            elif vertical_align == "bottom":
                text_y = y + max(0, height - total_height)
            else:
                text_y = y
            for line_index, line in enumerate(lines):
                line_spacing = float(
                    line_spacings[line_index]
                    if line_index < len(line_spacings)
                    else spacing
                )
                box = draw.textbbox((0, 0), line, font=font)
                line_width = box[2] - box[0]
                span = line_width + line_spacing * max(0, len(line) - 1)
                if align == "center":
                    line_x = x + max(0, (width - span) // 2)
                elif align == "right":
                    line_x = x + max(0, width - span)
                else:
                    line_x = x
                line_y = text_y + line_index * line_height - y
                if line_spacing:
                    cursor = line_x - x
                    for character in line:
                        draw.text(
                            (cursor, line_y), character, font=font, fill=color,
                            stroke_width=stroke, stroke_fill=color,
                        )
                        cursor += draw.textlength(character, font=font) + line_spacing
                else:
                    draw.text(
                        (line_x - x, line_y), line, font=font, fill=color,
                        stroke_width=stroke, stroke_fill=color,
                    )
            opacity = max(0.0, min(1.0, float(element.get("opacity", 1))))
            if opacity < 0.999:
                alpha = layer.getchannel("A").point(lambda value: round(value * opacity))
                layer.putalpha(alpha)
            poster.alpha_composite(layer, (x, y))
    return poster.convert("RGB")


@app.get("/")
def index():
    index_file = WEB_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "name": "SmartMerch Poster API",
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    import os

    layout_model = load_model()

    return {
        "status": "ok",
        "copywriterAi": ai_configured(),
        "aiModel": os.getenv("AI_MODEL", "qwen3-vl-plus"),
        "posterDesign": poster_design_available(),
        "layoutModel": layout_model["modelType"],
        "layoutModelVersion": layout_model["modelVersion"],
        "layoutTrainingSamples": layout_model["trainedSamples"],
    }


@app.get("/api/styles")
def list_styles():
    """前端据此动态渲染每个风格的文案条目。"""
    return {
        "styles": [
            {
                "key": key,
                "label": spec["label"],
                "fields": [
                    {
                        "key": field["key"],
                        "label": field["label"],
                        "kind": field["kind"],
                        "maxChars": field.get("maxChars", 30),
                        "maxItems": field.get("maxItems", 1),
                        "generated": field.get("generated", True),
                    }
                    for field in spec["fields"]
                ],
            }
            for key, spec in STYLE_SPECS.items()
        ]
    }


@app.get("/api/fonts")
def list_fonts():
    """可供模板分析、文案字段和图层编辑器选择的字体。"""
    return {"fonts": public_font_catalog()}


@app.post("/api/cutout")
async def cutout_product(image: UploadFile = File(...)):
    """SmartMerch 上传步骤使用：抠图并返回可直接预览的透明 PNG。"""
    suffix = Path(image.filename or "product.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "请上传 PNG、JPG 或 WEBP 图片。")
    job_id = uuid.uuid4().hex[:12]
    job_dir = GENERATED_DIR / job_id
    job_dir.mkdir(parents=True)
    source = job_dir / f"source{suffix}"
    source.write_bytes(await image.read())
    try:
        product_path = job_dir / "product_cutout.png"
        product = cutout(source, product_path)
        return {
            "jobId": job_id,
            "imageName": image.filename or "product.png",
            "cutoutUrl": _public(product_path),
            "productFeatures": extract_product_features(product),
        }
    except Exception as error:
        raise HTTPException(500, f"自动抠图失败：{error}") from error


@app.get("/api/ai-models")
def ai_models():
    """列出当前 OpenAI 兼容网关公开的模型名称，不返回 API Key。"""
    import os
    import requests

    base = os.getenv("AI_API_URL", "").strip().rstrip("/")
    key = os.getenv("AI_API_KEY", "").strip()
    if not base or not key:
        raise HTTPException(400, "尚未配置 AI_API_URL 或 AI_API_KEY。")
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    try:
        response = requests.get(
            f"{base}/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        if not response.ok:
            raise HTTPException(response.status_code, response.text[:800])
        payload = response.json()
        models = payload.get("data", payload)
        ids = [item.get("id") for item in models if isinstance(item, dict) and item.get("id")]
        return {"models": ids}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(502, f"读取模型列表失败：{error}") from error


@app.get("/api/poster-design/templates")
def poster_design_templates():
    try:
        return {
            "source": "poster-design/service/seed/poster.db",
            "templates": list_poster_design_templates(0),
            "components": list_poster_design_templates(1),
        }
    except Exception as error:
        raise HTTPException(503, f"读取 poster-design 模板库失败：{error}") from error


@app.get("/api/poster-design/templates/{template_id}")
def poster_design_template(template_id: int):
    try:
        document = normalize_template(load_poster_design_template(template_id))
        document["source"] = "poster-design"
        return document
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except Exception as error:
        raise HTTPException(500, f"转换 poster-design 模板失败：{error}") from error


@app.post("/api/analyze-copy")
async def analyze_copy(image: UploadFile = File(...)):
    suffix = Path(image.filename or "product.jpg").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "请上传PNG、JPG或WEBP图片。")
    temporary = GENERATED_DIR / f"copy_{uuid.uuid4().hex[:12]}{suffix}"
    temporary.write_bytes(await image.read())
    try:
        if ai_configured():
            return analyze_with_ai(temporary)
        return local_suggestions(temporary)
    except Exception as error:
        raise HTTPException(502, f"AI识别失败：{error}") from error
    finally:
        temporary.unlink(missing_ok=True)


def _job_product_path(job_id: str) -> Path:
    if len(job_id) != 12 or any(character not in "0123456789abcdef" for character in job_id.lower()):
        raise HTTPException(400, "无效的任务编号。")
    path = GENERATED_DIR / job_id / "product_cutout.png"
    if not path.is_file():
        raise HTTPException(404, "找不到该任务的商品图片，请重新上传。")
    return path


@app.post("/api/copy")
async def generate_copy(
    job_id: str = Form("", alias="jobId"),
    name: str = Form(""),
    feature: str = Form(""),
    selling_points: str = Form("[]"),
    footer: str = Form(""),
    launch_text: str = Form("新品上市"),
    badge_text: str = Form("NEW!"),
    style: str = Form("editorial"),
    context: str = Form(""),
):
    """结合抠图与用户已填信息生成三组文案建议。"""
    path = _job_product_path(job_id)
    try:
        points = json.loads(selling_points)
        if not isinstance(points, list):
            points = []
    except json.JSONDecodeError:
        points = []
    if not ai_configured():
        result = local_suggestions(path)
        result["jobId"] = job_id
        return result
    known: dict[str, Any] = {}
    if context.strip():
        try:
            parsed_context = json.loads(context)
        except json.JSONDecodeError as error:
            raise HTTPException(400, "context 必须是 JSON 对象。") from error
        if not isinstance(parsed_context, dict):
            raise HTTPException(400, "context 必须是 JSON 对象。")
        known = {str(key): value for key, value in parsed_context.items() if value not in (None, "")}
    else:
        known = {
            "英文商品名": name.strip(),
            "中文商品名": feature.strip(),
            "用户卖点": "；".join(str(point).strip() for point in points[:3] if str(point).strip()),
            "品牌口号": footer.strip(),
            "右上标签": launch_text.strip(),
            "徽章文字": badge_text.strip(),
        }
    try:
        result = analyze_with_ai(path, known, style)
        result["jobId"] = job_id
        return result
    except Exception as error:
        raise HTTPException(502, f"AI文案生成失败：{error}") from error


@app.post("/api/translate")
def translate_product_name(payload: dict[str, Any]):
    """使用统一 AI 模型翻译商品名，不读取或上传商品图片。"""
    chinese_name = str(payload.get("text", "")).strip()
    if not chinese_name:
        raise HTTPException(400, "请输入中文商品名。")
    if not ai_configured():
        raise HTTPException(503, "尚未配置 AI 模型接口。")
    try:
        return {
            "source": chinese_name,
            "translation": translate_with_ai(chinese_name),
            "model": os.getenv("AI_MODEL", "qwen3-vl-plus"),
        }
    except Exception as error:
        raise HTTPException(502, f"AI翻译失败：{error}") from error


@app.post("/api/copy/refine")
def refine_copy(payload: dict[str, Any]):
    """根据用户意见仅调整一组文案，其他候选不变。

    支持两种入参：逐条填写的 `feedback`（推荐），或一句自然语言 `instruction`（兼容旧前端）。
    """
    job_id = str(payload.get("jobId", ""))
    style = str(payload.get("style", "editorial"))
    current = payload.get("current")
    instruction = (
        str(payload.get("instruction", "")).strip()
        or _feedback_instruction(payload.get("feedback"), style)
    )
    if not isinstance(current, dict) or not instruction:
        raise HTTPException(400, "需要当前文案和修改意见。")
    if not ai_configured():
        raise HTTPException(503, "尚未配置视觉模型，暂时无法按意见修改。")
    try:
        result = refine_with_ai(_job_product_path(job_id), current, instruction, style)
        result["jobId"] = job_id
        return result
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(502, f"AI文案修改失败：{error}") from error


def _feedback_instruction(feedback: Any, style: str = "editorial") -> str:
    """把逐条修改意见拼成一句明确的指令，只列出用户真正填了的条目。"""
    if not isinstance(feedback, dict):
        return ""
    spec = STYLE_SPECS.get(style) or STYLE_SPECS["editorial"]
    lines: list[str] = []
    for field in spec["fields"]:
        key = field["key"]
        if field["kind"] == "list":
            values = feedback.get(key)
            if not isinstance(values, (list, tuple)):
                continue
            for index, item in enumerate(values[: field.get("maxItems", 3)], start=1):
                value = str(item or "").strip()[:80]
                if value:
                    lines.append(f"- {field['label']} {index}：{value}")
            continue
        value = str(feedback.get(key, "") or "").strip()[:80]
        if value:
            lines.append(f"- {field['label']}：{value}")
    if not lines:
        return ""
    return "请只修改下面这些条目，其余条目必须原样保留：\n" + "\n".join(lines)


@app.post("/api/generate")
async def generate(
    image: UploadFile = File(...),
    title: str | None = Form(None),
    subtitle: str | None = Form(None),
    name: str | None = Form(None),
    feature: str = Form(""),
    selling_points: str = Form("[]"),
    left_detail: str = Form(""),
    right_detail: str = Form(""),
    footer: str = Form(""),
    launch_text: str = Form("新品上市"),
    badge_text: str = Form("NEW!"),
    price: str = Form(""),
    style: str = Form("editorial"),
    copy_json: str = Form("", alias="copy"),
):
    suffix = Path(image.filename or "product.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "请上传PNG、JPG或WEBP图片。")
    job_id = uuid.uuid4().hex[:12]
    job_dir = GENERATED_DIR / job_id
    job_dir.mkdir(parents=True)
    source = job_dir / f"source{suffix}"
    source.write_bytes(await image.read())
    try:
        resolved_title = (title or name or "新品上市").strip()
        resolved_subtitle = (subtitle or feature or "让美好融入日常").strip()
        try:
            parsed_points = json.loads(selling_points)
        except json.JSONDecodeError as error:
            raise ValueError("selling_points 必须是 JSON 数组。") from error
        if not isinstance(parsed_points, list):
            raise ValueError("selling_points 必须是 JSON 数组。")
        normalized_points = [str(point).strip()[:60] for point in parsed_points if str(point).strip()][:3]
        if not normalized_points:
            normalized_points = [point.strip() for point in (left_detail, right_detail) if point.strip()][:3]
        copy_data: dict[str, Any] = {}
        if copy_json.strip():
            try:
                parsed_copy = json.loads(copy_json)
            except json.JSONDecodeError as error:
                raise ValueError("copy 必须是 JSON 对象。") from error
            if not isinstance(parsed_copy, dict):
                raise ValueError("copy 必须是 JSON 对象。")
            copy_data = {str(key): value for key, value in parsed_copy.items()}
        else:
            copy_data = {
                "title": resolved_title,
                "subtitle": resolved_subtitle,
                "sellingPoints": normalized_points,
                "footer": footer,
                "launchText": launch_text,
                "badgeText": badge_text,
            }
        product_path = job_dir / "product_cutout.png"
        product = cutout(source, product_path)
        features = extract_product_features(product)
        mean = tuple(features["mean_rgb"])
        try:
            style_models = load_models_for(style)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        documents = []
        for index, style_model in enumerate(style_models):
            paper = str(style_model.get("style", {}).get("paper", "#faf5ed"))
            background_path = job_dir / f"learned_background_{index}.jpg"
            build_style_background(
                background_path, (retro_palette(mean) if style == "retro" else adaptive_palette(mean, paper)), product, style_model,
                style_key=style, variant_index=index,
            )
            document = create_document(
                job_id=job_id,
                product_url=_public(product_path),
                background_url=_public(background_path),
                product_size=product.size,
                mean_rgb=mean,
                copy=copy_data,
                style=style,
                model=style_model,
                variant_index=index,
                variant_count=len(style_models),
            )
            preview_path = job_dir / f"preview_learned_{index}.jpg"
            _render(document).save(preview_path, quality=94)
            document["previewUrl"] = _public(preview_path)
            documents.append(document)
        (job_dir / "documents.json").write_text(
            json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "jobId": job_id,
            "input": {
                "name": resolved_title,
                "feature": feature,
                "sellingPoints": normalized_points,
                "footer": footer,
                "launchText": launch_text,
                "badgeText": badge_text,
                "style": style,
                "price": price,
                "copy": copy_data,
            },
            "productFeatures": features,
            "candidates": documents,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(500, str(error)) from error


@app.post("/api/evaluate")
def evaluate(document: dict[str, Any]):
    return evaluate_document(document)


@app.post("/api/import-template")
def import_template(payload: dict[str, Any]):
    try:
        return normalize_template(payload)
    except Exception as error:
        raise HTTPException(400, f"模板转换失败：{error}") from error


@app.post("/api/render")
def render_endpoint(document: dict[str, Any]):
    try:
        image = _render(document)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return Response(
            buffer.getvalue(), media_type="image/png",
            headers={"Content-Disposition": 'attachment; filename="poster.png"'},
        )
    except Exception as error:
        raise HTTPException(400, f"渲染失败：{error}") from error


@app.post("/api/feedback")
def feedback(payload: dict[str, Any]):
    path = DATA_DIR / "web_feedback.csv"
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["job_id", "template_id", "rating"])
        if not exists:
            writer.writeheader()
        writer.writerow({
            "job_id": payload.get("jobId", ""),
            "template_id": payload.get("templateId", ""),
            "rating": payload.get("rating", 5),
        })
    return {"saved": True}


@app.get("/{full_path:path}", include_in_schema=False)
def frontend(full_path: str):
    """在生产预览模式下由同一个端口提供 Vue 页面。"""
    if not FRONTEND_DIR.is_dir():
        raise HTTPException(
            503,
            "前端尚未构建，请在项目根目录运行 npm run build。",
        )
    requested = (FRONTEND_DIR / full_path).resolve()
    frontend_root = FRONTEND_DIR.resolve()
    if requested != frontend_root and frontend_root not in requested.parents:
        raise HTTPException(404, "页面不存在。")
    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import os
    import socket
    import subprocess
    import threading
    import uvicorn
    import webbrowser

    def find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])

    preview_port = find_free_port()
    preview_url = f"http://127.0.0.1:{preview_port}/studio"

    def open_preview_without_proxy() -> None:
        edge_candidates = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        edge = next((path for path in edge_candidates if path.is_file()), None)
        if edge:
            subprocess.Popen([
                str(edge),
                f"--user-data-dir={ROOT / '.preview-browser-profile'}",
                "--no-first-run",
                "--no-default-browser-check",
                "--proxy-server=direct://",
                "--proxy-bypass-list=*",
                f"--app={preview_url}",
            ])
            return
        webbrowser.open(preview_url)

    print(f"SmartMerch preview: {preview_url}", flush=True)
    threading.Timer(1.5, open_preview_without_proxy).start()
    uvicorn.run(app, host="127.0.0.1", port=preview_port)

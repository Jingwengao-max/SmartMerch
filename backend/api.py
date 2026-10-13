"""商品图到可编辑海报的完整Web API。"""

from __future__ import annotations

import csv
import io
import json
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
)
from layout_engine import CANVAS, extract_product_features, load_font
from learned_layout import adaptive_palette, build_style_background, create_document, load_model
from main import cutout
from poster_design_adapter import normalize_template
from poster_design_source import (
    STATIC_DIR as POSTER_DESIGN_STATIC_DIR,
    available as poster_design_available,
    list_templates as list_poster_design_templates,
    load_template as load_poster_design_template,
)
from quality_evaluator import evaluate_document

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
        elif element["type"] == "text":
            draw = ImageDraw.Draw(poster)
            font = load_font(
                int(element.get("fontSize", 40)),
                int(element.get("fontWeight", 400)),
            )
            content = str(element.get("content", ""))
            align = element.get("textAlign", "left")
            line_height = round(font.size * 1.18)
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
                box = draw.textbbox((0, 0), line, font=font)
                line_width = box[2] - box[0]
                if align == "center":
                    line_x = x + max(0, (width - line_width) // 2)
                elif align == "right":
                    line_x = x + max(0, width - line_width)
                else:
                    line_x = x
                draw.text(
                    (line_x, text_y + line_index * line_height), line, font=font,
                    fill=element.get("color", "#222222"),
                    stroke_width=1 if int(element.get("fontWeight", 400)) >= 600 else 0,
                    stroke_fill=element.get("color", "#222222"),
                )
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
    try:
        result = analyze_with_ai(path, {
            "英文商品名": name.strip(),
            "中文商品名": feature.strip(),
            "用户卖点": "；".join(str(point).strip() for point in points[:3] if str(point).strip()),
            "品牌口号": footer.strip(),
            "右上标签": launch_text.strip(),
            "徽章文字": badge_text.strip(),
        })
        result["jobId"] = job_id
        return result
    except Exception as error:
        raise HTTPException(502, f"AI文案生成失败：{error}") from error


@app.post("/api/copy/refine")
def refine_copy(payload: dict[str, Any]):
    """根据用户意见仅调整一组文案，其他候选不变。"""
    job_id = str(payload.get("jobId", ""))
    current = payload.get("current")
    instruction = str(payload.get("instruction", "")).strip()
    if not isinstance(current, dict) or not instruction:
        raise HTTPException(400, "需要当前文案和修改意见。")
    if not ai_configured():
        raise HTTPException(503, "尚未配置视觉模型，暂时无法按意见修改。")
    try:
        result = refine_with_ai(_job_product_path(job_id), current, instruction)
        result["jobId"] = job_id
        return result
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(502, f"AI文案修改失败：{error}") from error


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
        product_path = job_dir / "product_cutout.png"
        product = cutout(source, product_path)
        features = extract_product_features(product)
        mean = tuple(features["mean_rgb"])
        background_path = job_dir / "learned_background.jpg"
        build_style_background(background_path, adaptive_palette(mean), product)
        document = create_document(
            job_id=job_id,
            product_url=_public(product_path),
            background_url=_public(background_path),
            product_size=product.size,
            mean_rgb=mean,
            title=resolved_title,
            feature=resolved_subtitle,
            price=price,
            selling_points=normalized_points,
            footer=footer,
            launch_text=launch_text,
            badge_text=badge_text,
        )
        preview_path = job_dir / "preview_learned.jpg"
        _render(document).save(preview_path, quality=94)
        document["previewUrl"] = _public(preview_path)
        documents = [document]
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
                "price": price,
            },
            "productFeatures": features,
            "candidates": documents,
        }
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
    """在生产预览模式下由同一个 8000 端口提供 Vue 页面。"""
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
    import threading
    import uvicorn
    import webbrowser

    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:8000/studio")).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)

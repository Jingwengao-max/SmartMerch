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

from ai_copywriter import analyze_with_ai, configured as ai_configured, local_suggestions
from background_provider import build_background
from layout_engine import CANVAS, extract_product_features, load_font, load_templates, make_candidate
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
            font = load_font(int(element.get("fontSize", 40)))
            draw.text((x, y), str(element.get("content", "")), font=font, fill=element.get("color", "#222222"))
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

    return {
        "status": "ok",
        "postercraft": bool(__import__("os").getenv("POSTERCRAFT_URL")),
        "copywriterAi": ai_configured(),
        "aiModel": os.getenv("AI_MODEL", "qwen3-vl-plus"),
        "posterDesign": poster_design_available(),
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


@app.post("/api/generate")
async def generate(
    image: UploadFile = File(...),
    title: str | None = Form(None),
    subtitle: str | None = Form(None),
    name: str | None = Form(None),
    feature: str = Form(""),
    vibe: str = Form(""),
    price: str = Form(""),
    style: str = Form("minimal"),
    background_provider: str = Form("auto"),
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
        product_path = job_dir / "product_cutout.png"
        product = cutout(source, product_path)
        features = extract_product_features(product)
        templates = load_templates()
        ranked = sorted(
            (
                (item, make_candidate(item, product, resolved_title, resolved_subtitle, style))
                for item in templates
            ),
            key=lambda pair: pair[1]["score"],
            reverse=True,
        )[:1]
        mean = tuple(features["mean_rgb"])
        prompt = (
            f"commercial product poster background for {resolved_title}, {style} style, "
            f"campaign mood {vibe or 'general'}, visible feature {feature or 'unspecified'}, "
            f"dominant color rgb{mean}, elegant abstract shapes, clean premium composition, "
            "generous negative space, no product, no bottle, no text, no letters, no logo"
        )
        documents = []
        for index, (template, candidate) in enumerate(ranked):
            background_path = job_dir / f"background_{index}.jpg"
            _, provider = build_background(
                background_path, CANVAS, mean, index, prompt, background_provider
            )
            document = _document(
                job_id, index, template, candidate, _public(product_path),
                _public(background_path), resolved_title, resolved_subtitle, price, provider,
            )
            preview_path = job_dir / f"preview_{index}.jpg"
            _render(document).save(preview_path, quality=92)
            document["previewUrl"] = _public(preview_path)
            documents.append(document)
        documents.sort(key=lambda item: item["quality"]["overall"], reverse=True)
        (job_dir / "documents.json").write_text(
            json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "jobId": job_id,
            "input": {
                "name": resolved_title,
                "feature": feature,
                "vibe": vibe,
                "style": style,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)

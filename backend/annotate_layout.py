#!/usr/bin/env python3
"""本地版式标注工具。

跑一条命令，浏览器会自动打开：

    py annotate_layout.py --style style2

左侧选图，右侧选区域，在图上拖框即可。保存后会在
training/ 下生成 layout_annotations_<style>.json，可直接用于训练。
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parent
TRAINING = ROOT / "training"
POSTERS = TRAINING / "reference_posters"

STYLE_REGIONS = {
    "style1": [
        "heroTitle", "cnTitle", "product", "launch", "badge",
        "footer", "leftCallout", "leftDetail", "rightDetail",
    ],
    "style2": ["product", "name", "point1", "point2", "point3", "slogan", "intro"],
}

REGION_LABELS = {
    "heroTitle": "英文标题", "cnTitle": "中文标题", "product": "商品主体",
    "launch": "右上标签", "badge": "徽章", "footer": "页脚",
    "leftCallout": "左侧强调", "leftDetail": "左下落点", "rightDetail": "右下落点",
    "name": "商品名", "point1": "卖点 1", "point2": "卖点 2", "point3": "卖点 3",
    "slogan": "口号", "intro": "介绍",
}


def _hex(color) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(value))) for value in color)


def _palette(path: Path) -> dict[str, str]:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        image.thumbnail((96, 96))
        pixels = list(image.getdata())
    ordered = sorted(pixels, key=lambda p: p[0] * 0.299 + p[1] * 0.587 + p[2] * 0.114)
    light = ordered[max(0, int(len(ordered) * 0.9)):]
    paper = tuple(round(sum(p[i] for p in light) / max(1, len(light))) for i in range(3))

    def saturation(pixel) -> float:
        maximum, minimum = max(pixel), min(pixel)
        return 0.0 if maximum == 0 else (maximum - minimum) / maximum

    accent = max(pixels, key=saturation)
    if saturation(accent) < 0.15:
        accent = tuple(max(0, value - 90) for value in paper)
    soft = tuple(round(value + (255 - value) * 0.72) for value in accent)
    return {"accent": _hex(accent), "soft": _hex(soft), "paper": _hex(paper)}


def _list_images(style: str) -> list[Path]:
    folder = POSTERS / style
    if not folder.is_dir():
        return []
    return sorted(
        path for path in folder.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )


def _canvas_ratio(path: Path) -> float:
    with Image.open(path) as image:
        return round(image.width / max(1, image.height), 4)


PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>版式标注</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Microsoft YaHei", system-ui, sans-serif; background: #f6f3ec; color: #2b2723; }
  .app { display: flex; height: 100vh; }
  aside { width: 220px; border-right: 1px solid #d6cec0; padding: 16px; overflow-y: auto; }
  aside.right { border-right: 0; border-left: 1px solid #d6cec0; width: 240px; }
  h2 { font-size: 14px; margin: 0 0 12px; letter-spacing: .08em; }
  .item { padding: 8px 10px; border: 1px solid #d6cec0; margin-bottom: 6px; cursor: pointer; font-size: 12px; word-break: break-all; }
  .item.active { border-color: #2b2723; background: #fff; }
  .item.done::after { content: " ✓"; color: #7b8a72; }
  .region { padding: 8px 10px; border: 1px solid #d6cec0; margin-bottom: 6px; cursor: pointer; font-size: 13px; display: flex; justify-content: space-between; gap: 8px; }
  .region.active { border-color: #2b2723; background: #fff; }
  .region small { color: #8a8078; font-size: 10px; }
  main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  #stage { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; min-height: 0; }
  #wrap { position: relative; display: inline-block; max-width: 100%; max-height: 100%; }
  #img { display: block; max-width: 100%; max-height: calc(100vh - 140px); user-select: none; }
  #canvas { position: absolute; inset: 0; cursor: crosshair; }
  footer { border-top: 1px solid #d6cec0; padding: 12px 20px; display: flex; gap: 12px; align-items: center; font-size: 12px; }
  button { border: 1px solid #2b2723; background: #2b2723; color: #f6f3ec; padding: 8px 14px; cursor: pointer; font-size: 12px; }
  button.ghost { background: transparent; color: #2b2723; }
  button:disabled { opacity: .4; cursor: not-allowed; }
  #log { color: #7b8a72; }
</style>
</head>
<body>
<div class="app">
  <aside>
    <h2>参考图</h2>
    <div id="images"></div>
  </aside>
  <main>
    <div id="stage">
      <div id="wrap">
        <img id="img" alt="参考图">
        <canvas id="canvas"></canvas>
      </div>
    </div>
    <footer>
      <button class="ghost" id="clear">清空当前图</button>
      <button class="ghost" id="prev">上一张</button>
      <button class="ghost" id="next">下一张</button>
      <span id="log"></span>
      <span style="flex:1"></span>
      <button id="save">保存 JSON</button>
    </footer>
  </main>
  <aside class="right">
    <h2>区域（先选区域，再在图上拖框）</h2>
    <div id="regions"></div>
  </aside>
</div>
<script>
const params = new URLSearchParams(location.search);
const style = params.get('style') || 'style2';
const state = { images: [], regions: [], index: 0, boxes: {}, active: null, drag: null };
const colors = ['#e05b6d', '#3f6fb5', '#5b8a4a', '#c07a2c', '#7a5bab', '#2f8a8a', '#9a5b3f', '#555555', '#b03a7a'];

const img = document.getElementById('img');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

async function boot() {
  const info = await (await fetch('/api/state?style=' + encodeURIComponent(style))).json();
  state.images = info.images;
  state.regions = info.regions;
  state.canvasRatio = info.canvasRatio;
  state.boxes = info.boxes || {};
  renderLists();
  if (state.images.length) selectImage(0);
}

function regionLabel(key) { return ({ product: '商品主体', name: '商品名', point1: '卖点 1', point2: '卖点 2', point3: '卖点 3', slogan: '口号', intro: '介绍' })[key] || key; }

function renderLists() {
  const images = document.getElementById('images');
  images.innerHTML = '';
  state.images.forEach((name, index) => {
    const div = document.createElement('div');
    const box = state.boxes[name] || {};
    div.className = 'item' + (index === state.index ? ' active' : '') + (state.regions.every(r => box[r]) ? ' done' : '');
    div.textContent = name;
    div.onclick = () => selectImage(index);
    images.appendChild(div);
  });
  const regions = document.getElementById('regions');
  regions.innerHTML = '';
  const current = state.boxes[state.images[state.index]] || {};
  state.regions.forEach((key, i) => {
    const div = document.createElement('div');
    div.className = 'region' + (state.active === key ? ' active' : '');
    div.innerHTML = '<span>' + regionLabel(key) + '</span><small>' + (current[key] ? '已标注' : '待标注') + '</small>';
    div.onclick = () => { state.active = key; renderLists(); };
    regions.appendChild(div);
  });
}

function selectImage(index) {
  state.index = index;
  state.active = null;
  img.src = '/images/' + encodeURIComponent(style) + '/' + encodeURIComponent(state.images[index]);
  renderLists();
}

img.onload = () => { resizeCanvas(); draw(); };
window.addEventListener('resize', () => { resizeCanvas(); draw(); });

function resizeCanvas() {
  canvas.width = img.clientWidth;
  canvas.height = img.clientHeight;
  canvas.style.width = img.clientWidth + 'px';
  canvas.style.height = img.clientHeight + 'px';
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const box = state.boxes[state.images[state.index]] || {};
  state.regions.forEach((key, i) => {
    const rect = box[key];
    if (!rect) return;
    const [x, y, w, h] = rect;
    const left = x * canvas.width, top = y * canvas.height;
    const width = w * canvas.width, height = h * canvas.height;
    ctx.strokeStyle = colors[i % colors.length];
    ctx.lineWidth = 2;
    ctx.strokeRect(left, top, width, height);
    ctx.fillStyle = colors[i % colors.length];
    ctx.fillRect(left, Math.max(0, top - 16), Math.min(120, width), 16);
    ctx.fillStyle = '#fff';
    ctx.font = '11px Microsoft YaHei';
    ctx.fillText(regionLabel(key), left + 4, Math.max(12, top - 4));
  });
}

canvas.addEventListener('pointerdown', (event) => {
  if (!state.active) return;
  const rect = canvas.getBoundingClientRect();
  const startX = (event.clientX - rect.left) / rect.width;
  const startY = (event.clientY - rect.top) / rect.height;
  state.drag = { startX, startY };
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener('pointermove', (event) => {
  if (!state.drag) return;
  const rect = canvas.getBoundingClientRect();
  const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
  const box = state.boxes[state.images[state.index]] || (state.boxes[state.images[state.index]] = {});
  box[state.active] = [
    Math.round(Math.min(state.drag.startX, x) * 10000) / 10000,
    Math.round(Math.min(state.drag.startY, y) * 10000) / 10000,
    Math.round(Math.abs(x - state.drag.startX) * 10000) / 10000,
    Math.round(Math.abs(y - state.drag.startY) * 10000) / 10000,
  ];
  draw();
});

canvas.addEventListener('pointerup', () => {
  state.drag = null;
  renderLists();
});

document.getElementById('clear').onclick = () => {
  state.boxes[state.images[state.index]] = {};
  draw(); renderLists();
};
document.getElementById('prev').onclick = () => selectImage(Math.max(0, state.index - 1));
document.getElementById('next').onclick = () => selectImage(Math.min(state.images.length - 1, state.index + 1));
document.getElementById('save').onclick = async () => {
  const log = document.getElementById('log');
  log.textContent = '保存中…';
  const response = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ style, regions: state.regions, boxes: state.boxes }),
  });
  const result = await response.json();
  log.textContent = response.ok ? ('已保存：' + result.path) : ('失败：' + result.detail);
};

boot();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    style = "style2"
    regions: list[str] = []

    def log_message(self, *_args) -> None:  # 安静一点
        return

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/state":
            query = parse_qs(parsed.query)
            style = (query.get("style") or [self.style])[0]
            images = _list_images(style)
            existing = TRAINING / f"layout_annotations_{style}.json"
            boxes = {}
            if existing.is_file():
                payload = json.loads(existing.read_text(encoding="utf-8"))
                for example in payload.get("examples", []):
                    boxes[Path(example["image"]).name] = example.get("regions", {})
            self._json({
                "style": style,
                "images": [path.name for path in images],
                "regions": self.regions,
                "canvasRatio": _canvas_ratio(images[0]) if images else 0.75,
                "boxes": boxes,
            })
            return
        if parsed.path.startswith("/images/"):
            parts = parsed.path.split("/", 3)
            if len(parts) < 4:
                self.send_error(404)
                return
            target = (POSTERS / parts[2] / parts[3]).resolve()
            if POSTERS.resolve() not in target.parents or not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/save":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        style = str(payload.get("style", self.style))
        regions = payload.get("regions") or self.regions
        boxes = payload.get("boxes") or {}
        images = _list_images(style)
        if not images:
            self._json({"detail": "该风格没有参考图"}, 400)
            return
        examples = []
        for image in images:
            example_regions = boxes.get(image.name) or {}
            missing = [region for region in regions if not example_regions.get(region)]
            if missing:
                self._json({"detail": f"{image.name} 还缺区域：{', '.join(missing)}"}, 400)
                return
            examples.append({
                "image": f"reference_posters/{style}/{image.name}",
                "palette": _palette(image),
                "regions": {region: example_regions[region] for region in regions},
            })
        output = TRAINING / f"layout_annotations_{style}.json"
        output.write_text(json.dumps({
            "schemaVersion": 1,
            "canvasRatio": _canvas_ratio(images[0]),
            "examples": examples,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._json({"path": str(output)})


def main() -> None:
    parser = argparse.ArgumentParser(description="本地版式标注工具")
    parser.add_argument("--style", default="style2")
    parser.add_argument("--regions", default="", help="逗号分隔的区域名，留空使用该风格的默认集合")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    regions = [item.strip() for item in args.regions.split(",") if item.strip()]
    if not regions:
        regions = STYLE_REGIONS.get(args.style, STYLE_REGIONS["style2"])

    Handler.style = args.style
    Handler.regions = regions
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/?style={args.style}"
    print(f"标注工具已启动：{url}")
    print("区域：" + "、".join(REGION_LABELS.get(r, r) for r in regions))
    print("标注完成后点右下角“保存 JSON”，然后按 Ctrl+C 退出。")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。")


if __name__ == "__main__":
    main()

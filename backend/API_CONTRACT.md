# SmartMerch 前后端接口约定

后端默认地址：`http://127.0.0.1:8000`。Vite 开发服务器可通过 `VITE_API_BASE_URL` 保存该地址。

## 1. 自动抠图

`POST /api/cutout`，请求类型为 `multipart/form-data`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `image` | File | 是 | JPG、PNG 或 WEBP 商品图片 |

返回字段：

```json
{
  "jobId": "任务编号",
  "imageName": "原文件名.jpg",
  "cutoutUrl": "/generated/任务编号/product_cutout.png",
  "productFeatures": {
    "width": 500,
    "height": 900,
    "aspect_ratio": 0.5556,
    "shape": "vertical",
    "mean_rgb": [220, 180, 190],
    "brightness": 0.7712
  }
}
```

## 2. AI 翻译与视觉文案

`POST /api/translate` 使用普通文本模型翻译商品名，不发送商品图片。请求为 JSON：

```json
{ "text": "草莓奶油丹麦" }
```

返回：

```json
{ "source": "草莓奶油丹麦", "translation": "Strawberry Cream Danish", "model": "qwen-plus" }
```

文本模型通过 `AI_TEXT_MODEL` 配置，与下方视觉模型 `AI_MODEL` 相互独立。

`POST /api/analyze-copy`，请求类型为 `multipart/form-data`，字段为 `image`。

前端对应关系：

- `category` → `state.name`
- `visible_features.join('，')` → `state.feature`
- 用户仍可手动修改 `name` 和 `feature`
- `copywriting` 用于让用户选择标题与副标题

推荐使用 `POST /api/copy` 获取适配当前海报的完整文案。请求类型为 `multipart/form-data`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `jobId` | string | `/api/cutout` 返回的任务编号 |
| `name` | string | 已填写的英文商品名，可为空 |
| `feature` | string | 已填写的中文商品名，作为视觉文案生成的已知信息 |
| `selling_points` | JSON string | 用户已填写的卖点，最多 3 条 |
| `footer` | string | 品牌口号 |
| `launch_text` | string | 右上标签 |
| `badge_text` | string | 徽章文字 |

返回 `copywriting` 中的每个方案都包含 `title、subtitle、sellingPoints、footer、launchText、badgeText`。所有内容只是建议，用户选择后仍可修改。

`POST /api/copy/refine` 接收 JSON：

```json
{
  "jobId": "任务编号",
  "current": { "title": "英文名", "subtitle": "中文名" },
  "instruction": "英文名再短一些，第二条卖点突出便携"
}
```

模型只修改意见涉及的字段，其余文案保持不变。未配置视觉模型时该接口返回 503，不会伪造修改结果。

## 3. 生成海报

`POST /api/generate`，请求类型为 `multipart/form-data`。

接口使用 `models/bakery_editorial_layout.json` 中由 4 张参考海报训练得到的版式先验，输出 1080×1440 的可编辑海报。旧版 `templates/*.json` 不再参与主生成链路。

| SmartMerch 字段 | 类型 | 必填 | 后端用途 |
| --- | --- | --- | --- |
| `image` | File | 是 | 商品原图；后端会重新抠图以保证任务独立 |
| `name` | string | 是 | 英文商品名，显示在标题区第一行 |
| `feature` | string | 否 | 中文商品名，显示在英文名下一行 |
| `selling_points` | JSON string | 否 | 最多 3 条卖点的 JSON 数组；根据数量动态排版 |
| `footer` | string | 否 | 底部品牌口号 |
| `launch_text` | string | 否 | 右上标签，默认“新品上市” |
| `badge_text` | string | 否 | 徽章文字，默认“NEW!” |
| `price` | string | 否 | 价格文字；为空时不添加价格图层 |

为兼容旧页面，接口仍接受 `title` 和 `subtitle`；它们的优先级高于 `name` 和 `feature`。

返回的 `candidates` 当前只包含一套学习版式方案，附带 `layoutModel`、`palette`、可编辑 `elements` 和预览图地址。生成链路不再计算或返回质量评分；独立的 `/api/evaluate` 仍保留供后续实验使用。

## 4. 其他接口

- `GET /api/health`：服务和可选能力状态。
- `POST /api/evaluate`：重新评价一个分层海报文档。
- `POST /api/render`：把分层文档导出为 PNG。
- `GET /api/poster-design/templates`：可选；只有部署了本地 poster-design 素材库时可用。

前端已按上述字段完成接入，并会保留原始 `File` 供抠图、视觉分析和生成接口使用。

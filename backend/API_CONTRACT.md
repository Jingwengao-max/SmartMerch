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

## 2. 视觉识别与文案

`POST /api/analyze-copy`，请求类型为 `multipart/form-data`，字段为 `image`。

前端对应关系：

- `category` → `state.name`
- `visible_features.join('，')` → `state.feature`
- 用户仍可手动修改 `name` 和 `feature`
- `copywriting` 用于让用户选择标题与副标题

### 2.1 结构化文案（推荐新接口）

`POST /api/copy`，请求类型为 `multipart/form-data`。输入的是**抠图后的商品图**，
优先用 `jobId` 复用 `/api/cutout` 已经产出的透明图，不需要重新上传。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `jobId` | string | 二选一 | `/api/cutout` 返回的任务号 |
| `image` | File | 二选一 | 没有 `jobId` 时直接上传原图；后端会先抠图再生成 |
| `name` / `feature` / `vibe` / `style` / `price` / `promo` | string | 否 | 用户已填写的商品资料（`promo` 即活动信息），作为生成依据 |
| `selling_points` | string | 否 | 用户填写的卖点，JSON 数组或顿号/分号分隔；模型会把它拆成一条一项返回 |

返回结构与字段含义：

```json
{
  "source": "ai",
  "jobId": "任务编号",
  "imageSource": "cutout",
  "identification": {
    "category": "陶瓷马克杯",
    "color": "米白",
    "visible_features": ["圆柱杯身", "带把手"],
    "scene": ["办公桌"],
    "confidence": 0.82,
    "warning": "尺寸为视觉估计，请人工核对。"
  },
  "variants": [
    {
      "title": "手作陶瓷杯",
      "subtitle": "每一只都独一无二",
      "selling_points": ["手工拉坯", "耐高温"],
      "price_text": "￥39",
      "promo_text": "第二件半价"
    }
  ],
  "suggested": { "name": "陶瓷马克杯", "feature": "圆柱杯身，带把手", "price": "￥39", "promo": "第二件半价", "selling_points": ["手工拉坯"] },
  "meta": { "provider": "openai_compat", "model": "qwen3-vl-plus" }
}
```

约束与反馈约定：

- `variants` 最多 3 组，字段超长会被后端截断。
- **`price_text`**：用户填了 `price` 就一律以用户为准（`price_estimated=false`）；
  没填时模型会给出推测的参考价，此时 `price_estimated=true`，界面显示「参考价 · 请核对」。
- **`promo_text`**：只能来自用户填写的 `promo`。模型若自行编造折扣或优惠，服务端会清空并写入
  `identification.warning`。
- `source` 为 `ai` 表示调用了视觉模型，为 `local_fallback` 表示未配置模型，
  只返回按图片颜色生成的通用占位文案。
- `/api/analyze-copy` 保留为旧版接口，内部复用同一套逻辑，返回旧字段结构。

### 2.2 按意见修改文案

`POST /api/copy/refine`，请求类型为 `application/json`。用户对某几条文案提意见后调用。

```json
{
  "jobId": "任务编号",
  "current": { "title": "…", "subtitle": "…", "selling_points": ["…"], "price_text": "", "promo_text": "" },
  "feedback": { "title": "再活泼一点", "subtitle": "", "selling_points": ["太长"], "price_text": "", "promo_text": "" },
  "context": { "name": "", "feature": "", "selling_points": [], "vibe": "", "style": "", "price": "", "promo": "" }
}
```

约定：

- `feedback` 的 `selling_points` 按位置与 `current.selling_points` 一一对应；`context` 可省略。
- **只改写提了意见的条目**，未提意见的条目原样保留。
- 返回结构同 `/api/copy`，但 `variants` 只有 1 组（修改后的这一组），并带上 `refinedFrom` 作为改动前的副本。
- 一条意见都没有时返回 400。

## 3. 生成海报

`POST /api/generate`，请求类型为 `multipart/form-data`。

| SmartMerch 字段 | 类型 | 必填 | 后端用途 |
| --- | --- | --- | --- |
| `image` | File | 是 | 商品原图；后端会重新抠图以保证任务独立 |
| `name` | string | 是 | 商品名称，同时作为海报主标题 |
| `feature` | string | 否 | 商品特点，同时作为副标题 |
| `vibe` | string | 否 | 上新、节日、品牌、种草、清仓等营销方向 |
| `style` | string | 是 | `natural`、`minimal`、`retro`、`festive`、`tech` |
| `price` | string | 否 | 价格文字；为空时不添加价格图层 |
| `promo` | string | 否 | 活动信息文字；为空时不添加图层 |
| `selling_points` | string | 否 | 卖点，JSON 数组或顿号/分号分隔；每项生成一个图层 |
| `background_provider` | string | 否 | `auto`、`local`、`template`、`postercraft`，默认 `auto` |

为兼容旧页面，接口仍接受 `title` 和 `subtitle`；它们的优先级高于 `name` 和 `feature`。

返回的 `candidates` 当前只包含后端评分最高的一套方案。评分保留在返回数据中供推荐使用，前端不必显示。

## 4. 其他接口

- `GET /api/health`：服务和可选能力状态。
- `POST /api/evaluate`：重新评价一个分层海报文档。
- `POST /api/render`：把分层文档导出为 PNG。
- `GET /api/poster-design/templates`：可选；只有部署了本地 poster-design 素材库时可用。

## SmartMerch 前端目前需要调整的状态

当前 `state.image` 只保存 Data URL。接入时应额外保留原始 `File`，例如 `sourceFile: File | null`，因为 `FormData` 必须上传文件本身。还建议新增：

- `cutoutUrl: string`
- `jobId: string`
- `candidates: PosterCandidate[]`
- `selectedCandidateIndex: number`
- `error: string`

生成数量不应写死，应显示 `candidates.length`；当前后端返回评分最高的一套。

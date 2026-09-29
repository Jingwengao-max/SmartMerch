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

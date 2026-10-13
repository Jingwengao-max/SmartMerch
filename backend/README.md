# AI商品海报工作室

SmartMerch 的海报生成后端，实现“商品照片 → 自动抠图 → 背景生成 → 候选排版 → 质量评分 → 高清导出”闭环。

## 当前功能

- 上传 PNG、JPG、WEBP 商品照片
- 普通照片通过 rembg 自动抠图，透明 PNG 直接使用
- 分析商品长宽比、形态、平均色和亮度
- 使用三套 JSON 模板生成候选布局
- 默认使用商品颜色生成稳定的本地背景
- 可选调用独立的 PosterCraft 背景服务
- 检查安全边距、遮挡、可读性、平衡和商品突出程度
- 后端按 1080×1350 输出高清 PNG
- 记录用户最终选择，为后续模板推荐模型收集数据

## 一键启动

在项目文件夹中打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

也可以分开执行：

```powershell
py -m pip install -r requirements.txt
py -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

接口文档打开 `http://127.0.0.1:8000/docs`。前后端字段见 `API_CONTRACT.md`。

首次处理普通照片时，rembg可能需要下载抠图模型。透明PNG不需要下载模型。

## AI商品识别与文案

抠图完成后，后端立刻结合商品图出一版文案，并按块返回：主标题、副标题、每条卖点、价格、活动各一块，
每条卖点后面都是一个独立图层。用户可以在任意条目下填写「修改意见」，点按钮后只改写提了意见的条目，
其余条目原样保留。未配置接口时不会假装识别商品，只给出通用占位或复用用户已填内容。

价格策略：用户填了价格就一律以用户的为准；没填时模型会根据商品推测一个**参考价**，
返回里带 `price_estimated` 标记，界面显示为「参考价 · 请核对」，务必人工确认。
活动/优惠信息不会由模型编造，只能来自用户输入。

配置支持图片输入的OpenAI兼容接口：

推荐把 `.env.example` 复制成 `.env` 后填好，后端启动时会自动读取，不必每次设置环境变量：

```text
AI_API_URL=https://你的服务地址/v1
AI_API_KEY=你的密钥
AI_MODEL=你的视觉模型名称
```

也可以临时用环境变量覆盖（优先级更高）：

```powershell
$env:AI_API_URL="https://你的服务地址/v1/chat/completions"
$env:AI_API_KEY="你的密钥"
$env:AI_MODEL="你的视觉模型名称"
py -m uvicorn api:app --host 127.0.0.1 --port 8000
```

密钥仅从环境变量读取，不会写入项目文件。模型被要求不得虚构品牌、容量、材质、价格、保温时长和产品功效，生成结果仍需人工核对。

### 文案模块结构

视觉文案的实现集中在 `copywriting/` 包，业务代码只依赖它的公开入口，
换模型或换网关都不需要改调用方：

```text
copywriting/
├── __init__.py         公开入口：generate_copy() / CopyRequest / configured()
├── config.py           环境变量读取与端点拼接
├── schema.py           文案契约与长度校验
├── prompts.py          系统提示词（含防编造约束）
├── compose.py          合并模型输出与用户事实，服务端防幻觉校验
├── legacy.py           旧 /api/analyze-copy 的兼容映射
└── providers/
    ├── __init__.py     按配置选择 provider
    ├── openai_compat.py  OpenAI 兼容的视觉模型调用
    └── local_fallback.py 未配置模型时的颜色兜底文案
```

`ai_copywriter.py` 退化为兼容薄壳，旧导入仍然可用。文案图层由 `copy_layout.py`
追加，不改动 `layout_engine.py` 的模板评分逻辑。`env_loader.py` 负责读取
`backend/.env`，只补全缺失的环境变量。

可选环境变量：`AI_TIMEOUT`（默认 120 秒）、`AI_IMAGE_MAX_EDGE`（默认 1024，
送模型前的最长边）。本地部署（localhost / 内网地址）允许省略 `AI_API_KEY`。

国内课程项目优先推荐阿里云百炼 `qwen3-vl-plus`：中文商品识别、图片输入和OpenAI兼容接口都与本项目匹配。代码默认模型已经设置为该名称。配置示例：

```powershell
$env:AI_API_URL="https://你的WorkspaceId.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
$env:AI_API_KEY="你的百炼API Key"
$env:AI_MODEL="qwen3-vl-plus"
```

也可以换成任何支持 `chat/completions`、Base64图片和JSON输出的视觉模型。

## 模板背景图库

“内置本地背景”由本项目根据商品颜色程序化生成，并非poster-design素材。“模板图库”会读取 `backgrounds` 文件夹中的PNG/JPG/WEBP图片。可以把获得授权的纯背景导出到该目录；若目录为空，系统自动回退到内置背景。

## PosterCraft接入方式

系统在没有PosterCraft时也能完整运行，背景引擎会自动回退为本地生成。

当PosterCraft部署在GPU服务器后，为它增加一个HTTP接口。接口接收：

```json
{"prompt": "commercial product poster background ..."}
```

返回以下任意一种结果：

1. 响应正文直接返回 `image/png` 或 `image/jpeg`；
2. JSON返回 `{"image_base64": "..."}`。

启动本系统前配置接口地址：

```powershell
$env:POSTERCRAFT_URL="http://GPU服务器地址:端口/generate"
py -m uvicorn api:app --host 127.0.0.1 --port 8000
```

网页选择“自动”时优先调用PosterCraft，失败自动使用本地背景；选择“仅PosterCraft”时，失败会显示错误。

## SmartMerch 集成

SmartMerch 前端使用 `image、name、feature、vibe、style`；生成接口已经兼容这些字段，同时保留旧版 `title、subtitle` 字段。新增 `/api/cutout` 供上传步骤真正执行抠图，Vite 默认开发地址已加入跨域白名单。

前端暂不随本目录上传，`web/` 已加入 `.gitignore`。运行时图片、反馈数据、模型缓存以及 `vendor/poster-design` 第三方源码同样不会进入仓库。

## 目录说明

```text
poster_project/
├── api.py                   Web API与高清渲染
├── background_provider.py   本地/PosterCraft背景适配器
├── layout_engine.py         模板候选生成与布局评分
├── quality_evaluator.py     海报质量评价
├── main.py                  原命令行生成程序
├── record_feedback.py       原命令行反馈记录
├── templates/               三套版式模板
├── API_CONTRACT.md          SmartMerch 前后端字段约定
├── .env.example             环境变量示例，不包含真实密钥
├── generated/               Web生成文件（运行后创建）
├── data/                    用户选择记录
└── output/                  原命令行输出
```

## 运行测试

```powershell
py -m unittest -v
```

## 与 poster-design 的关系

当前编辑器按poster-design的核心交互拆出了分层画布、拖动、缩放控制点、图层面板、删除、撤销/重做、模板JSON导入导出、属性编辑和服务端出图。候选方案继续由后端评分排序，但分数和评分细节不在前端展示。

poster-design 是可选本地模板源，源码放在 `vendor/poster-design` 时后端可读取其种子模板库。该目录默认不上传；若未来分发或部署其代码，需要遵守 AGPL-3.0-or-later 许可证。

## 安全提示

宣传文案必须来自真实商品资料。不要让系统自动虚构容量、材质、保温时长或功效。
价格是唯一的例外：模型可以给出推测的参考零售价，但会被明确标注并提示核对；
折扣、优惠、活动等承诺仍然只能由用户提供。

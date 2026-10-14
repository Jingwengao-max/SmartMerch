# AI商品海报工作室

SmartMerch 的海报生成后端，实现“商品照片 → 自动抠图 → 参考样式学习 → 自适应排版 → 分层编辑 → 高清导出”闭环。

## 当前功能

- 上传 PNG、JPG、WEBP 商品照片
- 普通照片通过 rembg 自动抠图，透明 PNG 直接使用
- 分析商品长宽比、形态、平均色和亮度
- 从 4 张参考海报的区域标注中训练小样本版式先验
- 根据新商品的长宽比与主色自动调整商品尺寸、强调色和柔和背景色
- 根据商品抠图轮廓自动生成同色简笔画装饰
- 生成超大标题、中央商品、NEW 徽章、最多三条卖点和波浪底栏等可编辑图层
- 后端按 1080×1440（3:4）输出高清 PNG
- 编辑器预览与 PNG 导出统一使用 LXGW WenKai 字体

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

页面既支持手动填写，也通过同一个 AI 模型提供两项能力：“生成英文名”仅接收中文商品名并返回英文标题，不上传图片；“AI 推荐”分析商品图，生成卖点、底部口号等候选文案。所有结果仍可人工修改，每组候选支持按意见重写。未配置接口时使用安全的本地通用建议，不会假装识别商品。

配置支持图片输入的OpenAI兼容接口：

```powershell
$env:AI_API_URL="https://你的服务地址/v1/chat/completions"
$env:AI_API_KEY="你的密钥"
$env:AI_MODEL="你的视觉模型名称"
py -m uvicorn api:app --host 127.0.0.1 --port 8000
```

密钥仅从环境变量读取，不会写入项目文件。模型被要求不得虚构品牌、容量、材质、价格、保温时长和产品功效，生成结果仍需人工核对。

国内课程项目优先推荐阿里云百炼 `qwen3-vl-plus`：中文商品识别、图片输入和OpenAI兼容接口都与本项目匹配。代码默认模型已经设置为该名称。配置示例：

```powershell
$env:AI_API_URL="https://你的WorkspaceId.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
$env:AI_API_KEY="你的百炼API Key"
$env:AI_MODEL="qwen3-vl-plus"
```

也可以换成任何支持 `chat/completions`、Base64图片和JSON输出的视觉模型。

## 训练参考版式

当前训练集位于 `training/reference_posters/`，区域与配色标注位于 `training/layout_annotations.json`。四张样本不足以可靠微调扩散模型，因此当前采用可解释的小样本统计模型：训练脚本学习各版式区域的归一化坐标和配色角色，输出 `models/bakery_editorial_layout.json`。

重新训练：

```powershell
cd backend
py train_layout_model.py
```

增加参考海报时，将图片放入 `training/reference_posters/`，并在标注文件中增加同名样本及 9 个区域。重新运行训练脚本即可更新模型，无需修改生成代码。

## SmartMerch 集成

SmartMerch 前端使用 `image、name、feature、selling_points、footer、launch_text、badge_text`。`selling_points` 最多包含 3 条，后端按实际数量动态分配版面位置。视觉模型只返回文案建议，用户在生成前和图层编辑阶段都可以修改；生成接口同时保留旧版 `title、subtitle、style、left_detail、right_detail` 字段以兼容旧调用方。`/api/cutout` 供上传步骤执行抠图，Vite 默认开发地址已加入跨域白名单。

运行时图片、反馈数据、模型缓存以及 `vendor/poster-design` 第三方源码不会进入仓库。

## 目录说明

```text
poster_project/
├── api.py                   Web API与高清渲染
├── learned_layout.py        学习版式的实例化与自适应配色
├── train_layout_model.py    小样本版式训练脚本
├── models/                  训练后的版式模型
├── training/                参考海报与区域标注
├── layout_engine.py         共用画布、字体与商品特征提取
├── quality_evaluator.py     可选的海报质量实验接口
├── main.py                  原命令行生成程序
├── record_feedback.py       原命令行反馈记录
├── templates/               旧版模板（仅保留兼容，不再用于主生成接口）
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

当前编辑器参考 poster-design 的核心交互，实现了分层画布、拖动、缩放控制点、图层面板、删除、撤销/重做、属性编辑和服务端出图。主生成链路只输出一套学习版式，不在前端展示实验评分。

poster-design 是可选本地模板源，源码放在 `vendor/poster-design` 时后端可读取其种子模板库。该目录默认不上传；若未来分发或部署其代码，需要遵守 AGPL-3.0-or-later 许可证。

## 安全提示

宣传文案必须来自真实商品资料。不要让系统自动虚构容量、材质、保温时长或功效。

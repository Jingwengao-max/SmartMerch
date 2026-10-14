# 智绘商品 SmartMerch

智绘商品是一个面向课程实验与竞赛展示的 AI 商品宣传海报生成系统。用户上传一张商品照片，系统完成自动抠图、商品文案辅助、参考版式生成、分图层编辑和高清 PNG 导出，形成“商品图 → 可编辑宣传海报”的完整闭环。

## 一、项目当前状态

项目目前已经打通以下流程：

1. 上传 JPG、PNG 或 WEBP 商品照片。
2. 使用 `rembg` 自动抠出商品主体；透明 PNG 可直接使用。
3. 人工填写中文商品名，使用普通文本模型翻译英文商品名。
4. 使用视觉模型分析商品图片，推荐卖点、品牌口号和标签文案。
5. 用户选择 AI 建议后仍可人工修改，也可以输入意见让模型局部重写。
6. 根据 4 张参考海报学习出的版式先验生成 1080×1440 海报。
7. 根据商品抠图轮廓生成同色简笔画装饰。
8. 在分图层编辑器中调整文字、位置、尺寸和颜色。
9. 导出 PNG，文件名为 `智绘商品-商品名称.png`。

AI 能力是可选的。没有配置 API 时，抠图、手工填写、海报生成、分层编辑和 PNG 导出仍可使用；AI 翻译、AI 推荐和按意见改写不可用。

## 二、输入与输出

### 输入

- 一张商品照片；
- 中文商品名；
- 可选的英文商品名；
- 最多 3 条商品卖点；
- 可选的底部品牌口号、右上标签和徽章文字。

### 输出

- 一张 1080×1440 的商品宣传海报；
- 一份包含图片、文字和装饰元素的可编辑图层文档；
- 一张高清 PNG 图片。

## 三、技术架构

### 前端

- Vue 3、TypeScript、Vite、Tailwind CSS；
- 自研分图层海报编辑器；
- LXGW WenKai 与 Noto Sans SC 字体。

### 后端

- Python、FastAPI、Pillow、rembg；
- OpenAI 兼容 Chat Completions 接口。

### AI 模块

- 文本翻译：普通文本模型，默认 `deepseek-chat`；只接收中文商品名，不上传图片。
- 视觉推荐：支持图片输入的视觉模型；根据商品图生成卖点和宣传文案。
- 版式生成：根据 4 张参考海报的区域标注训练可解释的小样本统计模型，不是扩散模型微调。
- 自动抠图：rembg。

## 四、目录结构

```text
SmartMerch/
├── src/                         Vue 前端源码
│   ├── components/studio/       上传、文案、预览和图层编辑组件
│   ├── composables/useStudio.ts 工作室状态与完整业务流程
│   └── services/posterApi.ts    前后端请求封装
├── backend/
│   ├── api.py                   FastAPI 接口、静态页面托管和 PNG 渲染
│   ├── ai_copywriter.py         文本翻译、视觉推荐和按意见改写
│   ├── learned_layout.py        学习版式的实例化和自适应配色
│   ├── layout_engine.py         字体、画布和商品特征提取
│   ├── train_layout_model.py    参考版式训练脚本
│   ├── models/                  训练后的版式模型
│   ├── training/                4 张参考海报及区域标注
│   ├── API_CONTRACT.md          前后端接口字段说明
│   ├── requirements.txt         Python 依赖
│   └── test_pipeline.py         后端测试
├── start-smartmerch.cmd         Windows 首次启动入口
├── start.ps1                    安装、构建和启动脚本
├── open-smartmerch.cmd          已完成安装后的快速启动入口
├── package.json                 前端依赖和命令
└── README.md                    本说明
```

## 五、运行环境

推荐环境：

- Windows 10/11；
- Git；
- Node.js 20 或更高版本；
- Python 3.11 或 3.12。

Python 3.14 可能与部分 `rembg/pymatting/numba` 版本存在兼容问题，新用户优先使用 Python 3.11 或 3.12。

## 六、新用户首次运行

### 1. 获取代码

```powershell
git clone https://github.com/Jingwengao-max/SmartMerch.git
cd SmartMerch
```

### 2. 不使用 AI，直接体验基础功能

```powershell
.\start-smartmerch.cmd
```

脚本会安装依赖、构建网页并启动服务。程序会自动寻找空闲端口，终端显示类似：

```text
SmartMerch preview: http://127.0.0.1:54321/studio
Uvicorn running on http://127.0.0.1:54321
```

如果浏览器没有自动打开，复制 `SmartMerch preview:` 后面的完整地址。使用期间不要关闭后端终端。首次处理普通照片时，rembg 可能需要联网下载抠图模型。

## 七、配置 AI 后完整运行

API Key 不得写入源码或上传到 GitHub。项目根目录的 `.gitignore` 已忽略 `.env`，当前程序主要从启动终端的环境变量中读取配置。

### 方案 A：视觉模型和文本模型来自不同平台

以下示例使用千问AI平台的视觉模型和 DeepSeek 官方文本模型。请将示例 Key 替换为各平台创建的完整 Key，不要使用页面显示的脱敏字符串。

```powershell
cd "C:\你的路径\SmartMerch"

# 视觉模型：必须支持图片输入
$env:AI_API_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
$env:AI_API_KEY = Read-Host "粘贴视觉模型平台的完整 API Key"
$env:AI_MODEL = "qwen3.8-max"

# 普通文本模型：只负责中文商品名翻译
$env:AI_TEXT_API_URL = "https://api.deepseek.com/v1"
$env:AI_TEXT_API_KEY = Read-Host "粘贴 DeepSeek 官方完整 API Key"
$env:AI_TEXT_MODEL = "deepseek-chat"
```

### 方案 B：同一平台同时提供两个模型

```powershell
$env:AI_API_URL = "平台的 OpenAI 兼容 Base URL"
$env:AI_API_KEY = Read-Host "粘贴平台完整 API Key"
$env:AI_MODEL = "支持图片输入的视觉模型名称"

$env:AI_TEXT_API_URL = $env:AI_API_URL
$env:AI_TEXT_API_KEY = $env:AI_API_KEY
$env:AI_TEXT_MODEL = "deepseek-chat"
```

确认配置已经进入当前 PowerShell：

```powershell
Write-Host "视觉接口：" $env:AI_API_URL
Write-Host "视觉模型：" $env:AI_MODEL
Write-Host "视觉 Key 长度：" $env:AI_API_KEY.Length
Write-Host "文本接口：" $env:AI_TEXT_API_URL
Write-Host "文本模型：" $env:AI_TEXT_MODEL
Write-Host "文本 Key 长度：" $env:AI_TEXT_API_KEY.Length
```

两个 Key 长度都应大于 10。配置和启动必须在同一个 PowerShell 窗口中完成。

构建并启动：

```powershell
npm install
npm run build
py -m pip install -r backend\requirements.txt
cd backend
py api.py
```

后端会自动选择空闲端口并打开工作室页面。访问 `/api/health` 可以检查模型配置状态，正确结果应包含：

```json
{
  "status": "ok",
  "copywriterAi": true,
  "translatorAi": true,
  "aiModel": "视觉模型名称",
  "textModel": "deepseek-chat"
}
```

## 八、开发模式

后端终端：

```powershell
cd backend
py -m pip install -r requirements.txt
py -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

前端终端：

```powershell
npm install
npm run dev
```

访问 `http://127.0.0.1:5173/studio`。开发环境默认调用 `http://127.0.0.1:8000`。需要修改时，在项目根目录创建 `.env.local`：

```text
VITE_API_BASE_URL=http://你的后端地址:端口
```

## 九、主要接口

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 检查后端、模型与版式状态 |
| POST | `/api/cutout` | 上传商品图并自动抠图 |
| POST | `/api/translate` | 使用普通文本模型翻译商品名 |
| POST | `/api/copy` | 使用视觉模型生成宣传文案建议 |
| POST | `/api/copy/refine` | 根据用户意见修改一组文案 |
| POST | `/api/generate` | 生成海报和分层文档 |
| POST | `/api/render` | 将分层文档导出为 PNG |
| POST | `/api/feedback` | 保存用户选择反馈 |

详细字段见 [`backend/API_CONTRACT.md`](backend/API_CONTRACT.md)。启动后也可以访问 `/docs` 查看 FastAPI 自动接口文档。

## 十、海报版式模型

当前参考版式来自 4 张烘焙商品海报：蓝莓乳酪贝果、海盐焦糖可露丽、开心果可颂和草莓奶油丹麦。

训练数据位于 `backend/training/`，训练结果位于 `backend/models/bakery_editorial_layout.json`。重新训练：

```powershell
cd backend
py train_layout_model.py
```

4 张样本不足以可靠微调大型生成模型，因此当前使用归一化区域坐标、颜色角色和商品特征构建可解释的版式先验。后续增加海报样本和区域标注后可以重新训练，无需重写主生成流程。

## 十一、测试与构建

```powershell
# 前端类型检查
npm run typecheck

# 前端正式构建
npm run build

# 后端测试
py -m unittest discover -s backend -p "test*.py" -v
```

当前测试覆盖透明图片处理、学习版式、模板适配、质量检测和视觉文案字段约束。可选的 poster-design 本地素材库未放入 `vendor` 时，对应测试会跳过。

## 十二、常见问题

### `尚未配置文本模型接口`

当前后端进程没有读到 `AI_TEXT_API_URL` 或 `AI_TEXT_API_KEY`。必须先在 PowerShell 配置，再从同一个窗口启动后端。

### `尚未配置视觉AI`

当前后端进程没有读到 `AI_API_URL` 或 `AI_API_KEY`。没有视觉模型时可以人工填写卖点继续生成。

### `HTTP 401 invalid_api_key`

接口已经连接成功，但 API Key 无效或与平台不匹配。不同平台的 Key 不能混用；页面显示为 `****xxxx` 的脱敏字符串也不能作为完整 Key。

### 页面拒绝连接或端口被占用

直接运行 `py backend/api.py` 时，程序会自动选择当前空闲端口。请使用终端中最新显示的 `SmartMerch preview:` 地址，不要继续访问旧端口。

### 自动抠图失败

建议使用 Python 3.11/3.12，并重新安装：

```powershell
py -m pip install --upgrade "rembg[cpu]" pillow
```

### AI 翻译和 AI 推荐的区别

- AI 翻译只发送中文商品名，不发送商品图片。
- AI 推荐会发送商品图片给配置的视觉模型。
- 两项结果都只是建议，用户可以继续修改。

## 十三、安全与上传说明

- 不要提交真实 API Key。
- 不要把 Key 写入 README、源码或截图。
- `backend/generated/`、运行日志、模型缓存、用户反馈和第三方 `vendor/poster-design` 默认不上传。
- 视觉模型生成的商品属性和宣传文案必须人工核对，不得虚构品牌、容量、材质、价格或功效。
- 如果希望普通用户免配置 API，需要部署统一后端，并把密钥保存在服务器环境变量中，而不是放进前端代码。

## 十四、后续可扩展方向

- 增加更多行业和风格的版式训练样本；
- 为不同商品类别训练版式选择器；
- 增加模板检索与推荐；
- 增加账号、项目保存和历史作品；
- 部署统一后端，让体验者无需配置 API；
- 建立海报美学、信息完整性和商品一致性评价指标；
- 将用户选择与人工修改记录用于后续排序模型训练。

## 十五、项目定位

本项目重点不是单纯调用文生图模型，而是将图像处理、多模态理解、文本生成、可解释版式学习、前后端工程和可编辑输出组合为一套完整应用，适合作为程序设计综合实验项目，并可继续包装为软件类或人工智能应用类竞赛作品。

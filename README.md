# SmartMerch

AI 商品宣传图生成系统。Vue 3 前端负责上传商品图、确认或修改文案、预览和分图层编辑；FastAPI 后端负责自动抠图、视觉文案建议、学习版式生成、商品轮廓简笔画装饰和 PNG 渲染。

## 一键启动（推荐）

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

也可以在资源管理器中直接双击 `start-smartmerch.cmd`。聊天中的文件链接只用于定位文件，Windows/Codex 不会从聊天窗口直接执行脚本。

脚本会自动检查依赖、构建网页、启动服务并打开浏览器。整个网站只使用一个地址：`http://127.0.0.1:8765/studio`，不再需要分别保持 5173 和 8000 两个开发服务。独立使用 8765 端口可避免旧开发服务占用 8000 时造成启动失败。启动器会打开一个仅用于预览的无代理 Edge 窗口，以免系统代理拦截本机地址；它不会修改系统代理设置。

前端已经构建完成时，可直接双击 `open-smartmerch.cmd` 快速启动。该入口不会重复安装或构建，只启动网站服务，并会保留窗口显示明确的错误信息。

## 开发模式

启动后端：

```powershell
cd backend
py -m pip install -r requirements.txt
py -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

视觉模型为可选能力。复制 `backend/.env.example` 中的配置到当前终端环境；模型必须支持图片输入，`bge-*` 向量模型不能用于商品识别。

## 启动前端

另开一个终端：

```powershell
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。开发环境默认连接 `http://127.0.0.1:8000`，需要修改时创建 `.env.local`：

```text
VITE_API_BASE_URL=http://你的后端地址:8000
```

## 已接通流程

1. 上传 JPG、PNG 或 WEBP 商品图。
2. 后端自动抠图；视觉模型可用时识别商品并给出可修改的文案建议。
3. 用户填写中文商品名后，可由视觉模型翻译英文名，并从三组建议中选择或按意见局部修改；随后确认最多三条卖点和品牌口号。
4. 后端根据四张参考海报学习出的版式生成海报，并从商品轮廓生成简笔画装饰。
5. 前端进入分图层编辑器，可调整文字、位置、尺寸和颜色，再导出 PNG。

前端预览与后端 PNG 渲染统一使用 `LXGW WenKai`。后端从前端依赖目录读取该字体，因此首次运行请先在项目根目录执行 `npm install`。

具体字段见 [`backend/API_CONTRACT.md`](backend/API_CONTRACT.md)。

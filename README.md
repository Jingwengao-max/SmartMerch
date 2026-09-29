# SmartMerch

AI 商品宣传图生成系统。Vue 3 前端负责上传、商品信息、风格选择与候选展示；FastAPI 后端负责自动抠图、视觉文案、模板推荐、背景生成、质量评分和海报渲染。

## 启动后端

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
2. 后端自动抠图；视觉模型可用时同步识别商品并推荐文案。
3. 用户确认商品名称、特点、营销方向和设计风格。
4. 后端评估模板并生成评分最高的一套海报。
5. 前端进入分图层编辑器，可调整内容并导出 PNG。

具体字段见 [`backend/API_CONTRACT.md`](backend/API_CONTRACT.md)。

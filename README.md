# SmartMerch

AI 商品宣传图生成系统。Vue 3 前端负责上传、商品信息、风格选择与候选展示；FastAPI 后端负责自动抠图、视觉文案、模板推荐、背景生成、质量评分和海报渲染。

## 启动后端

```powershell
cd backend
py -m pip install -r requirements.txt
py -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

视觉模型为可选能力。把 `backend/.env.example` 复制成 `backend/.env` 并填写 Key 即可，后端启动时会自动读取；外部已设置的环境变量优先，不会被覆盖。模型必须支持图片输入，`bge-*` 向量模型不能用于商品识别。`.env` 已被 `.gitignore` 忽略，密钥不会提交到仓库。

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

1. 上传 JPG、PNG 或 WEBP 商品图，后端自动抠图。
2. 抠图完成后立刻结合商品图生成一版文案：主标题、副标题、每条卖点、价格、活动各成一块。
3. 用户可对任意条目填写「修改意见」，后端只改写提了意见的条目，其余原样保留；也可以整组应用或直接手改。
4. 选择设计风格，后端评估模板并生成评分最高的一套分层海报。
5. 前端进入分图层编辑器，可调整内容并导出 PNG。

具体字段见 [`backend/API_CONTRACT.md`](backend/API_CONTRACT.md)。

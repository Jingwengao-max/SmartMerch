FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig*.json vite.config.ts ./
COPY public ./public
COPY src ./src
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    U2NET_HOME=/opt/smartmerch-models \
    SMARTMERCH_RUNTIME_DIR=/data
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN mkdir -p "$U2NET_HOME" \
    && python -c "from rembg import new_session; new_session('u2net')"
COPY backend ./backend
COPY --from=frontend /app/dist ./dist
RUN mkdir -p /data/generated /data/data
EXPOSE 8000
CMD ["python", "backend/api.py"]

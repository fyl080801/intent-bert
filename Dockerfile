# 多阶段构建Dockerfile
# 用于部署金融意图BERT分类系统

# ============================================
# 阶段1: Python模型服务
# ============================================
FROM python:3.10-slim AS python-builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖文件
COPY lib/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制Python代码
COPY lib/python/ /app/lib/python/

# 复制训练好的模型（如果存在）
# 注意：首次构建时模型文件不存在，需要先训练
COPY models/ /app/models/ 2>/dev/null || echo "模型文件不存在，需要先训练"

# 设置环境变量
ENV PYTHONPATH=/app/lib/python
ENV MODEL_PATH=/app/models
ENV HOST=0.0.0.0
ENV PORT=5000

# 暴露模型服务端口
EXPOSE 5000

# ============================================
# 阶段2: Node.js API服务
# ============================================
FROM node:18-slim AS node-builder

WORKDIR /app

# 安装Python运行时（用于运行模型服务）
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖和模型
COPY --from=python-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=python-builder /app /app

# 复制package.json
COPY package*.json ./

# 安装Node.js依赖
RUN npm install --production

# 复制TypeScript源代码
COPY src/ ./src/
COPY tsconfig.json ./

# 编译TypeScript
RUN npm run build

# 设置环境变量
ENV NODE_ENV=production
ENV PORT=3000
ENV MODEL_SERVICE_URL=http://localhost:5000

# 暴露Node.js API端口
EXPOSE 3000

# ============================================
# 阶段3: 最终运行镜像
# ============================================
FROM python:3.10-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制所有文件
COPY --from=node-builder /app /app

# 创建启动脚本
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# 启动Python模型服务（后台）\n\
echo "启动Python模型服务..."\n\
cd /app\n\
python3 lib/python/model_server.py &\n\
MODEL_PID=$!\n\
\n\
# 等待模型服务就绪\n\
echo "等待模型服务启动..."\n\
sleep 10\n\
\n\
# 启动Node.js API服务（前台）\n\
echo "启动Node.js API服务..."\n\
cd /app\n\
node dist/server.js\n\
\n\
# 如果Node.js服务停止，也停止Python服务\n\
kill $MODEL_PID\n\
' > /app/start.sh && chmod +x /app/start.sh

# 暴露端口
EXPOSE 3000 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# 启动服务
CMD ["/app/start.sh"]

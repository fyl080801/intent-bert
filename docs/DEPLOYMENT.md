# 服务部署和运行指南

本文档详细说明如何启动和运行金融意图BERT分类系统。

## 📋 目录

- [系统架构](#系统架构)
- [环境要求](#环境要求)
- [快速启动](#快速启动)
- [服务配置](#服务配置)
- [验证部署](#验证部署)
- [常见问题](#常见问题)

## 系统架构

### 双服务架构

```
┌─────────────────────────────────────────┐
│         用户请求 (Port 3000)            │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│      Node.js API 服务                   │
│  - REST API                             │
│  - Swagger UI 文档                      │
│  - 请求路由和验证                        │
│  - 端口: 3000                           │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│      Python 模型服务                    │
│  - BERT 模型加载                         │
│  - 文本推理计算                          │
│  - 端口: 5001 (macOS兼容)               │
└─────────────────────────────────────────┘
```

### 服务职责

| 服务 | 职责 | 技术栈 | 端口 |
|------|------|--------|------|
| **Python模型服务** | BERT模型推理 | Flask + PyTorch + Transformers | 5001 |
| **Node.js API服务** | API网关 + 文档 | Express + TypeScript + Swagger UI | 3000 |

## 环境要求

### 硬件要求

- **CPU**: 4核心以上
- **内存**: 最少8GB，推荐16GB
- **磁盘**: 最少5GB可用空间

### 软件要求

- **Python**: 3.10+
- **Node.js**: 18+
- **操作系统**:
  - macOS (注意端口5000冲突)
  - Linux
  - Windows (WSL2)

## 快速启动

### 方法1: 使用npm脚本（推荐）

**步骤1: 启动Python模型服务**

```bash
# 终端1
npm run serve:model
```

**预期输出：**
```
模型已加载: models
启动模型服务...
地址: http://0.0.0.0:5001
健康检查: http://0.0.0.0:5001/health
模型信息: http://0.0.0.0:5001/model_info
预测接口: http://0.0.0.0:5001/predict
 * Running on http://0.0.0.0:5001
```

**步骤2: 启动Node.js API服务**

```bash
# 终端2
npm run dev
```

**预期输出：**
```
Node.js API服务已启动: http://localhost:3000
健康检查: http://localhost:3000/health
API文档: http://localhost:3000/api-docs
预测接口: http://localhost:3000/api/predict
模型信息: http://localhost:3000/api/model-info
示例接口: http://localhost:3000/api/example

等待Python模型服务启动...
✓ Python模型服务已就绪
```

### 方法2: 手动启动（高级配置）

如果需要自定义端口或模型路径：

**启动Python服务：**

```bash
MODEL_PATH=models PORT=5001 ./venv/bin/python lib/python/model_server.py
```

**启动Node.js服务：**

```bash
MODEL_SERVICE_URL=http://localhost:5001 PORT=3000 npm run dev
```

### 方法3: Docker部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 服务配置

### 环境变量说明

#### Python模型服务

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MODEL_PATH` | `models` | 训练好的模型目录路径 |
| `PORT` | `5001` | Python服务监听端口（已改为5001避免macOS冲突） |

**示例：**
```bash
MODEL_PATH=models PORT=5001 ./venv/bin/python lib/python/model_server.py
```

#### Node.js API服务

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MODEL_SERVICE_URL` | `http://localhost:5001` | Python模型服务的地址 |
| `PORT` | `3000` | Node.js API服务监听端口 |

**示例：**
```bash
MODEL_SERVICE_URL=http://localhost:5001 PORT=3000 npm run dev
```

### 端口配置说明

#### macOS用户特别说明

**问题：** macOS的AirPlay Receiver默认占用5000端口

**解决方案：**
1. ✅ **使用项目默认配置（推荐）** - 已自动使用5001端口
2. 关闭AirPlay Receiver：
   - 打开"系统设置"
   - 进入"通用" > "隔空播放接收器"
   - 关闭该功能

#### 其他操作系统

Linux和Windows用户可以使用5000端口：

```bash
# Python服务
MODEL_PATH=models PORT=5000 ./venv/bin/python lib/python/model_server.py

# Node.js服务
MODEL_SERVICE_URL=http://localhost:5000 npm run dev
```

## 验证部署

### 1. 检查服务健康状态

```bash
# 检查Node.js API服务
curl http://localhost:3000/health
# 预期输出: {"status":"ok","service":"nodejs-api"}

# 检查Python模型服务
curl http://localhost:5001/health
# 预期输出: {"status":"healthy","model_loaded":true}
```

### 2. 访问Swagger文档

在浏览器打开：`http://localhost:3000/api-docs`

你应该能看到完整的API文档界面。

### 3. 测试预测功能

**在Swagger UI中：**
1. 展开 `POST /api/predict` 接口
2. 点击 "Try it out"
3. 输入测试文本：`{"text":"我要开通基金定投"}`
4. 点击 "Execute"
5. 查看响应结果

**使用cURL测试：**

```bash
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"我要开通基金定投"}' | python3 -m json.tool
```

**预期输出：**
```json
{
  "success": true,
  "data": {
    "label_level1": "投资理财",
    "label_level2": "基金投资",
    "label_level3": "基金定投",
    "confidence_level1": 0.9234,
    "confidence_level2": 0.8567,
    "confidence_level3": 0.7891,
    "overall_confidence": 0.8564
  }
}
```

### 4. 查看模型信息

```bash
curl http://localhost:5001/model_info | python3 -m json.tool
```

这会显示：
- 支持的所有标签
- 标签数量
- 模型配置参数

## 常见问题

### Q1: 启动时提示"Address already in use"

**macOS用户：**
```bash
# 已在package.json中配置使用5001端口，直接运行
npm run serve:model
```

**Linux/Windows用户：**
```bash
# 查找占用端口的进程
lsof -ti:5000  # Linux/macOS
netstat -ano | findstr :5000  # Windows

# 终止进程或更换端口
kill -9 <PID>
```

### Q2: 提示找不到模型文件

```bash
# 检查模型目录
ls models/

# 如果不存在，需要先训练模型
npm run train:model

# 确保环境变量指向正确目录
MODEL_PATH=models ./venv/bin/python lib/python/model_server.py
```

### Q3: Node.js无法连接Python服务

```bash
# 检查Python服务是否运行
curl http://localhost:5001/health

# 检查环境变量
echo $MODEL_SERVICE_URL

# 重启Node.js服务并指定正确的Python服务地址
MODEL_SERVICE_URL=http://localhost:5001 npm run dev
```

### Q4: 服务启动成功但预测失败

```bash
# 查看Python服务日志
# 应该能看到请求信息和可能的错误

# 检查模型文件完整性
ls models/*.bin
ls models/label_encoders.json
ls models/config.json

# 重新训练模型
npm run train:model
```

### Q5: 如何在后台运行服务

**使用nohup：**
```bash
# Python服务
nohup npm run serve:model > python-service.log 2>&1 &

# Node.js服务
nohup npm run dev > nodejs-service.log 2>&1 &

# 查看日志
tail -f python-service.log
tail -f nodejs-service.log
```

**使用screen或tmux：**
```bash
# 创建新session
screen -S python-service
npm run serve:model
# Ctrl+A, D 分离session

# 重新连接
screen -r python-service
```

**使用PM2（推荐生产环境）：**
```bash
# 安装PM2
npm install -g pm2

# 启动Python服务
pm2 start "./venv/bin/python lib/python/model_server.py" --name bert-python --env MODEL_PATH=models --env PORT=5001

# 启动Node.js服务
pm2 start "npm run dev" --name bert-api --env MODEL_SERVICE_URL=http://localhost:5001

# 查看状态
pm2 status

# 查看日志
pm2 logs

# 停止服务
pm2 stop all
```

## 生产环境建议

1. **使用进程管理器** - PM2、systemd等
2. **配置反向代理** - Nginx、Apache
3. **启用HTTPS** - 使用Let's Encrypt
4. **添加认证** - API密钥、OAuth
5. **监控和日志** - ELK Stack、Prometheus
6. **负载均衡** - 多实例部署
7. **定期备份** - 模型和数据文件

## 相关文档

- [快速开始](QUICKSTART.md) - 5分钟部署指南
- [API文档](../SWAGGER_README.md) - 接口详细说明
- [完整文档](README_BERT.md) - 系统架构详解

## 获取帮助

如遇到问题：
1. 查看本文档的[常见问题](#常见问题)部分
2. 查看服务日志输出
3. 访问 `http://localhost:3000/api-docs` 测试API
4. 运行健康检查：`curl http://localhost:3000/health`

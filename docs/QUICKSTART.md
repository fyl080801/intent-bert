# 快速开始指南

## 5分钟快速部署金融意图BERT分类系统

### 前提条件

- Python 3.10+
- Node.js 18+
- 至少8GB RAM
- （可选）Docker

### 步骤1: 安装依赖

```bash
# 安装Python依赖
pip install -r lib/requirements.txt

# 安装Node.js依赖
npm install
```

### 步骤2: 准备数据

确保您有以下数据文件在`datasets/`目录：
- `datasets/financial_intent_dataset.csv` (训练集)
- `datasets/financial_intent_validation.csv` (验证集)

这些文件已经在datasets目录中。

### 步骤3: 训练模型

```bash
npm run train:model
```

或：

```bash
python lib/python/train.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --output_dir models
```

训练大约需要30-60分钟（取决于硬件）。

### 步骤4: 启动服务

**服务架构说明：**

系统采用双服务架构：
1. **Python模型服务** - 加载BERT模型，处理推理请求
2. **Node.js API服务** - 提供REST API和Swagger文档界面

**方式A: 本地开发模式（推荐）**

```bash
# 终端1: 启动Python模型服务（端口5001）
npm run serve:model
# 预期输出：
# 模型已加载: models
# 启动模型服务...
# 地址: http://0.0.0.0:5001

# 终端2: 启动Node.js API服务（端口3000）
npm run dev
# 预期输出：
# Node.js API服务已启动: http://localhost:3000
# API文档: http://localhost:3000/api-docs
# ✓ Python模型服务已就绪
```

**⚠️ macOS端口问题说明：**

macOS系统的AirPlay Receiver默认占用5000端口。如果遇到端口冲突：
- 方案1：使用已配置的5001端口（推荐）
- 方案2：关闭AirPlay Receiver（系统设置 > 通用 > 隔空播放接收器）

**手动启动（高级用法）：**

```bash
# 如果需要自定义端口或模型路径
# 终端1
MODEL_PATH=models PORT=5001 ./venv/bin/python lib/python/model_server.py

# 终端2
MODEL_SERVICE_URL=http://localhost:5001 PORT=3000 npm run dev
```

**方式B: Docker部署**

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 步骤5: 测试API

**访问Swagger交互式文档（推荐）：**

在浏览器打开：`http://localhost:3000/api-docs`

你可以直接在浏览器中：
- 查看所有API端点
- 测试预测功能
- 查看请求/响应示例

**使用cURL测试：**

```bash
# 健康检查
curl http://localhost:3000/health

# 测试预测
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"基金怎么买"}'

# 查看模型信息
curl http://localhost:3000/api/model-info

# 查看示例预测
curl http://localhost:3000/api/example
```

### 预期输出

```json
{
  "success": true,
  "data": {
    "label_level1": "投资理财",
    "label_level2": "基金投资",
    "label_level3": "开放式基金",
    "confidence_level1": 0.95,
    "confidence_level2": 0.93,
    "confidence_level3": 0.91,
    "overall_confidence": 0.93
  }
}
```

## 交互式预测

```bash
npm run predict
```

然后输入文本进行预测。

## 常用命令

```bash
# 训练模型
npm run train:model

# 启动模型服务
npm run serve:model

# 启动API服务
npm run dev

# 交互式预测
npm run predict

# 测试模型
npm run test:model

# 构建项目
npm run build

# 启动生产服务
npm start
```

## Docker命令

```bash
# 构建镜像
docker build -t financial-intent-bert .

# 运行容器
docker run -d -p 3000:3000 -p 5000:5000 --name financial-intent financial-intent-bert

# 使用Docker Compose
docker-compose up -d      # 启动
docker-compose logs -f    # 查看日志
docker-compose down       # 停止
```

## 故障排除

### 问题1: 端口5000被占用（macOS）

**症状：**
```
Address already in use
Port 5000 is in use by another program
```

**解决方案：**
- ✅ **已自动修复**：项目已配置使用5001端口
- 直接运行 `npm run serve:model` 即可
- 如需使用5000端口，关闭macOS的AirPlay Receiver：
  - 系统设置 > 通用 > 隔空播放接收器 > 关闭

### 问题2: Python模型服务无法启动

**症状：**
```
FileNotFoundError: No such file or directory: './model_output/label_encoders.json'
```

**解决方案：**
```bash
# 检查模型是否存在
ls models/

# 如果models目录不存在，需要先训练模型
npm run train:model

# 确保使用正确的环境变量
MODEL_PATH=models PORT=5001 ./venv/bin/python lib/python/model_server.py
```

### 问题3: Node.js无法连接到Python服务

**症状：**
```
Error: connect ECONNREFUSED 127.0.0.1:5000
```

**解决方案：**
```bash
# 检查Python服务是否运行在正确端口
curl http://localhost:5001/health

# 重启Node.js服务，设置正确的Python服务地址
MODEL_SERVICE_URL=http://localhost:5001 npm run dev
```

### 问题4: 模型预测标签不正确

**症状：** 预测结果标签层级不匹配

**解决方案：**
```bash
# 重新训练模型（使用更多数据）
npm run train:model

# 查看模型信息，确认标签编码
curl http://localhost:5001/model_info

# 检查label_encoders.json文件
cat models/label_encoders.json | python3 -m json.tool
```

### 问题5: 训练时内存不足

**症状：**
```
RuntimeError: CUDA out of memory
```

**解决方案：**
```bash
# 减小batch size
./venv/bin/python lib/python/train.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --output_dir models \
  --batch_size 8
```

## 下一步

- 阅读完整文档: [README_BERT.md](./README_BERT.md)
- 查看数据集说明: [DATASET_README.md](./DATASET_README.md)
- 自定义模型参数: 修改 `train.py` 参数
- 集成到您的应用: 查看 `src/modelClient.ts` 和 `src/server.ts`

## 获取帮助

如果遇到问题，请：
1. 查看日志输出
2. 检查系统要求
3. 查阅完整文档

祝您使用愉快！

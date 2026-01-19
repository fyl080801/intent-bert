# 金融意图BERT分类系统 - 使用指南

基于BERT的多任务学习金融意图分类系统，支持三级标签预测。

## 📋 目录

- [系统架构](#系统架构)
- [环境准备](#环境准备)
- [模型训练](#模型训练)
- [模型推理](#模型推理)
- [API服务](#api服务)
- [Docker部署](#docker部署)
- [开发指南](#开发指南)

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                 用户请求                              │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│          Node.js API服务 (端口: 3000)                │
│  - 业务逻辑处理                                       │
│  - 请求转发                                           │
│  - 响应格式化                                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│       Python模型服务 (端口: 5000)                     │
│  - BERT多任务模型                                     │
│  - 模型推理                                           │
│  - 结果预测                                           │
└─────────────────────────────────────────────────────┘
```

**技术栈：**
- **Python**: PyTorch + Transformers（BERT模型训练和推理）
- **Node.js**: Express + Axios（API服务）
- **部署**: Docker单容器部署

## 🔧 环境准备

### 1. 系统要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose（可选）
- 至少8GB RAM（推荐16GB）

### 2. Python环境安装

```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 3. Node.js环境安装

```bash
# 安装Node.js依赖
npm install
```

## 🎓 模型训练

### 快速开始

使用默认参数训练模型：

```bash
npm run train:model
```

或直接使用Python：

```bash
python train.py \
  --train_data financial_intent_dataset.csv \
  --val_data financial_intent_validation.csv \
  --output_dir model_output
```

### 训练参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--train_data` | financial_intent_dataset.csv | 训练数据路径 |
| `--val_data` | financial_intent_validation.csv | 验证数据路径 |
| `--model_name` | bert-base-chinese | 预训练模型名称 |
| `--output_dir` | ./model_output | 模型输出目录 |
| `--max_length` | 128 | 最大序列长度 |
| `--batch_size` | 16 | 批次大小 |
| `--num_epochs` | 5 | 训练轮数 |
| `--learning_rate` | 2e-5 | 学习率 |
| `--warmup_steps` | 500 | 预热步数 |
| `--weight_decay` | 0.01 | 权重衰减 |

### 训练示例

```bash
# 使用小batch size和更多epoch
python train.py \
  --batch_size 8 \
  --num_epochs 10 \
  --learning_rate 3e-5 \
  --warmup_steps 1000

# 使用其他BERT模型
python train.py \
  --model_name bert-base-chinese \
  --output_dir model_output_bert
```

### 训练输出

训练完成后，`model_output`目录包含：

```
model_output/
├── pytorch_model.bin           # 模型权重
├── config.json                 # 模型配置
├── tokenizer_config.json       # Tokenizer配置
├── vocab.txt                   # 词汇表
├── label_encoders.json         # 标签编码器
├── training_config.json        # 训练配置
├── eval_results.json           # 评估结果
├── checkpoint-*/               # 检查点文件
└── logs/                       # 训练日志
```

## 🔮 模型推理

### 交互式预测

```bash
npm run predict
```

或：

```bash
python predict.py --interactive
```

### 单条预测

```bash
python predict.py --text "基金怎么买"
```

### 批量预测

```bash
python predict.py \
  --input_file financial_intent_validation.csv \
  --output_file predictions.csv \
  --text_column text
```

### Python API使用

```python
from predict import FinancialIntentPredictor

# 初始化预测器
predictor = FinancialIntentPredictor('model_output')

# 单条预测
result = predictor.predict_single("基金怎么买")
print(result)
# {'label_level1': '投资理财', 'label_level2': '基金投资', 'label_level3': '开放式基金', ...}

# 批量预测
texts = ["基金怎么买", "如何申请贷款"]
results = predictor.predict_batch(texts)
```

## 🌐 API服务

### 启动服务

#### 方式1：分别启动服务

```bash
# 终端1：启动Python模型服务
npm run serve:model

# 终端2：启动Node.js API服务
npm run dev
```

#### 方式2：使用Docker

```bash
docker-compose up
```

### API接口

#### 1. 健康检查

```bash
GET http://localhost:3000/health
```

响应：
```json
{
  "status": "ok",
  "service": "nodejs-api"
}
```

#### 2. 预测接口

```bash
POST http://localhost:3000/api/predict
Content-Type: application/json

{
  "text": "基金怎么买"
}
```

响应：
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

#### 3. 批量预测

```bash
POST http://localhost:3000/api/predict-batch
Content-Type: application/json

{
  "texts": ["基金怎么买", "如何申请贷款"]
}
```

#### 4. 模型信息

```bash
GET http://localhost:3000/api/model-info
```

响应：
```json
{
  "success": true,
  "data": {
    "model_path": "./model_output",
    "device": "cpu",
    "max_length": 128,
    "num_labels": {
      "level1": 6,
      "level2": 24,
      "level3": 108
    },
    "labels": {
      "level1": ["投资理财", "信贷服务", ...],
      "level2": ["基金投资", "股票投资", ...],
      "level3": ["开放式基金", "指数基金", ...]
    }
  }
}
```

#### 5. 示例接口

```bash
GET http://localhost:3000/api/example
```

返回多个示例的预测结果。

### Node.js客户端使用

```typescript
import { modelClient } from './src/modelClient';

// 单条预测
const result = await modelClient.predict('基金怎么买');
console.log(result);

// 批量预测
const results = await modelClient.predictBatch([
  '基金怎么买',
  '如何申请贷款'
]);

// 格式化输出
console.log(modelClient.formatPrediction(result, '基金怎么买'));
```

## 🐳 Docker部署

### 构建镜像

```bash
# 确保已经训练好模型
docker build -t financial-intent-bert .
```

### 运行容器

```bash
docker run -d \
  -p 3000:3000 \
  -p 5000:5000 \
  --name financial-intent \
  financial-intent-bert
```

### 使用Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 验证部署

```bash
# 健康检查
curl http://localhost:3000/health

# 测试预测
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"基金怎么买"}'
```

## 📊 性能优化

### 1. 模型优化

```bash
# 使用量化模型减少内存占用
python train.py --model_name bert-base-chinese

# 调整批次大小根据GPU内存
python train.py --batch_size 32  # GPU内存充足时
python train.py --batch_size 8   # GPU内存不足时
```

### 2. 推理优化

```bash
# 批量推理提高吞吐量
python predict.py --input_file large_dataset.csv --output_file results.csv

# 使用GPU加速（如果可用）
export CUDA_VISIBLE_DEVICES=0
python model_server.py
```

### 3. 服务优化

```bash
# 使用Gunicorn多worker部署
gunicorn -w 4 -b 0.0.0.0:5000 model_server:app
```

## 🧪 测试

### 单元测试

```bash
npm test
```

### 集成测试

```bash
# 测试模型服务
curl http://localhost:5000/health

# 测试API服务
curl http://localhost:3000/health

# 测试预测
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"测试文本"}'
```

## 📝 常见问题

### 1. 训练时内存不足

**问题**: CUDA out of memory

**解决方案**:
```bash
# 减小batch size
python train.py --batch_size 8

# 或使用CPU训练
export CUDA_VISIBLE_DEVICES=""
python train.py
```

### 2. 模型服务启动慢

**问题**: 模型加载时间较长

**解决方案**:
- 模型首次加载需要时间，后续推理会很快
- 可以使用更小的模型（如distilbert-base-chinese）

### 3. Docker容器无法访问

**问题**: 无法连接到API服务

**解决方案**:
```bash
# 检查容器状态
docker ps

# 查看容器日志
docker logs financial-intent

# 确保端口映射正确
docker run -p 3000:3000 -p 5000:5000 ...
```

## 📚 更多资源

- [数据集说明](./DATASET_README.md)
- [Transformers文档](https://huggingface.co/docs/transformers)
- [PyTorch文档](https://pytorch.org/docs)

## 📄 许可证

ISC

---

**提示**: 首次使用前，请确保已经完成模型训练，或使用预训练模型。

# 项目结构说明

## 目录结构

```
bert-aliyun-test/
├── lib/                           # Python代码目录
│   ├── python/                    # Python模块
│   │   ├── models.py             # BERT多任务模型定义
│   │   ├── train.py              # 模型训练脚本
│   │   ├── predict.py            # 模型推理脚本
│   │   └── model_server.py       # Flask模型服务API
│   └── requirements.txt          # Python依赖列表
│
├── src/                           # Node.js/TypeScript代码
│   ├── server.ts                 # Express API服务
│   ├── modelClient.ts            # Python模型服务客户端
│   ├── client.ts                 # 阿里云NLP SDK客户端
│   ├── generateDataset.ts        # 数据集生成脚本
│   └── *.ts                      # 其他TypeScript文件
│
├── datasets/                      # 数据集目录
│   ├── financial_intent_dataset.csv      # 训练集（2000条）
│   ├── financial_intent_validation.csv   # 验证集（300条）
│   └── dataset_labels_info.json          # 标签体系说明
│
├── models/                        # 训练好的模型（训练后生成）
│   ├── pytorch_model.bin         # 模型权重
│   ├── config.json               # 模型配置
│   ├── label_encoders.json       # 标签编码器
│   ├── training_config.json      # 训练配置
│   └── checkpoint-*/             # 检查点文件
│
├── docs/                          # 文档目录
│   ├── QUICKSTART.md             # 快速开始指南
│   ├── README_BERT.md            # 完整使用文档
│   └── DATASET_README.md         # 数据集说明
│
├── data/                          # 临时数据目录（可选）
├── checkpoints/                   # 检查点备份目录（可选）
│
├── dist/                          # TypeScript编译输出
├── node_modules/                  # Node依赖
│
├── docker-compose.yml             # Docker Compose配置
├── Dockerfile                     # Docker镜像配置
├── .dockerignore                  # Docker忽略文件
├── .gitignore                     # Git忽略文件
│
├── package.json                   # Node.js配置和脚本
├── tsconfig.json                  # TypeScript配置
└── README.md                      # 项目说明
```

## 路径映射

### Python代码
| 原路径 | 新路径 |
|--------|--------|
| `models.py` | `lib/python/models.py` |
| `train.py` | `lib/python/train.py` |
| `predict.py` | `lib/python/predict.py` |
| `model_server.py` | `lib/python/model_server.py` |
| `requirements.txt` | `lib/requirements.txt` |

### 数据集
| 原路径 | 新路径 |
|--------|--------|
| `financial_intent_dataset.csv` | `datasets/financial_intent_dataset.csv` |
| `financial_intent_validation.csv` | `datasets/financial_intent_validation.csv` |
| `dataset_labels_info.json` | `datasets/dataset_labels_info.json` |

### 模型输出
| 原路径 | 新路径 |
|--------|--------|
| `model_output/` | `models/` |

### 文档
| 原路径 | 新路径 |
|--------|--------|
| `QUICKSTART.md` | `docs/QUICKSTART.md` |
| `README_BERT.md` | `docs/README_BERT.md` |
| `DATASET_README.md` | `docs/DATASET_README.md` |

## 配置更新

### package.json
所有NPM脚本已更新为使用新路径：

```json
{
  "scripts": {
    "train:model": "python lib/python/train.py --train_data datasets/financial_intent_dataset.csv --val_data datasets/financial_intent_validation.csv --output_dir models",
    "predict": "python lib/python/predict.py --model_path models --interactive",
    "serve:model": "python lib/python/model_server.py",
    "test:model": "python lib/python/predict.py --model_path models"
  }
}
```

### Python脚本
- `train.py`: 默认输入 `datasets/*.csv`，输出到 `models/`
- `predict.py`: 默认模型路径 `models/`
- `model_server.py`: 默认模型路径 `models/`

### Docker
- `PYTHONPATH=/app/lib/python`
- `MODEL_PATH=/app/models`
- 启动命令: `python3 lib/python/model_server.py`

## 依赖关系

### Python模块导入
```python
# lib/python/train.py
from models import BertForMultiLabelClassification, create_multitask_model
```

所有Python文件在同一个目录（`lib/python/`），可以直接导入。

### Node.js调用Python
```typescript
// src/server.ts -> 调用 Python模型服务
import { modelClient } from './modelClient';

const result = await modelClient.predict('基金怎么买');
```

Node.js通过HTTP REST API调用Python模型服务。

## 环境变量

### 本地开发
```bash
# Python
export PYTHONPATH=lib/python
export MODEL_PATH=models

# Node.js
export MODEL_SERVICE_URL=http://localhost:5000
```

### Docker
在 `docker-compose.yml` 中配置：
```yaml
environment:
  - MODEL_PATH=/app/models
  - MODEL_SERVICE_URL=http://localhost:5000
```

## 工作流程

### 训练模型
```bash
# 1. 进入项目目录
cd bert-aliyun-test

# 2. 安装依赖
pip install -r lib/requirements.txt

# 3. 运行训练
python lib/python/train.py \
  --train_data datasets/financial_intent_dataset.csv \
  --val_data datasets/financial_intent_validation.csv \
  --output_dir models
```

### 启动服务
```bash
# 终端1: Python模型服务
python lib/python/model_server.py

# 终端2: Node.js API
npm run dev
```

### 预测
```bash
# 交互式
python lib/python/predict.py --model_path models --interactive

# 或通过API
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"基金怎么买"}'
```

## 最佳实践

1. **代码组织**: Python代码在`lib/`，Node.js代码在`src/`
2. **数据管理**: 数据集在`datasets/`，模型在`models/`
3. **文档**: 所有文档在`docs/`目录
4. **路径使用**: 使用相对路径，便于移植
5. **版本控制**: `models/`目录在`.gitignore`中（模型文件大）

## 故障排查

### 导入错误
```bash
# 确保PYTHONPATH正确
export PYTHONPATH=lib/python
```

### 找不到数据集
```bash
# 确保在项目根目录
ls datasets/
```

### 模型加载失败
```bash
# 检查模型路径
ls models/
```

## 扩展项目

### 添加新的Python模块
1. 在 `lib/python/` 创建新文件
2. 使用相对导入：`from .models import ...`

### 添加新的Node.js服务
1. 在 `src/` 创建新文件
2. 在 `package.json` 添加相应脚本

### 添加新的数据集
1. 放置在 `datasets/` 目录
2. 更新文档说明

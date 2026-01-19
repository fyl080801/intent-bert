# 金融意图BERT分类系统

基于BERT多任务学习的金融领域用户意图分类系统，支持三级标签预测。

## 项目结构

```
.
├── lib/                    # Python代码
│   ├── python/            # Python模块
│   │   ├── models.py      # BERT模型定义
│   │   ├── train.py       # 训练脚本
│   │   ├── predict.py     # 预测脚本
│   │   └── model_server.py # 模型服务API
│   └── requirements.txt   # Python依赖
├── src/                   # Node.js/TypeScript代码
│   ├── server.ts         # Node.js API服务
│   ├── modelClient.ts    # 模型客户端
│   └── client.ts         # 阿里云SDK客户端
├── datasets/             # 数据集
│   ├── financial_intent_dataset.csv
│   ├── financial_intent_validation.csv
│   └── dataset_labels_info.json
├── models/               # 训练好的模型（训练后生成）
├── docs/                 # 文档
│   ├── QUICKSTART.md     # 快速开始指南
│   ├── README_BERT.md    # 详细文档
│   └── DATASET_README.md # 数据集说明
├── docker-compose.yml    # Docker Compose配置
├── Dockerfile           # Docker镜像构建
└── package.json         # Node.js依赖和脚本
```

## 快速开始

### 1. 安装依赖

```bash
# Python依赖
pip install -r lib/requirements.txt

# Node.js依赖
npm install
```

### 2. 训练模型（可选）

```bash
npm run train:model
```

详细训练指南请查看 [docs/QUICKSTART.md](docs/QUICKSTART.md)

### 3. 启动服务

**本地开发：**

```bash
# 终端1: Python模型服务
npm run serve:model

# 终端2: Node.js API
npm run dev
```

**Docker部署：**

```bash
docker-compose up -d
```

### 4. 测试API

```bash
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"基金怎么买"}'
```

## 文档

- [快速开始](docs/QUICKSTART.md) - 5分钟快速部署
- [完整文档](docs/README_BERT.md) - 系统架构和API详解
- [数据集说明](docs/DATASET_README.md) - 数据集详细信息

## 技术栈

- **Python**: PyTorch + Transformers（BERT模型训练和推理）
- **Node.js**: Express + TypeScript（API服务）
- **部署**: Docker单容器部署

## 功能特性

- 多任务学习：同时预测一级、二级、三级标签
- REST API：完整的预测接口
- Docker支持：一键部署
- 交互式预测：命令行工具

## 阿里云NLP AutoML

本项目还包含阿里云NLP AutoML的客户端示例（`src/client.ts`），用于调用阿里云NLP服务。

**注意**: 生产环境建议使用更安全的无AK方式，详见[管理访问凭据](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-node-js-access-credentials)。

## 许可证

ISC
